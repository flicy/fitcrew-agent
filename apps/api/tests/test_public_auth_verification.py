from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from bodyos_api import public_auth
from bodyos_api.config import Settings
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException


@pytest.fixture
def signed_apple(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(public_auth, "apple_keys", lambda: SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())))
    now = datetime.now(UTC)
    claims = {"sub": "synthetic-identity", "aud": "com.example.fitcrew",
              "iss": "https://appleid.apple.com", "nonce": "synthetic-nonce",
              "iat": now, "exp": now + timedelta(minutes=5)}
    return key, claims


def test_apple_claims_verify_signature_audience_issuer_expiry_and_nonce(signed_apple):
    key, claims = signed_apple
    settings = Settings(apple_client_id="com.example.fitcrew")
    def encode(body):
        return jwt.encode(body, key, algorithm="RS256")
    assert public_auth.apple_claims(encode(claims), "synthetic-nonce", settings)["sub"]
    for change in ({"aud": "other.app"}, {"iss": "https://evil.example"},
                   {"nonce": "different"}, {"exp": datetime.now(UTC) - timedelta(minutes=2)}):
        with pytest.raises(HTTPException) as error:
            public_auth.apple_claims(encode({**claims, **change}), "synthetic-nonce", settings)
        assert error.value.status_code == 401
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException):
        public_auth.apple_claims(jwt.encode(claims, other_key, algorithm="RS256"),
                                 "synthetic-nonce", settings)
