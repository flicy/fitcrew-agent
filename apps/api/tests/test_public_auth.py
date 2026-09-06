from uuid import uuid4

from bodyos_api.app import create_app
from bodyos_api.config import Settings, get_settings
from bodyos_api.db import get_session
from bodyos_api.models import DeviceBinding, User
from bodyos_api.runtime import get_field_cipher
from fastapi.testclient import TestClient
from sqlalchemy import func, select


def client_for(session, cipher):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_field_cipher] = lambda: cipher
    app.dependency_overrides[get_settings] = lambda: Settings(
        public_base_url="https://example.test",
        identity_pepper="synthetic-pepper",
        public_auth_enabled=True,
        wechat_app_id="synthetic-app",
        wechat_app_secret="synthetic",
        apple_client_id="test.fitcrew",
        apple_client_secret="synthetic-apple-secret",
    )
    return TestClient(app)


def test_public_login_disabled_without_deployment_configuration(session, field_cipher):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_field_cipher] = lambda: field_cipher
    app.dependency_overrides[get_settings] = lambda: Settings()
    response = TestClient(app).post(
        "/v3/auth/wechat", json={"code": "synthetic-code", "privacy_version": "2026-09-07"}
    )
    assert response.status_code == 503


def test_wechat_verified_identity_reuses_user_not_device_secret(session, field_cipher, monkeypatch):
    import bodyos_api.public_auth as auth

    monkeypatch.setattr(auth, "verify_wechat", lambda code, settings: "synthetic-openid")
    client = client_for(session, field_cipher)
    body = {"code": "synthetic-code", "privacy_version": "2026-09-07"}
    one = client.post("/v3/auth/wechat", json=body)
    assert one.status_code == 200
    two = client.post("/v3/auth/wechat", json={**body, "code": "another-code"})
    assert two.status_code == 200
    assert session.scalar(select(func.count(User.fitcrew_user_id))) == 1
    assert one.json()["device_token"] != two.json()["device_token"]
    assert "synthetic-openid" not in one.text
    assert one.json()["consent_ids"] == {}
    token = one.json()["device_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    assert client.get("/v3/state").status_code == 200
    assert (
        client.post(
            "/v3/consents", json={"categories": ["sleep_deep"], "privacy_version": "2026-09-07"}
        ).status_code
        == 403
    )


def test_apple_challenge_cannot_be_replayed_or_replaced(session, field_cipher, monkeypatch):
    import bodyos_api.public_auth as auth

    calls = []

    def verified(body, nonce, settings):
        calls.append(nonce)
        return {"subject": "synthetic-apple-user", "refresh_token": "synthetic-refresh"}

    monkeypatch.setattr(auth, "verify_apple", verified)
    client = client_for(session, field_cipher)
    challenge = client.post("/v3/auth/apple/challenge", json={})
    assert challenge.status_code == 200
    body = {
        "challenge_id": challenge.json()["challenge_id"],
        "identity_token": "synthetic-jwt",
        "authorization_code": "synthetic-code",
        "privacy_version": "2026-09-07",
    }
    login = client.post("/v3/auth/apple", json=body)
    assert login.status_code == 200
    assert calls == [challenge.json()["nonce"]]
    assert client.post("/v3/auth/apple", json=body).status_code == 401
    assert (
        client.post("/v3/auth/apple", json={**body, "challenge_id": str(uuid4())}).status_code
        == 401
    )
    client.headers["Authorization"] = f"Bearer {login.json()['device_token']}"
    response = client.post(
        "/v3/consents", json={"categories": ["sleep_deep"], "privacy_version": "2026-09-07"}
    )
    assert response.status_code == 200
    assert set(response.json()["consent_ids"]) == {"sleep_deep"}


def test_invalid_privacy_version_cannot_create_account(session, field_cipher):
    client = client_for(session, field_cipher)
    assert (
        client.post(
            "/v3/auth/wechat", json={"code": "synthetic", "privacy_version": "old"}
        ).status_code
        == 422
    )
    assert session.scalar(select(func.count(User.fitcrew_user_id))) == 0


def test_expired_device_token_denies_private_routes(session, field_cipher):
    from datetime import UTC, datetime, timedelta

    from bodyos_api.auth import hash_device_token

    user = User(fitcrew_user_id=str(uuid4()))
    session.add(user)
    session.flush()
    device = DeviceBinding(
        fitcrew_user_id=user.fitcrew_user_id,
        device_public_id=str(uuid4()),
        token_hash=hash_device_token("expired-synthetic"),
    )
    # Assignment is deliberate: before implementation this field is not mapped, auth ignores it.
    device.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.add(device)
    session.commit()
    client = client_for(session, field_cipher)
    client.headers["Authorization"] = "Bearer expired-synthetic"
    assert client.get("/v3/state").status_code == 401
