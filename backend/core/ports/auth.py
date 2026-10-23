from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class AuthPort(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies JWT and returns claims including sub/user_id."""
        pass

    @abstractmethod
    def create_token(self, user_id: str, email: str, expires_in_sec: int = 86400) -> str:
        """Issues JWT for authenticated session."""
        pass
