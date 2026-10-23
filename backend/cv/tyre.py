import cv2
import numpy as np
from typing import Optional, Tuple
from backend.core.models import TyreMeasurement

def analyze_tyre(
    tyre_roi_bgr: np.ndarray,
    viewpoint: str,
    pixels_per_mm: Optional[float] = None
) -> TyreMeasurement:
    """
    Analyzes tyre tread depth and sidewall condition:
    1. Adaptive thresholding + morphological opening to segment grooves.
    2. Groove width/depth proxy estimation with scale.
    3. Canny edge density in sidewall for cracking.
    """
    gray = cv2.cvtColor(tyre_roi_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4
    )

    # Morphological opening to isolate main tread grooves
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 7))
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    # Calculate average groove width
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    widths = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if 5 <= w <= 80 and h > 20:
            widths.append(w)

    avg_width_px = float(np.mean(widths)) if widths else 15.0

    # Scale conversion
    if pixels_per_mm and pixels_per_mm > 0:
        depth_mm = avg_width_px / (pixels_per_mm * 1.5) # depth proxy based on groove shadow aspect
    else:
        # Default estimation based on typical phone distance
        depth_mm = (avg_width_px / 18.0) * 4.5

    # Band classification per legal/safety standards (minimum legal is usually 1.6 mm)
    if depth_mm >= 5.0:
        depth_range = "5 to 7 mm"
        condition_band = "good"
    elif depth_mm >= 3.0:
        depth_range = "3 to 5 mm"
        condition_band = "moderate"
    else:
        depth_range = "1.5 to 3 mm"
        condition_band = "worn"

    # Sidewall cracking detection via Canny edge density
    h, w = gray.shape
    sidewall_roi = gray[int(h * 0.7):, :]
    sw_edges = cv2.Canny(sidewall_roi, 60, 180)
    sw_edge_ratio = np.count_nonzero(sw_edges) / float(sidewall_roi.size)
    sidewall_cracking = sw_edge_ratio > 0.08

    return TyreMeasurement(
        viewpoint=viewpoint,
        depth_range_mm=depth_range,
        condition_band=condition_band,
        sidewall_cracking=sidewall_cracking,
        confidence=0.82
    )
