import json
from types import SimpleNamespace
from uuid import uuid4

from bodyos_api.config import Settings, get_settings
from bodyos_api.model_gateway import HarnessFailure
from bodyos_api.runtime import get_model_gateway
from test_v3_routes import client_for, rid


def setup_ai(client, provider):
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        product_ai_enabled=True,
        product_ai_provider="测试 AI 服务",
        product_ai_notice_version="provider-test-v1",
    )
    client.app.dependency_overrides[get_model_gateway] = lambda: provider


def test_model_never_runs_without_separate_consent(session, field_cipher):
    client, _ = client_for(session, field_cipher)

    class Forbidden:
        def respond(self, envelope):
            raise AssertionError("model must not receive data without consent")

    setup_ai(client, Forbidden())
    client.put("/v3/journey", json=rid(goal="sleep"))
    result = client.post("/v3/experiments/propose", json=rid())
    assert result.status_code == 200
    assert result.json()["source"] == "rule_based"
    assert client.get("/v3/capabilities").status_code == 200


def test_ai_receives_only_minimum_aggregates_and_selects_approved_action(session, field_cipher):
    client, uid = client_for(session, field_cipher)
    captured = []

    class Provider:
        def respond(self, envelope):
            captured.append(envelope)
            return SimpleNamespace(text=json.dumps({"choice": "gentle"}), route="synthetic")

    setup_ai(client, Provider())
    client.put("/v3/journey", json=rid(goal="sleep"))
    client.post(
        "/v3/logs", json=rid(energy=2, stress=3, feeling="有点累", note="private never send")
    )
    consent = client.post(
        "/v3/ai-consent", json={"granted": True, "provider_notice_version": "provider-test-v1"}
    )
    assert consent.status_code == 200
    result = client.post("/v3/experiments/propose", json=rid()).json()
    assert result["source"] == "ai_selected"
    assert len(captured) == 1
    sent = json.dumps(captured[0])
    assert uid not in sent and "private never send" not in sent and "device" not in sent
    assert captured[0]["features"]["observed_days"] == 1
    assert result["data_categories"] == ["手动精力与压力记录"]
    assert client.post("/v3/experiments/propose", json=rid()).status_code == 200
    assert len(captured) == 1


def test_ai_failure_is_labeled_and_revocation_is_immediate(session, field_cipher):
    client, _ = client_for(session, field_cipher)

    class Unavailable:
        def respond(self, envelope):
            raise HarnessFailure("provider unavailable")

    setup_ai(client, Unavailable())
    client.put("/v3/journey", json=rid(goal="activity"))
    client.post(
        "/v3/ai-consent", json={"granted": True, "provider_notice_version": "provider-test-v1"}
    )
    response = client.post("/v3/experiments/propose", json=rid()).json()
    assert response["source"] == "rule_based"
    assert response["ai_status"] == "unavailable"
    revoked = client.post(
        "/v3/ai-consent", json={"granted": False, "provider_notice_version": "provider-test-v1"}
    )
    assert revoked.status_code == 200
    assert client.get("/v3/capabilities").json()["ai_consent_granted"] is False


def test_unapproved_model_text_is_not_shown_to_user(session, field_cipher):
    client, _ = client_for(session, field_cipher)

    class Malformed:
        def respond(self, envelope):
            return SimpleNamespace(text='{"choice":"medication", "advice":"unsafe"}', route="fake")

    setup_ai(client, Malformed())
    client.put("/v3/journey", json=rid(goal="sleep"))
    client.post(
        "/v3/ai-consent", json={"granted": True, "provider_notice_version": "provider-test-v1"}
    )
    response = client.post("/v3/experiments/propose", json={"request_id": str(uuid4())})
    assert response.status_code == 200
    assert "medication" not in response.text and "unsafe" not in response.text
    assert response.json()["source"] == "rule_based"
