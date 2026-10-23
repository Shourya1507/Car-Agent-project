from abc import ABC, abstractmethod
from typing import Optional, List

class WorkflowPort(ABC):
    @abstractmethod
    def start_inspection_workflow(self, inspection_id: str) -> str:
        """Starts the multi-stage analysis pipeline and returns execution ID."""
        pass

    @abstractmethod
    def resume_retake(self, inspection_id: str, new_frames_uploaded: bool = True) -> bool:
        """Resumes workflow from WaitForRetake state after user uploads missing viewpoints."""
        pass
