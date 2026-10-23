from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO, List

class StoragePort(ABC):
    @abstractmethod
    def save_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Saves binary data and returns storage URI/path."""
        pass

    @abstractmethod
    def get_bytes(self, key: str) -> Optional[bytes]:
        """Reads binary data by key."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Deletes object by key."""
        pass

    @abstractmethod
    def delete_prefix(self, prefix: str) -> int:
        """Deletes all objects with the given prefix."""
        pass

    @abstractmethod
    def get_upload_url(self, key: str, expires_in_sec: int = 600) -> str:
        """Returns upload URL (presigned PUT or local upload endpoint)."""
        pass

    @abstractmethod
    def get_download_url(self, key: str, expires_in_sec: int = 3600) -> str:
        """Returns download URL."""
        pass
