import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from bodyos_api.app import create_app
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.models import Consent, DeviceBinding, IdentityBinding, PairingExchangeSession, User
from bodyos_api.runtime import get_field_cipher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

USER_ID = "11111111-1111-4111-8111-111111111111"
DEVICE_ID = "22222222-2222-4222-8222-222222222222"
CONSENT_ID = "33333333-3333-4333-8333-333333333333"
TOKEN = "owner-device-secret"


def seed_device(session: Session) -> None:
    session.add(User(fitcrew_user_id=USER_ID))
    session.add(
        DeviceBinding(
            id=DEVICE_ID,
            fitcrew_user_id=USER_ID,
            device_public_id="owner-iphone",
            token_hash=hashlib.sha256(TOKEN.encode()).hexdigest(),
        )
    )
    session.add(
        Consent(
            id=CONSENT_ID,
            fitcrew_user_id=USER_ID,
            category="blood_glucose",
            purpose="private_coaching",
            granted=True,
            receipt_version="v1",
            granted_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )
    session.commit()


def client_for(session: Session, cipher: FieldCipher) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_field_cipher] = lambda: cipher
    app.dependency_overrides[get_settings] = lambda: Settings(
        owner_token="owner-admin-secret",
        identity_pepper="test-identity-pepper",
        public_base_url="https://bodyos.example.test",
    )
    return TestClient(app)


def payload() -> dict:
    return {
        "batch_id": "44444444-4444-4444-8444-444444444444",
        "device_binding_id": DEVICE_ID,
        "consent_id": CONSENT_ID,
        "source": "com.yuwell.anytime",
        "timezone": "Asia/Shanghai",
        "sent_at": "2026-08-01T12:00:00+08:00",
        "samples": [
            {
                "sample_id": "55555555-5555-4555-8555-555555555555",
                "kind": "blood_glucose",
                "start_at": "2026-08-01T11:55:00+08:00",
                "end_at": "2026-08-01T11:55:00+08:00",
                "value": 5.6,
                "unit": "mmol/L",
                "source": "com.yuwell.anytime",
            }
        ],
    }


def test_sync_authenticates_bound_device_and_never_needs_user_id_header(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_device(session)
    response = client_for(session, field_cipher).post(
        "/v1/health/sync",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=payload(),
    )

    assert response.status_code == 202
    assert response.json() == {
        "batch_id": "44444444-4444-4444-8444-444444444444",
        "inserted_samples": 1,
        "replayed": False,
    }


def test_sync_rejects_missing_or_wrong_device_token(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_device(session)
    client = client_for(session, field_cipher)

    assert client.post("/v1/health/sync", json=payload()).status_code == 401
    assert (
        client.post(
            "/v1/health/sync",
            headers={"Authorization": "Bearer wrong"},
            json=payload(),
        ).status_code
        == 401
    )


def test_sync_rejects_token_bound_to_a_different_device(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_device(session)
    wrong = payload()
    wrong["device_binding_id"] = "99999999-9999-4999-8999-999999999999"

    response = client_for(session, field_cipher).post(
        "/v1/health/sync",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=wrong,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "device binding mismatch"


def test_sync_rejects_cross_user_token_without_creating_samples(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_device(session)
    second_user_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    second_device_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    second_consent_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    session.add(User(fitcrew_user_id=second_user_id))
    session.add(
        DeviceBinding(
            id=second_device_id,
            fitcrew_user_id=second_user_id,
            device_public_id="second-iphone",
            token_hash=hashlib.sha256(b"second-device-secret").hexdigest(),
        )
    )
    session.add(
        Consent(
            id=second_consent_id,
            fitcrew_user_id=second_user_id,
            category="blood_glucose",
            purpose="private_coaching",
            granted=True,
            receipt_version="v1",
            granted_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )
    session.commit()
    cross_user_batch = payload()
    cross_user_batch["device_binding_id"] = second_device_id
    cross_user_batch["consent_id"] = second_consent_id

    response = client_for(session, field_cipher).post(
        "/v1/health/sync",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=cross_user_batch,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "device binding mismatch"
    from bodyos_api.models import HealthSample

    assert session.scalar(select(func.count(HealthSample.id))) == 0


def test_status_returns_only_deidentified_operational_counts(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_device(session)
    client = client_for(session, field_cipher)
    client.post(
        "/v1/health/sync",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json=payload(),
    )

    response = client.get(
        "/v1/health/status", headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert response.status_code == 200
    assert response.json()["sample_count"] == 1
    assert response.json()["last_sync_at"] is not None
    assert USER_ID not in response.text


def test_owner_bootstrap_issues_an_opaque_exchange_without_mutating_device_or_consents(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    request = {
        "feishu_subject": "ou_private_owner",
        "device_public_id": "owner-iphone-15",
        "categories": ["blood_glucose", "sleep_deep", "workout"],
        "idempotency_key": "O" * 48,
    }
    response = client.post(
        "/v1/owner/bootstrap",
        headers={"X-Owner-Token": "owner-admin-secret"},
        json=request,
    )
    retry = client.post(
        "/v1/owner/bootstrap",
        headers={"X-Owner-Token": "owner-admin-secret"},
        json=request,
    )

    assert response.status_code == 201
    assert retry.status_code == 200
    assert retry.json() == response.json()
    body = response.json()
    assert set(body) == {"pairing_url", "expires_at"}
    assert body["pairing_url"].startswith("fitcrew-health://configure?")
    encoded = parse_qs(urlparse(body["pairing_url"]).query)["payload"][0]
    decoded = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    assert set(decoded) == {"baseURL", "expiresAt", "pairingCode"}
    assert "ou_private_owner" not in response.text
    assert session.scalar(select(func.count(DeviceBinding.id))) == 0
    assert session.scalar(select(func.count(Consent.id))) == 0
    assert session.scalar(select(func.count(PairingExchangeSession.id))) == 1

    exchanged = client.post(
        "/v1/pairing/exchange",
        headers={"Authorization": f"Bearer {decoded['pairingCode']}"},
    )

    assert exchanged.status_code == 200
    provisioning = exchanged.json()
    assert set(provisioning["consent_ids"]) == {"blood_glucose", "sleep_deep", "workout"}
    binding = session.get(DeviceBinding, provisioning["device_binding_id"])
    assert binding is not None
    assert binding.token_hash != provisioning["device_token"]


def test_owner_bootstrap_fails_closed_without_correct_owner_token(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    request = {
        "feishu_subject": "ou_private_owner",
        "device_public_id": "owner-iphone-15",
        "categories": ["blood_glucose"],
        "idempotency_key": "O" * 48,
    }

    assert client.post("/v1/owner/bootstrap", json=request).status_code == 401
    assert (
        client.post(
            "/v1/owner/bootstrap",
            headers={"X-Owner-Token": "wrong"},
            json=request,
        ).status_code
        == 401
    )


def test_owner_identity_rebind_preserves_device_token_and_health_owner(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_device(session)
    old_subject = "ou_old_bodyos_app_owner"
    old_hash = hmac.new(
        b"test-identity-pepper", old_subject.encode(), hashlib.sha256
    ).hexdigest()
    encrypted = field_cipher.encrypt_json({"subject": old_subject}, aad="identity:old-binding")
    session.add(
        IdentityBinding(
            id="old-binding",
            fitcrew_user_id=USER_ID,
            provider="feishu",
            subject_hash=old_hash,
            encrypted_subject=encrypted.nonce + encrypted.ciphertext,
            verified_at=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )
    session.commit()
    original_token_hash = session.get(DeviceBinding, DEVICE_ID).token_hash

    response = client_for(session, field_cipher).post(
        "/v1/owner/identity/rebind",
        headers={"X-Owner-Token": "owner-admin-secret"},
        json={
            "feishu_subject": "ou_current_bodyos_app_owner",
            "device_public_id": "owner-iphone",
        },
    )

    assert response.status_code == 200
    assert response.json()["changed"] is True
    assert "ou_current_bodyos_app_owner" not in response.text
    device = session.get(DeviceBinding, DEVICE_ID)
    assert device is not None
    assert device.fitcrew_user_id == USER_ID
    assert device.token_hash == original_token_hash
    old_identity = session.get(IdentityBinding, "old-binding")
    assert old_identity is not None
    assert old_identity.revoked_at is not None
    current_hash = hmac.new(
        b"test-identity-pepper",
        b"ou_current_bodyos_app_owner",
        hashlib.sha256,
    ).hexdigest()
    current = session.scalar(
        select(IdentityBinding).where(IdentityBinding.subject_hash == current_hash)
    )
    assert current is not None
    assert current.fitcrew_user_id == USER_ID
    assert current.revoked_at is None
