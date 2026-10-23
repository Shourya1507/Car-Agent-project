import os
import shutil
from typing import Optional
from backend.core.ports.storage import StoragePort

class LocalStorageAdapter(StoragePort):
    def __init__(self, base_dir: str = "data"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_path(self, key: str) -> str:
        # Normalize key to local path
        clean_key = key.lstrip("/").replace("/", os.sep)
        full_path = os.path.join(self.base_dir, clean_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def save_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._get_path(key)
        with open(path, "wb") as f:
            f.write(data)
        return f"file://{path}"

    def get_bytes(self, key: str) -> Optional[bytes]:
        path = self._get_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return f.read()

    def delete(self, key: str) -> bool:
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def delete_prefix(self, prefix: str) -> int:
        clean_prefix = prefix.lstrip("/").replace("/", os.sep)
        target_dir = os.path.join(self.base_dir, clean_prefix)
        count = 0
        if os.path.exists(target_dir):
            if os.path.isdir(target_dir):
                for root, dirs, files in os.walk(target_dir):
                    count += len(files)
                shutil.rmtree(target_dir)
            else:
                os.remove(target_dir)
                count = 1
        return count

    def get_upload_url(self, key: str, expires_in_sec: int = 600) -> str:
        # In local run, return the direct upload API route
        clean_key = key.lstrip("/")
        return f"/upload/{clean_key}"

    def get_download_url(self, key: str, expires_in_sec: int = 3600) -> str:
        clean_key = key.lstrip("/")
        return f"/media/{clean_key}"
