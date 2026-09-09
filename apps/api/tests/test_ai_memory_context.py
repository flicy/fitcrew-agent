import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from bodyos_api.config import Settings, get_settings
from bodyos_api.model_gateway import validate_model_envelope
from bodyos_api.models import Consent
from bodyos_api.product import ProductService
from test_product_ai import setup_ai
from test_v3_routes import client_for, rid


def remember(svc, day, assessment="not_fit", confirmed=True, goal="sleep"):
    svc.now = lambda: day
    svc.set_journey(goal)
    proposal = svc.propose()
    running = svc.transition(proposal["id"], "accept", proposal["revision"])
    svc.now = lambda: day + timedelta(days=1)
    log = svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": "private note marker"})
    svc.now = lambda: day + timedelta(days=8)
    completed = svc.transition(running["id"], "evaluate", running["revision"])
    svc.feedback(completed["id"], completed["revision"], assessment, confirmed)
    svc.session.commit()
    return proposal["id"], log["id"]


def allow(client):
    version = client.get("/v3/capabilities").json()["ai_notice_version"]
    assert len(version) <= 32
    assert (
        client.post(
            "/v3/ai-consent", json={"granted": True, "provider_notice_version": version}
        ).status_code
        == 200
    )
    return version


class Capture:
    def __init__(self):
        self.envelopes = []

    def respond(self, envelope):
        self.envelopes.append(envelope)
        return SimpleNamespace(text='{"choice":"gentle"}', route="synthetic")


def test_confirmed_context_is_minimal_and_withdrawal_invalidates_pending_proposal(
    session, field_cipher
):
    client, uid = client_for(session, field_cipher)
    svc = ProductService(session, field_cipher, uid)
    source, _ = remember(svc, datetime(2026, 8, 1, tzinfo=UTC))
    provider = Capture()
    setup_ai(client, provider)
    allow(client)
    body = rid()
    proposal = client.post("/v3/experiments/propose", json=body).json()
    sent = provider.envelopes[0]
    validate_model_envelope(sent)
    assert sent["features"]["confirmed_feedback"] == [
        {"goal_category": "sleep", "action": "standard", "assessment": "not_fit"}
    ]
    serialized = json.dumps(sent)
    assert (
        uid not in serialized
        and source not in serialized
        and "private note marker" not in serialized
    )
    assert "memory_source_ids" not in serialized
    assert proposal["memory_source_ids"] == [source]
    assert client.delete("/v3/memories/" + source).status_code == 200
    state = client.get("/v3/state").json()
    assert next(e for e in state["experiments"] if e["id"] == proposal["id"])["status"] == "stopped"
    assert client.post("/v3/experiments/propose", json=body).status_code == 410
    assert client.post("/v3/experiments/propose", json=rid()).status_code == 200
    assert provider.envelopes[-1]["features"]["confirmed_feedback"] == []


def test_source_deletion_removes_memory_context_and_pending_advice(session, field_cipher):
    client, uid = client_for(session, field_cipher)
    svc = ProductService(session, field_cipher, uid)
    _, log = remember(svc, datetime(2026, 8, 1, tzinfo=UTC))
    provider = Capture()
    setup_ai(client, provider)
    allow(client)
    proposed = client.post("/v3/experiments/propose", json=rid()).json()
    assert client.delete("/v3/logs/" + log).status_code == 200
    assert svc.confirmed_feedback_context("sleep") == ([], [])
    assert svc.read(svc.row("experiment", proposed["id"]))["status"] == "stopped"


def test_old_ai_consent_and_provider_change_require_new_disclosure(session, field_cipher):
    client, uid = client_for(session, field_cipher)
    provider = Capture()
    setup_ai(client, provider)
    session.add(
        Consent(
            fitcrew_user_id=uid,
            category="product_ai",
            purpose="experiment_selection",
            granted=True,
            receipt_version="provider-test-v1",
        )
    )
    session.commit()
    assert client.get("/v3/capabilities").json()["ai_consent_granted"] is False
    assert (
        client.post(
            "/v3/ai-consent", json={"granted": True, "provider_notice_version": "provider-test-v1"}
        ).status_code
        == 409
    )
    first = allow(client)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        product_ai_enabled=True,
        product_ai_provider="another provider",
        product_ai_notice_version="provider-test-v1",
    )
    caps = client.get("/v3/capabilities").json()
    assert caps["ai_notice_version"] != first and caps["ai_consent_granted"] is False


def test_context_excludes_unconfirmed_other_goal_and_oldest_entries(session, field_cipher):
    _, uid = client_for(session, field_cipher)
    svc = ProductService(session, field_cipher, uid)
    start = datetime(2025, 1, 1, tzinfo=UTC)
    ids = []
    for i in range(11):
        source, _ = remember(
            svc, start + timedelta(days=i * 9), assessment="fits" if i == 10 else "not_fit"
        )
        ids.append(source)
    remember(svc, start + timedelta(days=100), confirmed=False)
    remember(svc, start + timedelta(days=110), goal="activity")
    context, sources = svc.confirmed_feedback_context("sleep")
    assert len(context) == 10 and ids[0] not in sources
    assert sources[0] == ids[-1] and context[0]["assessment"] == "fits"
    assert all(item["goal_category"] == "sleep" for item in context)
    _, other_uid = client_for(session, field_cipher, token="another-synthetic-device")
    other = ProductService(session, field_cipher, other_uid)
    foreign, _ = remember(other, start + timedelta(days=120))
    assert foreign not in svc.confirmed_feedback_context("sleep")[1]


def test_updated_feedback_stops_pending_proposal_and_changes_next_context(session, field_cipher):
    client, uid = client_for(session, field_cipher)
    svc = ProductService(session, field_cipher, uid)
    source, _ = remember(svc, datetime(2026, 8, 1, tzinfo=UTC))
    provider = Capture()
    setup_ai(client, provider)
    allow(client)
    proposed = client.post("/v3/experiments/propose", json=rid()).json()
    current = svc.read(svc.row("experiment", source))
    svc.feedback(source, current["revision"], "fits", True)
    session.commit()
    assert svc.read(svc.row("experiment", proposed["id"]))["status"] == "stopped"
    assert svc.confirmed_feedback_context("sleep")[0][0]["assessment"] == "fits"
