import hashlib

from bodyos_api.app import create_app
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.models import Consent, DeviceBinding, IdentityBinding, User
from bodyos_api.runtime import get_field_cipher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

OWNER_HEADERS = {"X-Owner-Token": "owner-admin-secret"}
INVITED_SUBJECT = "ou_private_invited_user"


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


def invite(client: TestClient, subject: str = INVITED_SUBJECT):
    return client.post(
        "/v1/owner/users/invite",
        headers=OWNER_HEADERS,
        json={
            "feishu_subject": subject,
            "locale": "zh-CN",
            "timezone": "Asia/Shanghai",
        },
    )


def test_invite_feishu_user_is_idempotent_and_private(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)

    first = invite(client)
    second = invite(client)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json() == {"created": True, "status": "invited"}
    assert second.json() == {"created": False, "status": "invited"}
    assert INVITED_SUBJECT not in first.text + second.text
    assert session.scalar(select(func.count(User.fitcrew_user_id))) == 1
    assert session.scalar(select(func.count(IdentityBinding.id))) == 1


def test_invite_requires_owner_token_and_does_not_mutate(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    request = {
        "feishu_subject": INVITED_SUBJECT,
        "locale": "zh-CN",
        "timezone": "Asia/Shanghai",
    }

    assert client.post("/v1/owner/users/invite", json=request).status_code == 401
    assert (
        client.post(
            "/v1/owner/users/invite",
            headers={"X-Owner-Token": "wrong"},
            json=request,
        ).status_code
        == 401
    )
    assert session.scalar(select(func.count(User.fitcrew_user_id))) == 0


def test_pairing_is_scoped_to_invited_user(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201

    response = client.post(
        "/v1/owner/users/pair",
        headers=OWNER_HEADERS,
        json={
            "feishu_subject": INVITED_SUBJECT,
            "device_public_id": "invited-iphone",
            "categories": [
                "sleep_asleep",
                "heart_rate_variability",
                "resting_heart_rate",
                "workout",
                "active_energy",
                "step_count",
                "stand_hours",
                "activity_summary",
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "device_binding_id",
        "consent_ids",
        "device_token",
        "pairing_url",
    }
    assert INVITED_SUBJECT not in response.text
    identity = session.scalar(select(IdentityBinding))
    device = session.scalar(
        select(DeviceBinding).where(DeviceBinding.device_public_id == "invited-iphone")
    )
    assert identity is not None
    assert device is not None
    assert device.fitcrew_user_id == identity.fitcrew_user_id
    assert device.token_hash == hashlib.sha256(body["device_token"].encode()).hexdigest()
    consent_users = set(
        session.scalars(select(Consent.fitcrew_user_id)).all()
    )
    assert consent_users == {identity.fitcrew_user_id}


def test_pairing_rejects_uninvited_subject_and_bound_device_without_mutation(
    session: Session, field_cipher: FieldCipher
) -> None:
    existing_user = User()
    session.add(existing_user)
    session.flush()
    existing = DeviceBinding(
        fitcrew_user_id=existing_user.fitcrew_user_id,
        device_public_id="already-bound-iphone",
        token_hash=hashlib.sha256(b"existing-token").hexdigest(),
    )
    session.add(existing)
    session.commit()
    original_hash = existing.token_hash
    client = client_for(session, field_cipher)

    uninvited = client.post(
        "/v1/owner/users/pair",
        headers=OWNER_HEADERS,
        json={
            "feishu_subject": "ou_not_invited",
            "device_public_id": "new-iphone",
            "categories": ["workout"],
        },
    )
    assert uninvited.status_code == 404

    assert invite(client).status_code == 201
    conflict = client.post(
        "/v1/owner/users/pair",
        headers=OWNER_HEADERS,
        json={
            "feishu_subject": INVITED_SUBJECT,
            "device_public_id": "already-bound-iphone",
            "categories": ["workout"],
        },
    )
    assert conflict.status_code == 409
    session.refresh(existing)
    assert existing.fitcrew_user_id == existing_user.fitcrew_user_id
    assert existing.token_hash == original_hash
    assert session.scalar(select(func.count(Consent.id))) == 0
