import cv2
import numpy as np
from typing import Tuple, List, Optional
from backend.core.models import QualityScore

def compute_sharpness(frame_bgr: np.ndarray) -> float:
    """Computes variance of the Laplacian on downscaled grayscale frame."""
    gray = cv2.cvtColor(cv2.resize(frame_bgr, (640, 360)), cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def check_exposure(frame_bgr: np.ndarray, clip_ratio: float = 0.05) -> bool:
    """Rejects frames with more than clip_ratio pixels at histogram extremes."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel() / gray.size
    clipped = hist[:5].sum() + hist[-5:].sum()
    return bool(clipped < clip_ratio)

def compute_glare_ratio(frame_bgr: np.ndarray, v_threshold: int = 245) -> float:
    """Calculates ratio of saturated pixels in the V channel (HSV)."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    v_chan = hsv[:, :, 2]
    glare_pixels = np.count_nonzero(v_chan >= v_threshold)
    return float(glare_pixels / v_chan.size)

def evaluate_frame_quality(frame_bgr: np.ndarray, sharpness_threshold: float = 80.0, max_glare: float = 0.15) -> QualityScore:
    sharpness = compute_sharpness(frame_bgr)
    exposure_ok = check_exposure(frame_bgr)
    glare = compute_glare_ratio(frame_bgr)

    passed = (sharpness >= sharpness_threshold) and exposure_ok and (glare <= max_glare)
    reason = None
    if not passed:
        reasons = []
        if sharpness < sharpness_threshold:
            reasons.append(f"Blurry (sharpness {sharpness:.1f} < {sharpness_threshold})")
        if not exposure_ok:
            reasons.append("Extreme exposure / clipping")
        if glare > max_glare:
            reasons.append(f"Excessive glare ({glare*100:.1f}%)")
        reason = ", ".join(reasons)

    return QualityScore(
        sharpness=sharpness,
        exposure_ok=exposure_ok,
        glare_ratio=glare,
        passed=passed,
        reason=reason
    )
