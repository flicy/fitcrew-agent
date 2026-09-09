from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from bodyos_api.auth import hash_device_token
from bodyos_api.health_service import HealthIngestionService
from bodyos_api.models import Consent, DeviceBinding, User
from bodyos_api.product import ProductService
from bodyos_api.schemas import HealthSyncBatchIn
from sqlalchemy import select
from test_health_ingest import CONSENT_ID, DEVICE_ID, USER_ID, glucose_batch, seed_authorized_owner


def setup(session, cipher):
    seed_authorized_owner(session)
    start = datetime(2026, 8, 8, tzinfo=ZoneInfo("Asia/Shanghai"))
    session.get(User, USER_ID).timezone = "Asia/Shanghai"
    grant = session.get(Consent, CONSENT_ID)
    grant.category, grant.granted_at = "step_count", start - timedelta(days=10)
    session.commit()
    svc = ProductService(session, cipher, USER_ID)
    svc.now = lambda: start
    svc.set_journey("activity")
    return svc, start


def ingest(session, cipher, date, value, source="synthetic-watch"):
    body = glucose_batch().model_dump(mode="json")
    body["batch_id"] = str(uuid4())
    body["samples"][0].update(
        sample_id=str(uuid4()),
        kind="step_count",
        value=value,
        unit="count",
        source=source,
        start_at=(date + timedelta(hours=12)).isoformat(),
        end_at=(date + timedelta(hours=12)).isoformat(),
    )
    HealthIngestionService(session, cipher).ingest(USER_ID, HealthSyncBatchIn.model_validate(body))


def complete(svc, start, exp):
    accepted = svc.transition(exp["id"], "accept", exp["revision"])
    svc.now = lambda: start + timedelta(days=8)
    svc.transition(exp["id"], "evaluate", accepted["revision"])
    return svc.state()["experiments"][0]


def test_health_experiment_uses_encrypted_samples_zero_and_current_sources(session, field_cipher):
    svc, start = setup(session, field_cipher)
    exp = svc.propose()
    assert "步数" in exp["data_categories"][1]
    assert "不发送给 AI" in exp["data_categories"][2]
    for offset in range(4):
        ingest(session, field_cipher, start - timedelta(days=offset + 1), 0)
        ingest(session, field_cipher, start + timedelta(days=offset), 100)
    item = complete(svc, start, exp)
    metric = item["health_observation"]["metrics"][0]
    assert metric["baseline_days"] == metric["observation_days"] == 4
    assert metric["change"] == 100
    assert len(metric["baseline_dates"]) == len(metric["observation_dates"]) == 4
    assert metric["source_text"] == "synthetic-watch"
    # Health observations are read-through, not retained in product or idempotency records.
    assert "health_observation" not in svc.read(svc.row("experiment", exp["id"]))
    ingest(session, field_cipher, start, 200, source="another-device")
    metric = svc.state()["experiments"][0]["health_observation"]["metrics"][0]
    assert metric["change"] is None and metric["observation_days"] == 3
    assert metric["excluded_days"] == 1
    HealthIngestionService(session, field_cipher).delete_user_health(USER_ID)
    metric = svc.state()["experiments"][0]["health_observation"]["metrics"][0]
    assert metric["baseline_days"] == metric["observation_days"] == 0
    assert metric["change"] is None


def test_health_scope_does_not_expand_or_reactivate_after_withdrawal(session, field_cipher):
    svc, start = setup(session, field_cipher)
    exp = svc.propose()
    item = complete(svc, start, exp)
    assert item["health_observation"]["metrics"][0]["status"] == "insufficient_data"
    HealthIngestionService(session, field_cipher).withdraw_consent(
        USER_ID, CONSENT_ID, at=svc.now()
    )
    session.add(
        Consent(
            fitcrew_user_id=USER_ID,
            category="step_count",
            purpose="private_coaching",
            granted=True,
            granted_at=svc.now(),
            receipt_version="new-grant",
        )
    )
    session.add(
        Consent(
            fitcrew_user_id=USER_ID,
            category="heart_rate_variability",
            purpose="private_coaching",
            granted=True,
            granted_at=svc.now(),
            receipt_version="new-grant",
        )
    )
    session.commit()
    observation = svc.state()["experiments"][0]["health_observation"]
    assert len(observation["metrics"]) == 1
    assert observation["metrics"][0]["status"] == "not_authorized"
    assert observation["metrics"][0]["change"] is None


def test_health_pauses_exclude_whole_days_and_freeze_timezone(session, field_cipher):
    svc, start = setup(session, field_cipher)
    exp = svc.propose()
    exp = svc.transition(exp["id"], "accept", exp["revision"])
    for offset in range(4):
        ingest(session, field_cipher, start - timedelta(days=offset + 1), 0)
        ingest(session, field_cipher, start + timedelta(days=offset), 100)
    svc.now = lambda: start + timedelta(hours=1)
    exp = svc.transition(exp["id"], "pause", exp["revision"])
    svc.now = lambda: start + timedelta(hours=2)
    exp = svc.transition(exp["id"], "resume", exp["revision"])
    session.get(User, USER_ID).timezone = "America/New_York"
    svc.now = lambda: start + timedelta(days=8)
    svc.transition(exp["id"], "evaluate", exp["revision"])
    observation = svc.state()["experiments"][0]["health_observation"]
    assert observation["timezone"] == "Asia/Shanghai"
    assert observation["metrics"][0]["observation_days"] == 3
    assert observation["metrics"][0]["change"] is None


def test_product_only_export_omits_health_observations_and_other_users(session, field_cipher):
    from bodyos_api.app import create_app
    from bodyos_api.db import get_session
    from bodyos_api.runtime import get_field_cipher
    from fastapi.testclient import TestClient
    from test_v3_routes import client_for

    svc, start = setup(session, field_cipher)
    complete(svc, start, svc.propose())
    session.get(DeviceBinding, DEVICE_ID).token_hash = hash_device_token("synthetic-health")
    session.commit()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_field_cipher] = lambda: field_cipher
    client = TestClient(app, headers={"Authorization": "Bearer synthetic-health"})
    assert "health_observation" in client.get("/v3/export").json()["experiments"][0]
    assert (
        "health_observation" not in client.get("/v3/export?scope=product").json()["experiments"][0]
    )
    other, _ = client_for(session, field_cipher, "synthetic-other-health")
    assert other.get("/v3/state").json()["experiments"] == []


def test_existing_manual_experiment_is_not_silently_given_health_access(session, field_cipher):
    svc, start = setup(session, field_cipher)
    grant = session.scalar(select(Consent).where(Consent.id == CONSENT_ID))
    grant.granted = False
    session.commit()
    exp = svc.propose()
    assert exp["health_scope"] == {}
    grant.granted = True
    session.commit()
    assert "health_observation" not in complete(svc, start, exp)


def test_partial_boundary_days_are_excluded_from_health_comparison(session, field_cipher):
    svc, midnight = setup(session, field_cipher)
    start = midnight + timedelta(hours=10)
    svc.now = lambda: start
    exp = svc.propose()
    assert "步数（可用健康样本）" in exp["metrics"]
    for offset in range(4):
        ingest(session, field_cipher, midnight - timedelta(days=offset + 1), 0)
        ingest(session, field_cipher, midnight + timedelta(days=offset), 100)
    # The acceptance day has an observation sample, but is not a full in-window day.
    item = complete(svc, start, exp)
    metric = item["health_observation"]["metrics"][0]
    assert metric["baseline_days"] == 4
    assert metric["observation_days"] == 3
    assert metric["change"] is None
