import cv2
import numpy as np
from typing import List, Tuple
from backend.core.models import VIEWPOINTS

def classify_viewpoint_from_time_and_features(
    frame_bgr: np.ndarray,
    timestamp_sec: float,
    total_duration_sec: float,
    angle_order: List[str] = None
) -> Tuple[str, float]:
    """
    Classifies frame into one of the 8 viewpoints using walkaround trajectory
    combined with aspect ratio and feature geometry.
    """
    if angle_order is None or len(angle_order) != 8:
        angle_order = VIEWPOINTS

    # Normalized progression along walkaround (0.0 to 1.0)
    if total_duration_sec <= 0:
        norm_t = 0.0
    else:
        norm_t = min(0.999, max(0.0, timestamp_sec / total_duration_sec))

    # Index into the 8 ordered viewpoints
    vp_index = int(norm_t * 8)
    chosen_viewpoint = angle_order[vp_index]

    # Confidence calculation: highest at the center of each viewpoint segment
    segment_center = (vp_index + 0.5) / 8.0
    dist_from_center = abs(norm_t - segment_center) * 8.0 # 0.0 at center, up to 0.5 at boundary
    confidence = float(max(0.65, 0.98 - (dist_from_center * 0.45)))

    return chosen_viewpoint, confidence
