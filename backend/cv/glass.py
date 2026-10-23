import cv2
import numpy as np
from backend.core.models import GlassMeasurement

def analyze_glass(window_roi_bgr: np.ndarray, viewpoint: str) -> GlassMeasurement:
    """
    Analyzes window glass for stone chips and branching cracks using edge networks.
    """
    gray = cv2.cvtColor(window_roi_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)

    # Edge detection
    edges = cv2.Canny(blurred, 70, 200)

    # Count small circular/star-burst contours for chips
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    chips_count = 0
    cracks_count = 0

    for c in contours:
        area = cv2.contourArea(c)
        perimeter = cv2.arcLength(c, True)
        if perimeter > 0:
            circularity = 4 * np.pi * (area / (perimeter * perimeter))
            if 5 < area < 150 and circularity > 0.4:
                chips_count += 1
            elif perimeter > 60:
                # Long branching edge
                cracks_count += 1

    chips_detected = chips_count >= 2
    cracks_detected = cracks_count >= 1

    confidence = 0.85 if (chips_detected or cracks_detected) else 0.95

    return GlassMeasurement(
        viewpoint=viewpoint,
        cracks_detected=cracks_detected,
        chips_detected=chips_detected,
        confidence=confidence
    )
