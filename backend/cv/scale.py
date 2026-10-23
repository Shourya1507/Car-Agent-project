import cv2
import numpy as np
from typing import Optional, Tuple

def detect_aruco_scale(frame_bgr: np.ndarray, marker_length_mm: float = 100.0) -> Optional[float]:
    """
    Detects ArUco fiducial marker and computes pixels_per_millimetre.
    Supports both OpenCV 4.x and 5.x aruco APIs.
    """
    try:
        # Check cv2.aruco existence
        if not hasattr(cv2, "aruco"):
            return None

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        
        # OpenCV aruco dictionary loading
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        
        # Detector parameters
        if hasattr(cv2.aruco, "ArucoDetector"):
            parameters = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            corners, ids, rejected = detector.detectMarkers(gray)
        else:
            parameters = cv2.aruco.DetectorParameters_create()
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is not None and len(corners) > 0:
            c = corners[0][0] # 4 corners: top-left, top-right, bottom-right, bottom-left
            # Side lengths in pixels
            side_top = np.linalg.norm(c[0] - c[1])
            side_right = np.linalg.norm(c[1] - c[2])
            side_bottom = np.linalg.norm(c[2] - c[3])
            side_left = np.linalg.norm(c[3] - c[0])
            avg_side_px = float((side_top + side_right + side_bottom + side_left) / 4.0)
            pixels_per_mm = avg_side_px / marker_length_mm
            return pixels_per_mm
    except Exception:
        pass
    return None

def detect_plate_scale(frame_bgr: np.ndarray, plate_width_mm: float = 520.0) -> Optional[float]:
    """
    Estimates scale from standard rectangular license plate geometry.
    Standard plates have aspect ratio ~4.0 to 5.0 (European/Indian: 520x110 mm) or ~2.0 (US: 305x152 mm).
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h > 20 and w > 80:
            aspect = float(w) / float(h)
            # Match 4.0 - 5.0 aspect ratio
            if 3.8 <= aspect <= 5.2:
                pixels_per_mm = float(w) / plate_width_mm
                return pixels_per_mm
    return None
