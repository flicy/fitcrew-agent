import base64
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from bodyos_api.models import Consent, DeviceBinding, PairingExchangeSession
from sqlalchemy import select
from test_public_auth import client_for


def login(session, cipher, monkeypatch, subject="synthetic-wechat"):
    import bodyos_api.public_auth as auth

    monkeypatch.setattr(auth, "verify_wechat", lambda code, settings: subject)
    client = client_for(session, cipher)
    result = client.post(
        "/v3/auth/wechat",
        json={
            "code": "synthetic",
            "privacy_version": "2026-09-07",
        },
    ).json()
    client.headers["Authorization"] = "Bearer " + result["device_token"]
    return client, session.get(DeviceBinding, result["device_binding_id"])


def issue(client, request_id=None):
    return client.post(
        "/v3/device-pairing",
        json={
            "request_id": request_id or str(uuid4()),
            "privacy_version": "2026-09-07",
        },
    )


def code(response):
    encoded = parse_qs(urlparse(response.json()["pairing_url"]).query)["payload"][0]
    return json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))["pairingCode"]


def redeem(client, secret):
    return client.post("/v1/pairing/exchange", headers={"Authorization": "Bearer " + secret})


def test_pairing_shares_account_without_changing_consent(session, field_cipher, monkeypatch):
    client, original = login(session, field_cipher, monkeypatch)
    consent = Consent(
        fitcrew_user_id=original.fitcrew_user_id,
        category="step_count",
        purpose="private_coaching",
        granted=True,
        receipt_version="synthetic",
    )
    session.add(consent)
    session.commit()
    saved = client.post(
        "/v3/logs",
        json={
            "request_id": str(uuid4()),
            "energy": 3,
            "stress": 1,
            "feeling": "正常",
            "note": "synthetic shared private record",
        },
    )
    assert saved.status_code == 200
    request_id = str(uuid4())
    first = issue(client, request_id)
    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    assert issue(client, request_id).json() == first.json()
    result = redeem(client, code(first))
    assert result.status_code == 200
    assert result.json()["consent_ids"] == {}
    paired = session.get(DeviceBinding, result.json()["device_binding_id"])
    assert paired.fitcrew_user_id == original.fitcrew_user_id
    assert paired.platform == "ios" and paired.expires_at is not None
    session.refresh(consent)
    assert consent.granted and consent.withdrawn_at is None
    assert redeem(client, code(first)).status_code == 409
    assert issue(client, request_id).status_code == 409
    client.headers["Authorization"] = "Bearer " + result.json()["device_token"]
    state = client.get("/v3/state")
    assert state.status_code == 200
    assert state.json()["logs"][0]["id"] == saved.json()["id"]
    assert state.json()["logs"][0]["note"] == "synthetic shared private record"
    assert issue(client).status_code == 403
    assert (
        client.post(
            "/v3/consents",
            json={
                "categories": ["sleep_deep"],
                "privacy_version": "2026-09-07",
            },
        ).status_code
        == 200
    )


def test_new_connection_and_cancel_invalidate_only_own_pending_links(
    session, field_cipher, monkeypatch
):
    a, _ = login(session, field_cipher, monkeypatch)
    b, _ = login(session, field_cipher, monkeypatch, "another-wechat")
    old, other = issue(a), issue(b)
    new = issue(a)
    assert redeem(a, code(old)).status_code == 409
    assert a.delete("/v3/device-pairing").json() == {"cancelled": True}
    assert redeem(a, code(new)).status_code == 409
    assert redeem(b, code(other)).status_code == 200


def test_expiry_and_data_deletion_prevent_connection(session, field_cipher, monkeypatch):
    client, _ = login(session, field_cipher, monkeypatch)
    expired = issue(client)
    row = session.scalar(select(PairingExchangeSession))
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert redeem(client, code(expired)).status_code == 409
    fresh = issue(client)
    assert (
        client.request(
            "DELETE", "/v3/data", json={"confirmation": "DELETE", "scope": "all"}
        ).status_code
        == 200
    )
    assert redeem(client, code(fresh)).status_code == 409


def test_pairing_requires_authenticated_account_and_no_extra_grants(
    session, field_cipher, monkeypatch
):
    client, _ = login(session, field_cipher, monkeypatch)
    assert (
        client.post(
            "/v3/device-pairing",
            json={
                "request_id": str(uuid4()),
                "privacy_version": "2026-09-07",
                "categories": ["step_count"],
            },
        ).status_code
        == 422
    )
    client.headers.pop("Authorization")
    assert issue(client).status_code == 401


def test_disconnect_denies_paired_token_and_preserves_wechat_account(
    session, field_cipher, monkeypatch
):
    owner, _ = login(session, field_cipher, monkeypatch)
    other, _ = login(session, field_cipher, monkeypatch, "another-owner")
    paired = redeem(owner, code(issue(owner))).json()
    path = "/v3/device-pairing/devices/" + paired["device_binding_id"]
    listed = owner.get("/v3/device-pairing/devices").json()["devices"]
    assert [d["id"] for d in listed] == [paired["device_binding_id"]]
    assert paired["device_token"] not in json.dumps(listed)
    assert other.delete(path).status_code == 404
    assert other.get("/v3/device-pairing/devices").json()["devices"] == []
    assert owner.delete(path).json()["disconnected"] is True
    assert owner.delete(path).json()["disconnected"] is True
    assert owner.get("/v3/device-pairing/devices").json()["devices"] == []
    assert owner.get("/v3/state").status_code == 200
    assert (
        owner.get(
            "/v3/state", headers={"Authorization": "Bearer " + paired["device_token"]}
        ).status_code
        == 401
    )
