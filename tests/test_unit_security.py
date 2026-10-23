import pytest
import hashlib
from backend.adapters.signing_local import LocalEcdsaSigningAdapter
from backend.adapters.auth_local import LocalAuthAdapter

def test_ecdsa_signing_and_verification():
    signer = LocalEcdsaSigningAdapter(key_path="data/keys/test_key.pem")
    
    # Hash of a report
    raw_data = b'{"carMake":"Toyota","score":86,"trust":"VERIFIED"}'
    digest = hashlib.sha256(raw_data).digest()

    sig = signer.sign_digest(digest)
    assert isinstance(sig, str) and len(sig) > 20

    # Verification must succeed on original digest
    assert signer.verify_signature(digest, sig) is True

    # Tampered data must fail signature verification!
    tampered_data = b'{"carMake":"Toyota","score":99,"trust":"VERIFIED"}'
    tampered_digest = hashlib.sha256(tampered_data).digest()
    assert signer.verify_signature(tampered_digest, sig) is False

def test_jwt_auth_lifecycle():
    auth = LocalAuthAdapter()
    token = auth.create_token(user_id="usr_test123", email="tester@carcheck.local", expires_in_sec=3600)
    
    payload = auth.verify_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_test123"
    assert payload["email"] == "tester@carcheck.local"

    # Corrupted token must fail
    assert auth.verify_token(token + "corrupt") is None
