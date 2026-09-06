from datetime import UTC, datetime, timedelta
from uuid import uuid4

from bodyos_api.models import Memory
from bodyos_api.product import ProductService
from sqlalchemy import select
from test_v3_routes import client_for


def fixture_experiment(session, cipher):
    _, uid = client_for(session, cipher)
    svc = ProductService(session, cipher, uid)
    start = datetime(2026, 8, 1, 10, tzinfo=UTC)
    svc.now = lambda: start
    svc.set_journey("energy")
    exp = svc.propose()
    exp = svc.transition(exp["id"], "accept", exp["revision"])
    return svc, exp, start


def test_evaluation_compares_days_without_claiming_causality(session, field_cipher):
    svc, exp, start = fixture_experiment(session, field_cipher)
    for day, energy in enumerate([1, 2, 4, 5]):
        svc.now = lambda day=day: start + timedelta(days=day)
        svc.add_log({"energy": energy, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start + timedelta(days=8)
    result = svc.transition(exp["id"], "evaluate", exp["revision"])["result"]
    assert result["status"] == "descriptive_only"
    assert result["energy_change"] == 3.0
    assert "因果" in result["summary"] or "导致" in result["summary"]
    assert session.scalars(select(Memory)).all() == []  # never silently confirmed


def test_withdrawn_observation_invalidates_result_and_cached_response(session, field_cipher):
    svc, exp, start = fixture_experiment(session, field_cipher)
    record = svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start + timedelta(days=8)
    body = {"request_id": str(uuid4()), "action": "evaluate", "revision": exp["revision"]}
    svc.mutate("eval", body, lambda: svc.transition(exp["id"], "evaluate", exp["revision"]))
    svc.delete_log(record["id"])
    item = svc.read(svc.row("experiment", exp["id"]))
    assert item["result"]["status"] == "invalidated"
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        svc.mutate("eval", body, lambda: None)
    assert error.value.status_code == 410


def test_paused_days_do_not_count_as_experiment_observations(session, field_cipher):
    svc, exp, start = fixture_experiment(session, field_cipher)
    svc.now = lambda: start + timedelta(days=1)
    paused = svc.transition(exp["id"], "pause", exp["revision"])
    svc.now = lambda: start + timedelta(days=2)
    svc.add_log({"energy": 1, "stress": 3, "feeling": "很累", "note": ""})
    svc.now = lambda: start + timedelta(days=3)
    resumed = svc.transition(exp["id"], "resume", paused["revision"])
    svc.now = lambda: start + timedelta(days=10)
    result = svc.transition(exp["id"], "evaluate", resumed["revision"])["result"]
    assert result["observed_days"] == 0
