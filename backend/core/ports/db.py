from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from backend.core.models import Inspection, Finding, Challenge, ShareLink, CoverageItem

class DbPort(ABC):
    # Inspections
    @abstractmethod
    def save_inspection(self, inspection: Inspection) -> None:
        pass

    @abstractmethod
    def get_inspection(self, user_id: str, inspection_id: str) -> Optional[Inspection]:
        pass

    @abstractmethod
    def get_inspection_by_id(self, inspection_id: str) -> Optional[Inspection]:
        pass

    @abstractmethod
    def list_inspections(self, user_id: str) -> List[Inspection]:
        pass

    @abstractmethod
    def delete_inspection(self, user_id: str, inspection_id: str) -> bool:
        pass

    # Findings
    @abstractmethod
    def save_findings(self, inspection_id: str, findings: List[Finding]) -> None:
        pass

    @abstractmethod
    def get_findings(self, inspection_id: str) -> List[Finding]:
        pass

    # Challenges (TTL)
    @abstractmethod
    def save_challenge(self, challenge: Challenge) -> None:
        pass

    @abstractmethod
    def get_challenge(self, inspection_id: str) -> Optional[Challenge]:
        pass

    # ShareLinks (TTL)
    @abstractmethod
    def save_share_link(self, link: ShareLink) -> None:
        pass

    @abstractmethod
    def get_share_link(self, token: str) -> Optional[ShareLink]:
        pass
