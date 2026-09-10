from uuid import uuid4

from bodyos_api.auth import hash_device_token
from bodyos_api.models import Consent, DeviceBinding
from test_health_ingest import CONSENT_ID, USER_ID
from test_product_health import complete, setup
from test_public_auth import client_for


def client(session, cipher):
    token = "synthetic-second-iphone"
    session.add(
        DeviceBinding(
            fitcrew_user_id=USER_ID,
            device_public_id=str(uuid4()),
            token_hash=hash_device_token(token),
            platform="ios",
        )
    )
    session.commit()
    api = client_for(session, cipher)
    api.headers["Authorization"] = "Bearer " + token
    return api


def authorize(api, categories):
    response = api.post(
        "/v3/consents",
        json={
            "categories": categories,
            "privacy_version": "2026-09-07",
        },
    )
    assert response.status_code == 200
    return response.json()["consent_ids"]


def test_reconfirmation_preserves_experiment_scope_and_original_receipt(session, field_cipher):
    svc, start = setup(session, field_cipher)
    grant = session.get(Consent, CONSENT_ID)
    grant.receipt_version = "2026-09-07"
    session.commit()
    original_date = grant.granted_at
    exp = svc.propose()
    complete(svc, start, exp)
    api = client(session, field_cipher)
    for _ in range(2):
        assert authorize(api, ["step_count"]) == {"step_count": CONSENT_ID}
        observation = svc.state()["experiments"][0]["health_observation"]
        assert observation["metrics"][0]["status"] == "insufficient_data"
    session.refresh(grant)
    assert grant.granted and grant.withdrawn_at is None
    assert grant.granted_at.replace(tzinfo=None) == original_date.replace(tzinfo=None)


def test_added_scope_retains_existing_grant_but_withdraw_regrant_creates_new_receipt(
    session, field_cipher
):
    svc, start = setup(session, field_cipher)
    session.get(Consent, CONSENT_ID).receipt_version = "2026-09-07"
    session.commit()
    complete(svc, start, svc.propose())
    api = client(session, field_cipher)
    ids = authorize(api, ["step_count", "sleep_deep"])
    assert ids["step_count"] == CONSENT_ID
    assert authorize(api, ["sleep_deep"]) == {"sleep_deep": ids["sleep_deep"]}
    withdrawn = session.get(Consent, CONSENT_ID)
    session.refresh(withdrawn)
    withdrawn_date = withdrawn.withdrawn_at
    assert not withdrawn.granted
    replacement = authorize(api, ["step_count", "sleep_deep"])
    assert replacement["step_count"] != CONSENT_ID
    session.refresh(withdrawn)
    assert withdrawn.withdrawn_at == withdrawn_date and not withdrawn.granted
    metric = svc.state()["experiments"][0]["health_observation"]["metrics"][0]
    assert metric["status"] == "not_authorized"
    assert authorize(api, []) == {}


def test_changed_disclosure_requires_new_receipt(session, field_cipher):
    setup(session, field_cipher)
    api = client(session, field_cipher)
    assert authorize(api, ["step_count"])["step_count"] != CONSENT_ID
    old = session.get(Consent, CONSENT_ID)
    session.refresh(old)
    assert old.withdrawn_at is not None and not old.granted
