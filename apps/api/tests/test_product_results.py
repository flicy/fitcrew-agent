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
    assert result["baseline_observed_days"] == 0
    assert result["between_window_energy_change"] is None
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


def test_baseline_comparison_requires_both_windows_and_invalidates_on_withdrawal(
    session, field_cipher
):
    svc, exp, start = fixture_experiment(session, field_cipher)
    baseline_records = []
    for day in range(4):
        svc.now = lambda day=day: start - timedelta(days=day + 1)
        baseline_records.append(
            svc.add_log({"energy": 2, "stress": 1, "feeling": "正常", "note": ""})
        )
    for day in range(4):
        svc.now = lambda day=day: start + timedelta(days=day)
        svc.add_log({"energy": 4, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start + timedelta(days=8)
    completed = svc.transition(exp["id"], "evaluate", exp["revision"])
    result = completed["result"]
    assert result["baseline_observed_days"] == 4
    assert result["between_window_energy_change"] == 2
    assert result["energy_change"] == 0  # within-window and baseline comparisons differ
    svc.delete_log(baseline_records[0]["id"])
    assert svc.read(svc.row("experiment", exp["id"]))["result"]["status"] == "invalidated"


def test_next_check_tracks_pause_and_completion_without_pretending_data_is_ready(
    session, field_cipher
):
    svc, exp, start = fixture_experiment(session, field_cipher)
    check = svc.state()["next_check"]
    assert check["action"] == "log"
    assert "0 个有效记录日" in check["detail"]
    paused = svc.transition(exp["id"], "pause", exp["revision"])
    assert svc.state()["next_check"]["title"] == "实验已暂停"
    svc.now = lambda: start + timedelta(days=1)
    svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start + timedelta(days=2)
    resumed = svc.transition(exp["id"], "resume", paused["revision"])
    assert "0 个有效记录日" in svc.state()["next_check"]["detail"]
    svc.now = lambda: start + timedelta(days=10)
    check = svc.state()["next_check"]
    assert check["action"] == "experiments"
    assert "记录不足" in check["detail"]
    assert (
        svc.transition(exp["id"], "evaluate", resumed["revision"])["result"]["status"]
        == "insufficient_data"
    )


def test_today_quality_uses_recent_manual_days_and_current_consent(session, field_cipher):
    from bodyos_api.models import Consent

    svc, _, start = fixture_experiment(session, field_cipher)
    assert svc.state()["today_context"]["status"] == "restricted"
    consent = Consent(
        fitcrew_user_id=svc.user_id,
        category="step_count",
        purpose="private_coaching",
        granted=True,
        granted_at=start,
        receipt_version="test",
    )
    session.add(consent)
    session.flush()
    assert svc.state()["today_context"]["status"] == "baseline_building"
    for day in range(4):
        svc.now = lambda day=day: start - timedelta(days=day)
        svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start
    context = svc.state()["today_context"]
    assert context["status"] == "ready"
    assert context["observed_days"] == 4
    assert context["source"] == "手动身体记录"
    consent.withdrawn_at = start
    consent.granted = False
    session.flush()
    state = svc.state()
    assert state["today_context"]["status"] == "restricted"
    assert state["today_context"]["health_categories"] == []
    assert state["health"]["last_sync_at"] is None
    svc.now = lambda: start + timedelta(days=8)
    assert svc.state()["today_context"]["observed_days"] == 0


def test_feedback_requires_confirmation_and_erased_memory_cannot_replay(session, field_cipher):
    import pytest
    from fastapi import HTTPException

    svc, exp, start = fixture_experiment(session, field_cipher)
    record = svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start + timedelta(days=8)
    completed = svc.transition(exp["id"], "evaluate", exp["revision"])
    feedback = svc.feedback(exp["id"], completed["revision"], "fits", False)
    assert svc.state()["confirmed_memories"] == []
    body = {"request_id": str(uuid4()), "assessment": "fits", "confirm_memory": True}
    confirmed = svc.mutate(
        "feedback", body, lambda: svc.feedback(exp["id"], feedback["revision"], "fits", True)
    )
    assert svc.state()["confirmed_memories"][0]["evidence_type"] == "user_report"
    assert svc.mutate("feedback", body, lambda: None) == confirmed
    svc.delete_memory(exp["id"])
    assert svc.state()["confirmed_memories"] == []
    with pytest.raises(HTTPException) as error:
        svc.mutate("feedback", body, lambda: None)
    assert error.value.status_code == 410
    current = svc.read(svc.row("experiment", exp["id"]))
    svc.feedback(exp["id"], current["revision"], "not_fit", True)
    svc.delete_log(record["id"])
    assert svc.state()["confirmed_memories"] == []
    with pytest.raises(HTTPException):
        latest = svc.read(svc.row("experiment", exp["id"]))
        svc.feedback(exp["id"], latest["revision"], "fits", True)
