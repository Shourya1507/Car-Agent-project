import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from backend.core.ports.signing import SigningPort

class LocalEcdsaSigningAdapter(SigningPort):
    def __init__(self, key_path: str = "data/keys/report_signing_p256.pem"):
        self.key_path = key_path
        os.makedirs(os.path.dirname(os.path.abspath(key_path)), exist_ok=True)
        self.private_key = self._load_or_generate_key()
        self.public_key = self.private_key.public_key()

    def _load_or_generate_key(self) -> ec.EllipticCurvePrivateKey:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)
        
        # Generate new NIST P-256 (secp256r1) keypair
        private_key = ec.generate_private_key(ec.SECP256R1())
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(self.key_path, "wb") as f:
            f.write(pem)
        return private_key

    def sign_digest(self, digest: bytes) -> str:
        """Signs a 32-byte SHA-256 digest using ECDSA P-256."""
        signature = self.private_key.sign(digest, ec.ECDSA(hashes.SHA256()))
        return base64.b64encode(signature).decode("utf-8")

    def verify_signature(self, digest: bytes, signature_b64: str) -> bool:
        """Verifies signature against digest using public key."""
        try:
            signature = base64.b64decode(signature_b64.encode("utf-8"))
            self.public_key.verify(signature, digest, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

    def get_public_key_pem(self) -> str:
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode("utf-8")
