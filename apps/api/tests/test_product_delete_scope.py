from datetime import timedelta
from uuid import uuid4

from bodyos_api.models import Consent, DeviceBinding
from test_product_results import fixture_experiment
from test_v3_routes import client_for


def test_log_scope_preserves_health_consent_and_invalidates_dependencies(session, field_cipher):
    svc, exp, start = fixture_experiment(session, field_cipher)
    svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    consent = Consent(
        fitcrew_user_id=svc.user_id,
        category="step_count",
        purpose="private_coaching",
        granted=True,
        granted_at=start,
        receipt_version="test",
    )
    session.add(consent)
    device = session.query(DeviceBinding).filter_by(fitcrew_user_id=svc.user_id).one()
    device.last_cursor = "preserved-cursor"
    svc.now = lambda: start + timedelta(days=8)
    completed = svc.transition(exp["id"], "evaluate", exp["revision"])
    svc.feedback(exp["id"], completed["revision"], "fits", True)
    receipt = svc.erase_logs()
    assert receipt["scope"] == "logs" and receipt["deleted_count"] == 1
    state = svc.state()
    assert state["logs"] == [] and state["confirmed_memories"] == []
    assert state["journey"] is not None
    assert state["experiments"][0]["result"]["status"] == "invalidated"
    assert state["milestones"][0]["status"] == "source_withdrawn"
    session.refresh(consent)
    session.refresh(device)
    assert consent.granted and consent.withdrawn_at is None
    assert device.last_cursor == "preserved-cursor"
    assert svc.erase_logs()["deleted_count"] == 0


def test_delete_scope_is_validated_and_isolated(session, field_cipher):
    client, uid = client_for(session, field_cipher)
    from bodyos_api.product import ProductService

    svc = ProductService(session, field_cipher, uid)
    log = svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    session.commit()
    other, _ = client_for(session, field_cipher, str(uuid4()))
    assert (
        other.request(
            "DELETE", "/v3/data", json={"confirmation": "DELETE", "scope": "logs"}
        ).status_code
        == 200
    )
    assert svc.read(svc.row("log", log["id"])) is not None
    assert (
        other.request(
            "DELETE", "/v3/data", json={"confirmation": "DELETE", "scope": "bad"}
        ).status_code
        == 422
    )
    assert (
        other.request(
            "DELETE", "/v3/account", json={"confirmation": "DELETE", "scope": "logs"}
        ).status_code
        == 422
    )
