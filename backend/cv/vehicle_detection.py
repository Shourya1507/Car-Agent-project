import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional, List
from pydantic import BaseModel

class VehicleDetectionResult(BaseModel):
    car_detected: bool
    confidence: float
    reason: str
    wheels_detected: int
    contour_area_ratio: float
    aspect_ratio: float
    edge_density: float
    details: Dict[str, Any] = {}

def detect_vehicle_presence(
    frame_bgr: np.ndarray,
    min_confidence: float = 0.40
) -> VehicleDetectionResult:
    """
    Analyzes an image frame to determine whether a vehicle/car is present.
    Evaluates:
    1. Overall frame dimensions and valid imagery.
    2. Large contiguous automotive body mass (contour area & aspect ratio).
    3. Structural automotive edges (horizontal rocker/roof lines, windshield slopes).
    4. Wheel/tire presence via circular/elliptical contours in the lower half.
    5. Color consistency and contrast against background.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return VehicleDetectionResult(
            car_detected=False,
            confidence=0.0,
            reason="Empty or invalid image frame",
            wheels_detected=0,
            contour_area_ratio=0.0,
            aspect_ratio=0.0,
            edge_density=0.0
        )

    h, w = frame_bgr.shape[:2]
    total_pixels = h * w
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Edge Density Analysis
    # Low edge density indicates plain wall, ceiling, sky, or completely blank surface
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / float(total_pixels)

    if edge_density < 0.005:
        # Less than 0.5% edges -> plain wall / solid color / blank image
        return VehicleDetectionResult(
            car_detected=False,
            confidence=0.05,
            reason="No structural edges found (plain background or blank frame)",
            wheels_detected=0,
            contour_area_ratio=0.0,
            aspect_ratio=0.0,
            edge_density=round(edge_density, 4)
        )

    # 2. Central Vehicle Region of Interest Analysis
    # Look for substantial automotive body contour in the central 70% of frame
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    # Adaptive threshold + Otsu to separate foreground vehicle from background
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Morphological closing to join panels, windows, and wheels into cohesive vehicle mass
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 9))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_contour_area = 0.0
    best_bbox = (0, 0, 0, 0)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > max_contour_area:
            max_contour_area = area
            best_bbox = cv2.boundingRect(cnt)

    bx, by, bw, bh = best_bbox
    contour_area_ratio = float(max_contour_area) / float(total_pixels)
    aspect_ratio = float(bw) / float(bh) if bh > 0 else 0.0

    # 3. Wheel / Tire Detection (circular or rounded shapes in lower 50% of candidate ROI)
    lower_half_y = int(h * 0.45)
    lower_half = gray[lower_half_y:, :]
    wheels_found = 0

    if lower_half.size > 0:
        # Detect circular features (wheels) using Hough Circles
        circles = cv2.HoughCircles(
            lower_half,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=int(w * 0.15),
            param1=80,
            param2=35,
            minRadius=int(h * 0.04),
            maxRadius=int(h * 0.22)
        )
        if circles is not None:
            wheels_found = min(len(circles[0]), 4)

    # 4. Multi-Signal Vehicle Scoring
    score = 0.0
    reasons = []

    # Signal A: Contour Area (Vehicles occupy 12% to 88% of standard framing)
    if 0.12 <= contour_area_ratio <= 0.88:
        score += 0.35
        reasons.append("Vehicle body mass detected")
    elif contour_area_ratio < 0.08:
        reasons.append("Insufficient subject mass in frame")
    else:
        score += 0.10

    # Signal B: Aspect Ratio (Vehicles are wider than they are tall, ~1.1 to 3.5)
    if 1.15 <= aspect_ratio <= 3.4:
        score += 0.30
        reasons.append("Automotive aspect ratio verified")
    elif 0.8 <= aspect_ratio < 1.15:
        score += 0.15
        reasons.append("Compact/frontal aspect ratio")
    else:
        reasons.append(f"Non-automotive aspect ratio ({aspect_ratio:.2f})")

    # Signal C: Wheel / Tire presence
    if wheels_found >= 1:
        score += 0.25
        reasons.append(f"{wheels_found} wheel/tire candidate(s) detected")

    # Signal D: Edge density consistent with automotive seams & glass
    if 0.015 <= edge_density <= 0.22:
        score += 0.15
        reasons.append("Automotive edge structure confirmed")

    confidence = round(float(min(0.99, max(0.05, score))), 2)
    car_detected = confidence >= min_confidence and (contour_area_ratio >= 0.08 or wheels_found >= 1)

    primary_reason = reasons[0] if reasons else ("Vehicle detected" if car_detected else "No car detected")
    if not car_detected:
        primary_reason = "No car detected: " + (", ".join(reasons) if reasons else "No vehicle features identified")

    return VehicleDetectionResult(
        car_detected=car_detected,
        confidence=confidence,
        reason=primary_reason,
        wheels_detected=wheels_found,
        contour_area_ratio=round(contour_area_ratio, 3),
        aspect_ratio=round(aspect_ratio, 2),
        edge_density=round(edge_density, 4),
        details={"best_bbox": [bx, by, bw, bh], "signals": reasons}
    )

def check_video_for_vehicle(
    frames_bgr: List[np.ndarray],
    threshold_ratio: float = 0.30
) -> Tuple[bool, float, List[VehicleDetectionResult]]:
    """
    Evaluates a sample of walkaround video frames to verify vehicle presence.
    At least `threshold_ratio` of sampled frames must detect a car.
    """
    if not frames_bgr:
        return False, 0.0, []

    results = []
    detected_count = 0

    # Sample up to 16 frames evenly distributed across the footage
    step = max(1, len(frames_bgr) // 16)
    sampled = frames_bgr[::step][:16]

    for frame in sampled:
        res = detect_vehicle_presence(frame)
        results.append(res)
        if res.car_detected:
            detected_count += 1

    detection_rate = float(detected_count) / float(len(sampled))
    mean_conf = float(np.mean([r.confidence for r in results])) if results else 0.0

    # A video has a car if at least 30% of frames show the vehicle
    overall_car_detected = detection_rate >= threshold_ratio and mean_conf >= 0.35

    return overall_car_detected, round(mean_conf, 2), results
