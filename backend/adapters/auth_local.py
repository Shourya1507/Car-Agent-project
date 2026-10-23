import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any
from backend.core.ports.auth import AuthPort

class LocalAuthAdapter(AuthPort):
    def __init__(self, secret: str = "carcheck-agent-hackathon-local-secret-key-2026"):
        self.secret = secret.encode("utf-8")

    def _b64encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def _b64decode(self, s: str) -> bytes:
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += "=" * padding
        return base64.urlsafe_b64decode(s.encode("utf-8"))

    def create_token(self, user_id: str, email: str, expires_in_sec: int = 86400) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "email": email,
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in_sec,
            "iss": "carcheck-local"
        }

        h_b64 = self._b64encode(json.dumps(header).encode("utf-8"))
        p_b64 = self._b64encode(json.dumps(payload).encode("utf-8"))
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        sig_b64 = self._b64encode(sig)

        return f"{h_b64}.{p_b64}.{sig_b64}"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.strip().split(".")
            if len(parts) != 3:
                return None
            h_b64, p_b64, sig_b64 = parts
            signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
            expected_sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
            actual_sig = self._b64decode(sig_b64)

            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            payload = json.loads(self._b64decode(p_b64).decode("utf-8"))
            if payload.get("exp", 0) < time.time():
                return None

            return payload
        except Exception:
            return None
