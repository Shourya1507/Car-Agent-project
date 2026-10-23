from abc import ABC, abstractmethod
from typing import List
import numpy as np
from backend.core.models import Finding

class DetectorPort(ABC):
    @abstractmethod
    def detect_damage(self, image_bgr: np.ndarray, viewpoint: str, frame_key: str) -> List[Finding]:
        """Runs damage detection model on a keyframe and returns structured findings."""
        pass
