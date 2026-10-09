from datetime import timedelta
from uuid import uuid4

import pytest
from bodyos_api.product import ProductService
from fastapi import HTTPException
from test_product_results import fixture_experiment
from test_v3_routes import client_for


def test_milestone_sources_and_explicit_withdrawal(session, field_cipher):
    svc, exp, start = fixture_experiment(session, field_cipher)
    assert svc.state()["milestones"] == []
    log = svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    svc.now = lambda: start + timedelta(days=8)
    svc.transition(exp["id"], "evaluate", exp["revision"])
    milestone = svc.state()["milestones"][0]
    assert milestone["status"] == "available"
    assert "不足" in milestone["evidence"]
    svc.delete_log(log["id"])
    withdrawn_source = svc.state()["milestones"][0]
    assert withdrawn_source["status"] == "source_withdrawn"
    assert withdrawn_source["action"] is None
    receipt = svc.withdraw_milestone(exp["id"])
    assert receipt["deleted"]
    assert svc.withdraw_milestone(exp["id"]) == receipt
    assert svc.state()["milestones"][0]["status"] == "withdrawn"
    assert svc.state()["experiments"][0]["id"] == exp["id"]
    with pytest.raises(HTTPException) as error:
        svc.withdraw_milestone(str(uuid4()))
    assert error.value.status_code == 404
    other_client, other_uid = client_for(session, field_cipher, "other-milestone-user")
    assert other_client.delete("/v3/milestones/" + exp["id"]).status_code == 404
    assert ProductService(session, field_cipher, other_uid).state()["milestones"] == []
    svc.erase()
    assert svc.state()["milestones"] == []
    assert svc.rows("milestone_withdrawal") == []
