import cv2
import numpy as np
from skimage.color import deltaE_ciede2000
from typing import Optional, Tuple
from backend.core.models import PaintMeasurement

def grey_world_white_balance(image_bgr: np.ndarray) -> np.ndarray:
    """Applies grey-world color constancy algorithm."""
    b, g, r = cv2.split(image_bgr.astype(np.float32))
    b_avg = np.mean(b)
    g_avg = np.mean(g)
    r_avg = np.mean(r)
    gray_avg = (b_avg + g_avg + r_avg) / 3.0

    b = np.clip(b * (gray_avg / (b_avg + 1e-6)), 0, 255)
    g = np.clip(g * (gray_avg / (g_avg + 1e-6)), 0, 255)
    r = np.clip(r * (gray_avg / (r_avg + 1e-6)), 0, 255)

    return cv2.merge([b, g, r]).astype(np.uint8)

def compute_panel_lab(panel_roi_bgr: np.ndarray) -> np.ndarray:
    """
    Computes robust median LAB color of a panel:
    Converts OpenCV 8-bit LAB (0..255) to standard CIE L*a*b* format:
    L: 0..100, a: -128..127, b: -128..127.
    Discards specular highlights (OpenCV L >= 240).
    """
    # Only apply grey-world if there is spatial variance across pixels (complex scene)
    # On uniform panel patches, avoid flattening chromaticity to neutral grey
    spatial_std = float(np.mean(np.std(panel_roi_bgr, axis=(0, 1))))
    if spatial_std > 10.0:
        processed = grey_world_white_balance(panel_roi_bgr)
    else:
        processed = panel_roi_bgr
    lab_cv = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB).astype(np.float32)

    # Filter highlights
    valid_mask = (lab_cv[:, :, 0] < 240) & (lab_cv[:, :, 0] > 10)
    if not np.any(valid_mask):
        pixels = lab_cv.reshape(-1, 3)
    else:
        pixels = lab_cv[valid_mask]

    median_cv = np.median(pixels, axis=0) # [L_cv, a_cv, b_cv]

    # Convert to standard CIE L*a*b*
    l_std = (median_cv[0] * 100.0) / 255.0
    a_std = median_cv[1] - 128.0
    b_std = median_cv[2] - 128.0

    return np.array([l_std, a_std, b_std], dtype=np.float32)

def compute_ciede2000(lab_a: np.ndarray, lab_b: np.ndarray) -> float:
    """Computes perceptual colour difference CIEDE2000."""
    return float(deltaE_ciede2000(lab_a[None, None, :], lab_b[None, None, :])[0, 0])

def analyze_paint_mismatch(
    panel_a_bgr: np.ndarray,
    panel_b_bgr: np.ndarray,
    panel_a_name: str,
    panel_b_name: str,
    viewpoint: str,
    delta_e_threshold: float = 3.5
) -> PaintMeasurement:
    """
    Compares paint color between adjacent panels.
    Delta-E > 3.5 is noticeable to human eye and flags possible repaint.
    """
    lab_a = compute_panel_lab(panel_a_bgr)
    lab_b = compute_panel_lab(panel_b_bgr)

    de = compute_ciede2000(lab_a, lab_b)
    mismatch = de > delta_e_threshold
    
    # Confidence scales with magnitude of mismatch
    if mismatch:
        confidence = min(0.96, 0.70 + (de - delta_e_threshold) * 0.05)
    else:
        confidence = 0.90

    return PaintMeasurement(
        panel_a=panel_a_name,
        panel_b=panel_b_name,
        viewpoint=viewpoint,
        delta_e=round(de, 2),
        mismatch_flag=mismatch,
        confidence=round(confidence, 2)
    )
