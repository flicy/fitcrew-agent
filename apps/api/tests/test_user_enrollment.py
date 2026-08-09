import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from bodyos_api.app import create_app
from bodyos_api.auth import hash_device_token
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.models import Consent, DeviceBinding, IdentityBinding, PairingExchangeSession, User
from bodyos_api.runtime import get_field_cipher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

OWNER_HEADERS = {"X-Owner-Token": "owner-admin-secret"}
INVITED_SUBJECT = "ou_private_invited_user"
PAIRING_KEY = "P" * 48


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


def issue_pairing(
    client: TestClient,
    *,
    subject: str = INVITED_SUBJECT,
    device_public_id: str = "invited-iphone",
    categories: list[str] | None = None,
    idempotency_key: str = PAIRING_KEY,
):
    return client.post(
        "/v1/owner/users/pair",
        headers=OWNER_HEADERS,
        json={
            "feishu_subject": subject,
            "device_public_id": device_public_id,
            "categories": categories or ["sleep_asleep", "workout"],
            "idempotency_key": idempotency_key,
        },
    )


def invitation_payload(pairing_url: str) -> dict[str, str]:
    encoded = parse_qs(urlparse(pairing_url).query)["payload"][0]
    normalized = encoded.replace("-", "+").replace("_", "/")
    padded = normalized + "=" * ((4 - len(normalized) % 4) % 4)
    return json.loads(base64.b64decode(padded))


def exchange(client: TestClient, pairing_url: str):
    payload = invitation_payload(pairing_url)
    return client.post(
        "/v1/pairing/exchange",
        headers={"Authorization": f"Bearer {payload['pairingCode']}"},
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


def test_pairing_url_contains_only_exchange_invitation_and_issuance_is_non_destructive(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201

    response = issue_pairing(client)

    assert response.status_code == 201
    assert set(response.json()) == {"pairing_url", "expires_at"}
    payload = invitation_payload(response.json()["pairing_url"])
    assert set(payload) == {"baseURL", "expiresAt", "pairingCode"}
    assert payload["baseURL"] == "https://bodyos.example.test"
    assert len(payload["pairingCode"]) >= 40
    assert datetime.fromisoformat(payload["expiresAt"]).tzinfo is not None
    assert INVITED_SUBJECT not in response.text
    assert session.scalar(select(func.count(DeviceBinding.id))) == 0
    assert session.scalar(select(func.count(Consent.id))) == 0
    assert session.scalar(select(func.count(PairingExchangeSession.id))) == 1


def test_pairing_issuance_retry_is_idempotent_and_mismatched_key_reuse_fails_closed(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201

    first = issue_pairing(client)
    second = issue_pairing(client)
    mismatch = issue_pairing(client, categories=["workout"], idempotency_key=PAIRING_KEY)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json() == first.json()
    assert mismatch.status_code == 409
    assert session.scalar(select(func.count(DeviceBinding.id))) == 0
    assert session.scalar(select(func.count(Consent.id))) == 0
    assert session.scalar(select(func.count(PairingExchangeSession.id))) == 1


def test_exchange_consumes_pairing_code_once_and_returns_direct_secrets(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201
    issued = issue_pairing(client)

    first = exchange(client, issued.json()["pairing_url"])
    second = exchange(client, issued.json()["pairing_url"])

    assert first.status_code == 200
    body = first.json()
    assert set(body) == {"base_url", "device_binding_id", "consent_ids", "device_token"}
    assert body["base_url"] == "https://bodyos.example.test"
    assert body["device_token"] not in issued.text
    assert second.status_code == 409
    binding = session.get(DeviceBinding, body["device_binding_id"])
    assert binding is not None
    assert binding.token_hash == hashlib.sha256(body["device_token"].encode()).hexdigest()
    assert session.get(User, binding.fitcrew_user_id).status == "active"


def test_exchange_rejects_expired_pairing_code(session: Session, field_cipher: FieldCipher) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201
    issued = issue_pairing(client)
    pending = session.scalar(select(PairingExchangeSession))
    assert pending is not None
    pending.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    response = exchange(client, issued.json()["pairing_url"])

    assert response.status_code == 409
    assert session.scalar(select(func.count(DeviceBinding.id))) == 0


def test_replacement_withdraws_omitted_categories_and_rotates_device_token(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201
    first_invitation = issue_pairing(client, categories=["sleep_asleep", "workout"])
    first = exchange(client, first_invitation.json()["pairing_url"])
    second_invitation = issue_pairing(
        client, categories=["workout"], idempotency_key="Q" * 48
    )
    second = exchange(
        client,
        second_invitation.json()["pairing_url"],
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["device_token"] != second.json()["device_token"]
    consents = session.scalars(select(Consent).order_by(Consent.created_at)).all()
    active = [consent.category for consent in consents if consent.withdrawn_at is None]
    assert active == ["workout"]
    assert all(consent.withdrawn_at is not None for consent in consents[:2])


def test_revoke_invalidates_pending_codes_device_token_and_private_consents(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201
    paired = exchange(client, issue_pairing(client).json()["pairing_url"])
    pending = issue_pairing(client, idempotency_key="R" * 48)

    response = client.post(
        "/v1/owner/users/revoke",
        headers=OWNER_HEADERS,
        json={"feishu_subject": INVITED_SUBJECT, "device_public_id": "invited-iphone"},
    )

    assert response.status_code == 200
    assert response.json() == {"revoked": True}
    assert INVITED_SUBJECT not in response.text
    assert exchange(client, pending.json()["pairing_url"]).status_code == 409
    assert client.post(
        "/v1/health/sync",
        headers={"Authorization": f"Bearer {paired.json()['device_token']}"},
        json={},
    ).status_code == 401
    assert all(consent.withdrawn_at is not None for consent in session.scalars(select(Consent)))


def test_pairing_rejects_cross_user_device_without_mutation(
    session: Session, field_cipher: FieldCipher
) -> None:
    existing_user = User()
    session.add(existing_user)
    session.flush()
    existing = DeviceBinding(
        fitcrew_user_id=existing_user.fitcrew_user_id,
        device_public_id="already-bound-iphone",
        token_hash=hash_device_token("existing-token"),
    )
    session.add(existing)
    session.commit()
    client = client_for(session, field_cipher)
    assert invite(client).status_code == 201

    conflict = issue_pairing(client, device_public_id="already-bound-iphone")

    assert conflict.status_code == 409
    session.refresh(existing)
    assert existing.fitcrew_user_id == existing_user.fitcrew_user_id
    assert existing.token_hash == hash_device_token("existing-token")
    assert session.scalar(select(func.count(PairingExchangeSession.id))) == 0
