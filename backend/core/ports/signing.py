from abc import ABC, abstractmethod
from typing import Tuple

class SigningPort(ABC):
    @abstractmethod
    def sign_digest(self, digest: bytes) -> str:
        """Signs a 32-byte SHA-256 digest using ECDSA P-256 and returns base64 signature."""
        pass

    @abstractmethod
    def verify_signature(self, digest: bytes, signature_b64: str) -> bool:
        """Verifies base64 ECDSA signature against the digest."""
        pass

    @abstractmethod
    def get_public_key_pem(self) -> str:
        """Returns public key in PEM format."""
        pass
