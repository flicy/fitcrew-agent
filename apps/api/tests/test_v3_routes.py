from uuid import uuid4

from bodyos_api.app import create_app
from bodyos_api.auth import hash_device_token
from bodyos_api.db import get_session
from bodyos_api.models import DeviceBinding, User
from bodyos_api.runtime import get_field_cipher
from fastapi.testclient import TestClient


def client_for(session, field_cipher, token="synthetic-device-a"):
    uid = str(uuid4())
    session.add(User(fitcrew_user_id=uid))
    session.flush()
    session.add(
        DeviceBinding(
            fitcrew_user_id=uid, device_public_id=str(uuid4()), token_hash=hash_device_token(token)
        )
    )
    session.commit()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_field_cipher] = lambda: field_cipher
    return TestClient(app, headers={"Authorization": f"Bearer {token}"}), uid


def rid(**values):
    return {"request_id": str(uuid4()), **values}


def test_structured_subjective_signals_round_trip_and_erase(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    body = rid(
        energy=2,
        stress=3,
        feeling="不适",
        sleep_feeling="醒后疲惫",
        training_feeling="偏累",
        stress_source="工作",
    )
    response = client.post("/v3/logs", json=body)
    assert response.status_code == 200
    record = response.json()
    for key in ("sleep_feeling", "training_feeling", "stress_source"):
        assert record[key] == body[key]
        assert client.get("/v3/export").json()["logs"][0][key] == body[key]
    assert client.post("/v3/logs", json=body).json() == record
    assert (
        client.post(
            "/v3/logs",
            json=rid(energy=3, stress=1, feeling="正常", sleep_feeling="unverified diagnosis"),
        ).status_code
        == 422
    )
    assert client.delete("/v3/logs/" + record["id"]).status_code == 200
    assert client.get("/v3/state").json()["logs"] == []
    assert client.post("/v3/logs", json=body).status_code == 410


def test_new_user_has_no_invented_health_or_experiments(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    response = client.get("/v3/state")
    assert response.status_code == 200
    state = response.json()
    assert state["health"]["sample_count"] == 0
    assert state["experiments"] == []
    assert state["journey"] is None
    assert state["mission"] is None
    assert client.get("/v3/state", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_journey_and_logs_retry_without_duplicates_or_plaintext(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    body = rid(goal="sleep")
    first = client.put("/v3/journey", json=body)
    assert first.status_code == 200
    assert client.put("/v3/journey", json=body).json() == first.json()
    log = rid(energy=3, stress=2, feeling="正常", note="synthetic-private-note")
    assert client.post("/v3/logs", json=log).status_code == 200
    assert client.post("/v3/logs", json=log).status_code == 200
    assert len(client.get("/v3/state").json()["logs"]) == 1
    assert client.post("/v3/logs", json={**log, "energy": 5}).status_code == 409
    from sqlalchemy import text

    stored = session.execute(text("SELECT payload_ciphertext FROM product_records")).all()
    assert stored
    assert all(b"synthetic-private-note" not in row[0] for row in stored)


def test_experiment_requires_acceptance_and_revision_and_real_observations(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    client.put("/v3/journey", json=rid(goal="sleep"))
    proposal = client.post("/v3/experiments/propose", json=rid())
    assert proposal.status_code == 200
    exp = proposal.json()
    assert exp["status"] == "proposed"
    assert exp["source"] == "rule_based"
    assert exp["stop_conditions"]
    route = f"/v3/experiments/{exp['id']}/transition"
    assert client.post(route, json=rid(action="evaluate", revision=1)).status_code == 409
    accepted = client.post(route, json=rid(action="accept", revision=1))
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "running"
    assert accepted.json()["accepted_at"]
    assert client.post(route, json=rid(action="stop", revision=1)).status_code == 409
    result = client.post(route, json=rid(action="evaluate", revision=2))
    assert result.status_code == 409  # cannot finish a seven-day experiment immediately
    assert client.post(route, json=rid(action="pause", revision=2)).json()["status"] == "paused"
    assert client.post(route, json=rid(action="stop", revision=3)).json()["status"] == "stopped"


def test_cross_user_read_write_and_delete_are_isolated(session, field_cipher):
    first, _ = client_for(session, field_cipher)
    second, _ = client_for(session, field_cipher, "synthetic-device-b")
    created = first.post("/v3/logs", json=rid(energy=2, stress=1, feeling="有点累", note=""))
    assert created.status_code == 200
    resource = created.json()["id"]
    assert second.get("/v3/state").json()["logs"] == []
    assert second.delete(f"/v3/logs/{resource}").status_code == 404
    assert first.delete(f"/v3/logs/{resource}").json()["receipt_id"]
    assert first.get("/v3/state").json()["logs"] == []


def test_export_and_delete_require_confirmation_and_revoke_account(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    client.put("/v3/journey", json=rid(goal="activity"))
    exported = client.get("/v3/export")
    assert exported.status_code == 200
    assert exported.json()["journey"]["goal"] == "activity"
    assert client.request("DELETE", "/v3/data", json={"confirmation": "no"}).status_code == 422
    removed = client.request("DELETE", "/v3/data", json={"confirmation": "DELETE"})
    assert removed.status_code == 200
    assert removed.json()["receipt_id"]
    assert client.get("/v3/state").json()["journey"] is None
    assert (
        client.request("DELETE", "/v3/account", json={"confirmation": "DELETE"}).status_code == 200
    )
    assert client.get("/v3/state").status_code == 401


def test_mission_needs_journey_and_actions_persist(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    assert client.post("/v3/mission", json=rid(action="done")).status_code == 409
    client.put("/v3/journey", json=rid(goal="energy"))
    mission = client.get("/v3/state").json()["mission"]
    assert mission["status"] == "proposed"
    assert client.post("/v3/mission", json=rid(action="lighten")).json()["status"] == "proposed"
    assert client.post("/v3/mission", json=rid(action="done")).json()["status"] == "done"
    assert client.get("/v3/state").json()["mission"]["status"] == "done"


def test_request_authenticated_before_account_delete_cannot_recreate_private_data(
    session, field_cipher
):
    import pytest
    from bodyos_api.product import ProductService
    from fastapi import HTTPException

    client, uid = client_for(session, field_cipher)
    stale_service = ProductService(session, field_cipher, uid)
    client.request("DELETE", "/v3/account", json={"confirmation": "DELETE"})
    with pytest.raises(HTTPException) as rejected:
        stale_service.mutate(
            "journey", rid(goal="sleep"), lambda: stale_service.set_journey("sleep")
        )
    assert rejected.value.status_code == 401


def test_deleted_log_cannot_be_resurrected_by_retry(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    body = rid(energy=3, stress=1, feeling="正常", note="synthetic-private")
    saved = client.post("/v3/logs", json=body).json()
    client.delete(f"/v3/logs/{saved['id']}")
    assert client.post("/v3/logs", json=body).status_code == 410
    assert client.get("/v3/state").json()["logs"] == []


def test_erased_data_cannot_be_resurrected_by_retry(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    body = rid(goal="sleep")
    client.put("/v3/journey", json=body)
    client.request("DELETE", "/v3/data", json={"confirmation": "DELETE"})
    assert client.put("/v3/journey", json=body).status_code == 410


def test_changing_goal_invalidates_unaccepted_proposal(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    client.put("/v3/journey", json=rid(goal="sleep"))
    before = client.post("/v3/experiments/propose", json=rid()).json()
    client.put("/v3/journey", json=rid(goal="activity"))
    after = client.post("/v3/experiments/propose", json=rid()).json()
    assert before["id"] != after["id"]
    assert "活动" in after["intervention"]
    assert (
        client.post(
            f"/v3/experiments/{before['id']}/transition",
            json=rid(action="accept", revision=before["revision"]),
        ).status_code
        == 409
    )


def test_lighten_alternative_persists_once_and_rejects_unknown_choice(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    assert client.put("/v3/journey", json=rid(goal="sleep")).status_code == 200
    before = client.get("/v3/state").json()["mission"]
    assert client.get("/v3/state").json()["mission"] == before
    body = rid(action="lighten", alternative="quiet_minute")
    response = client.post("/v3/mission", json=body)
    assert response.status_code == 200
    adjusted = response.json()
    assert adjusted["alternative"] == "quiet_minute"
    assert adjusted["adjusted_at"]
    assert adjusted["title"] != before["title"]
    assert client.post("/v3/mission", json=body).json() == adjusted
    assert client.get("/v3/state").json()["mission"] == adjusted
    assert (
        client.post("/v3/mission", json=rid(action="lighten", alternative="unknown")).status_code
        == 422
    )


def test_stale_mission_choice_cannot_replace_another_device_or_day(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    assert client.put("/v3/journey", json=rid(goal="sleep")).status_code == 200
    original = client.get("/v3/state").json()["mission"]
    body = rid(action="lighten", mission_id=original["id"], revision=0)
    accepted = client.post("/v3/mission", json=body)
    assert accepted.status_code == 200
    assert client.post("/v3/mission", json=body).json() == accepted.json()
    stale = rid(action="lighten", alternative="quiet_minute", mission_id=original["id"], revision=0)
    assert client.post("/v3/mission", json=stale).status_code == 409
    stale_day = rid(action="done", mission_id="2000-01-01", revision=1)
    assert client.post("/v3/mission", json=stale_day).status_code == 409
    assert client.get("/v3/state").json()["mission"] == accepted.json()


def test_trends_keep_missing_days_and_recompute_after_erasure(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    empty = client.get("/v3/state").json()["trends"]
    assert empty["source"] == "manual_logs"
    assert len(empty["points"]) == 90
    assert all(p["energy"] is None and p["count"] == 0 for p in empty["points"])
    first = client.post("/v3/logs", json=rid(energy=1, stress=1, feeling="正常")).json()
    second = client.post("/v3/logs", json=rid(energy=5, stress=3, feeling="正常")).json()
    points = client.get("/v3/state").json()["trends"]["points"]
    assert points[-1] == {"date": first["date"], "count": 2, "energy": 3, "stress": 2, "events": []}
    assert points[-2]["energy"] is None
    assert client.delete("/v3/logs/" + second["id"]).status_code == 200
    assert client.get("/v3/state").json()["trends"]["points"][-1]["energy"] == 1
    assert client.delete("/v3/logs/" + first["id"]).status_code == 200
    assert client.get("/v3/state").json()["trends"] == empty


def test_trend_window_uses_account_timezone_and_excludes_outside_days(
    session, field_cipher, monkeypatch
):
    from datetime import UTC, datetime, timedelta

    from bodyos_api.product import ProductService

    _, uid = client_for(session, field_cipher)
    session.get(User, uid).timezone = "Asia/Shanghai"
    session.commit()
    monkeypatch.setattr(ProductService, "now", lambda self: datetime(2026, 1, 1, 18, tzinfo=UTC))
    svc = ProductService(session, field_cipher, uid)
    start = (datetime(2026, 1, 2) - timedelta(days=89)).date().isoformat()
    logs = [
        {"date": start, "energy": 1, "stress": 2},
        {"date": "2026-01-02", "energy": 5, "stress": 1},
        {"date": "2026-01-03", "energy": 2, "stress": 1},
        {"date": "2025-01-01", "energy": 3, "stress": 1},
    ]
    result = svc.trends(
        logs, [{"title": "Synthetic observation", "accepted_at": "2026-01-01T18:00:00+00:00"}]
    )
    assert result["window_end"] == "2026-01-02"
    assert result["points"][0]["date"] == start
    assert sum(p["count"] for p in result["points"]) == 2
    assert result["points"][-1]["events"] == ["开始实验：Synthetic observation"]
    assert all(p["events"] == [] for p in result["points"][:-1])


def test_onboarding_resumes_and_cannot_skip_missing_prerequisites(session, field_cipher):
    client, _ = client_for(session, field_cipher)
    assert client.get("/v3/state").json()["onboarding"]["step"] == 1
    assert client.post("/v3/onboarding", json=rid(step=6)).status_code == 409
    first = rid(step=1)
    response = client.post("/v3/onboarding", json=first)
    assert response.status_code == 200
    assert client.post("/v3/onboarding", json=first).json() == response.json()
    assert client.get("/v3/state").json()["onboarding"]["step"] == 2
    assert client.post("/v3/onboarding", json=rid(step=2)).status_code == 409
    client.put("/v3/journey", json=rid(goal="sleep"))
    assert client.post("/v3/onboarding", json=rid(step=2)).status_code == 200
    assert client.post("/v3/onboarding", json=rid(step=3)).status_code == 200
    assert client.post("/v3/onboarding", json=rid(step=4)).status_code == 422
    assert client.post("/v3/onboarding", json=rid(step=4, route="health")).status_code == 200
    assert client.post("/v3/onboarding", json=rid(step=5)).status_code == 409
    assert client.post("/v3/onboarding", json=rid(step=5, route="manual")).status_code == 200
    assert client.post("/v3/onboarding", json=rid(step=6)).status_code == 409
    client.post("/v3/logs", json=rid(energy=3, stress=1, feeling="正常"))
    assert client.post("/v3/onboarding", json=rid(step=6)).status_code == 200
    progress = client.get("/v3/state").json()["onboarding"]
    assert progress["step"] == 7
    assert progress["route"] == "manual"
    assert progress["disclosure_1"] and progress["disclosure_3"]
    assert client.get("/v3/state").json()["health"]["last_sync_at"] is None
    assert client.request("DELETE", "/v3/data", json={"confirmation": "DELETE"}).status_code == 200
    assert client.get("/v3/state").json()["onboarding"]["step"] == 1


def test_onboarding_health_needs_current_consent_batch_and_persisted_progress(
    session, field_cipher
):
    from datetime import UTC, datetime, timedelta

    from bodyos_api.models import Consent, SyncBatch
    from bodyos_api.product import ProductService

    client, uid = client_for(session, field_cipher)
    svc = ProductService(session, field_cipher, uid)
    svc.write("onboarding", "current", {"step": 5, "route": "health"})
    now = datetime.now(UTC)
    device = session.query(DeviceBinding).filter_by(fitcrew_user_id=uid).one()
    device.last_sync_at = now - timedelta(days=1)
    consent = Consent(
        fitcrew_user_id=uid,
        category="step_count",
        purpose="private_coaching",
        granted=True,
        granted_at=now,
        receipt_version="test",
    )
    session.add(consent)
    session.flush()
    batch = SyncBatch(
        fitcrew_user_id=uid,
        batch_id=str(uuid4()),
        device_binding_id=device.id,
        consent_id=consent.id,
        source="synthetic",
        timezone="UTC",
        status="accepted",
        created_at=now - timedelta(days=1),
    )
    session.add(batch)
    session.commit()
    assert client.post("/v3/onboarding", json=rid(step=5)).status_code == 409
    batch.created_at = now + timedelta(seconds=1)
    session.commit()
    assert client.post("/v3/onboarding", json=rid(step=5)).status_code == 200
    # A separately constructed service reads encrypted persisted progress, not UI memory.
    assert ProductService(session, field_cipher, uid).onboarding()["step"] == 6
