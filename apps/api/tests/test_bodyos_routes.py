import hashlib
import hmac
from datetime import UTC, datetime

from bodyos_api.app import create_app
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.dlp import render_public_knowledge_answer
from bodyos_api.knowledge import KnowledgeService
from bodyos_api.model_gateway import HarnessFailure
from bodyos_api.models import (
    Consent,
    DeviceBinding,
    HealthSample,
    IdentityBinding,
    SyncBatch,
    User,
)
from bodyos_api.runtime import get_field_cipher, get_model_gateway
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

USER_ID = "11111111-1111-4111-8111-111111111111"
SUBJECT = "ou_private_owner"
SECOND_USER_ID = "22222222-2222-4222-8222-222222222222"
SECOND_SUBJECT = "ou_private_invited"


class RecordingGateway:
    def __init__(self):
        self.envelopes: list[dict] = []

    def respond(self, envelope: dict):
        self.envelopes.append(envelope)
        text = "安全建议"
        if envelope.get("schema_version") == "bodyos-public.v2" and envelope.get("knowledge"):
            text = "安全建议（《控糖革命》第12页）。"
        return type(
            "Reply",
            (),
            {"text": text, "route": "codex"},
        )()


class FailingGateway:
    def respond(self, envelope: dict):
        del envelope
        raise HarnessFailure("provider unavailable")


def client_for(session: Session, cipher: FieldCipher, gateway: RecordingGateway) -> TestClient:
    settings = Settings(
        internal_token="bodyos-internal-secret",
        model_proxy_token="model-proxy-secret",
        identity_pepper="identity-pepper",
    )
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_field_cipher] = lambda: cipher
    app.dependency_overrides[get_model_gateway] = lambda: gateway
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def seed_identity(
    session: Session,
    cipher: FieldCipher,
    *,
    user_id: str = USER_ID,
    subject: str = SUBJECT,
    binding_id: str = "binding-1",
    verified: bool = True,
    user_status: str = "active",
) -> None:
    session.add(User(fitcrew_user_id=user_id, status=user_status))
    subject_hash = hmac.new(
        b"identity-pepper", subject.encode(), hashlib.sha256
    ).hexdigest()
    encrypted = cipher.encrypt_json({"subject": subject}, aad=f"identity:{binding_id}")
    session.add(
        IdentityBinding(
            id=binding_id,
            fitcrew_user_id=user_id,
            provider="feishu",
            subject_hash=subject_hash,
            encrypted_subject=encrypted.nonce + encrypted.ciphertext,
            verified_at=datetime.now(UTC) if verified else None,
        )
    )
    session.commit()


def seed_private_sync_status(
    session: Session,
    *,
    user_id: str,
    prefix: str,
    kinds: list[str],
    synced_at: datetime,
) -> None:
    device_id = f"{prefix}-0000-4000-8000-000000000001"
    consent_id = f"{prefix}-0000-4000-8000-000000000002"
    batch_id = f"{prefix}-0000-4000-8000-000000000003"
    session.add(
        DeviceBinding(
            id=device_id,
            fitcrew_user_id=user_id,
            device_public_id=f"{prefix}-iphone",
            token_hash=f"{prefix}-token-hash",
            last_sync_at=synced_at,
        )
    )
    session.add(
        Consent(
            id=consent_id,
            fitcrew_user_id=user_id,
            category="private_status_test",
            purpose="private_coaching",
            granted=True,
            receipt_version="test-v1",
            granted_at=synced_at,
        )
    )
    session.add(
        SyncBatch(
            id=batch_id,
            fitcrew_user_id=user_id,
            batch_id=f"{prefix}-0000-4000-8000-000000000004",
            device_binding_id=device_id,
            consent_id=consent_id,
            source="test-source",
            timezone="Asia/Shanghai",
        )
    )
    for index, kind in enumerate(kinds, start=5):
        sample_id = f"{prefix}-0000-4000-8000-0000000000{index}"
        session.add(
            HealthSample(
                id=sample_id,
                fitcrew_user_id=user_id,
                sync_batch_id=batch_id,
                sample_id=sample_id,
                kind=kind,
                start_at=synced_at,
                end_at=synced_at,
                original_unit="private",
                normalized_unit="private",
                source="test-source",
                value_nonce=b"opaque-nonce",
                value_ciphertext=b"opaque-ciphertext",
            )
        )
    session.commit()


def seed_shared_glucose_book(session: Session, cipher: FieldCipher) -> None:
    if session.get(User, USER_ID) is None:
        session.add(User(fitcrew_user_id=USER_ID))
        session.commit()
    service = KnowledgeService(session, cipher)
    source = service.import_pages(
        fitcrew_user_id=USER_ID,
        title="控糖革命",
        author="Jessie Inchauspé",
        content_hash="8" * 64,
        rights_status="user_provided_internal_expert_use",
        pages={12: "进餐顺序可能影响餐后葡萄糖曲线。"},
    )
    service.publish_private_source(
        source.id,
        expected_owner_id=USER_ID,
        reviewer_role="owner_editor",
        rationale="approved for internal expert summaries",
        applicability="general lifestyle education",
        rights_confirmation="owner confirmed closed BodyOS shared expert use",
    )


def test_envelope_endpoint_maps_feishu_identity_but_returns_no_identifier_or_raw_text(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher)
    raw_text = "我的鱼跃血糖是 10.2，我该怎么办？"

    response = client_for(session, field_cipher, RecordingGateway()).post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "dm", "text": raw_text},
    )

    assert response.status_code == 200
    rendered = response.text
    assert response.json()["mode"] == "model"
    assert response.json()["envelope"]["intent"] == "glucose_coaching"
    assert SUBJECT not in rendered
    assert USER_ID not in rendered
    assert raw_text not in rendered
    assert "10.2" not in rendered


def test_group_envelope_is_a_fixed_token_and_never_calls_gateway(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher)
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "group", "text": "血糖 10.2"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "deterministic",
        "reply": "个性化健康建议请私聊 BodyOS。",
        "envelope": {
            "schema_version": "bodyos-group.v1",
            "channel": "group",
            "behavior_token": "private_coaching",
        },
    }
    assert gateway.envelopes == []


def test_general_group_question_returns_a_checked_public_answer_envelope(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_shared_glucose_book(session, field_cipher)
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={
            "provider": "feishu",
            "subject": SUBJECT,
            "channel": "group",
            "text": "晚饭后散步为什么有助于控糖？",
        },
    )

    assert response.status_code == 200
    reviewed = render_public_knowledge_answer("glucose_coaching", "控糖革命", 12)
    assert response.json() == {
        "mode": "group_public",
        "reply": reviewed,
        "envelope": {
            "schema_version": "bodyos-group-answer.v1",
            "channel": "group",
            "reply": reviewed,
        },
    }
    assert gateway.envelopes == []


def test_group_endpoints_return_public_fallback_when_model_is_unavailable(
    session: Session, field_cipher: FieldCipher
) -> None:
    client = client_for(session, field_cipher, FailingGateway())
    payload = {
        "provider": "feishu",
        "subject": SUBJECT,
        "channel": "group",
        "text": "晚饭后散步为什么有助于控糖？",
    }

    envelope_response = client.post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json=payload,
    )
    reply_response = client.post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json=payload,
    )

    assert envelope_response.status_code == 200
    assert envelope_response.json()["mode"] == "group_public"
    assert envelope_response.json()["reply"] != "个性化健康建议请私聊 BodyOS。"
    assert envelope_response.json()["envelope"]["schema_version"] == "bodyos-group-answer.v1"
    assert reply_response.json()["mode"] == "group_public"
    assert reply_response.json()["route"] == "deterministic_public"


def test_proxy_rejects_freeform_public_group_answers(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    seed_shared_glucose_book(session, field_cipher)
    import json

    envelope = {
        "schema_version": "bodyos-group-answer.v1",
        "channel": "group",
        "reply": "餐后舒适步行可以增加肌肉对葡萄糖的利用。",
    }
    response = client_for(session, field_cipher, gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer model-proxy-secret"},
        json={
            "model": "bodyos-codex",
            "messages": [
                {
                    "role": "user",
                    "content": "BODYOS_SANITIZED_ENVELOPE=" + json.dumps(envelope),
                }
            ],
        },
    )

    assert response.status_code == 403
    assert gateway.envelopes == []


def test_group_contact_request_is_a_fixed_join_token_and_never_calls_gateway(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher)
    gateway = RecordingGateway()
    raw_group_text = "@BodyOS 提供我 BodyOS 的联系方式；我的血糖是 10.2。"

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={
            "provider": "feishu",
            "subject": SUBJECT,
            "channel": "group",
            "text": raw_group_text,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "deterministic",
        "reply": "请私聊 BodyOS 并发送“加入 BodyOS”，获取加入流程。",
        "envelope": {
            "schema_version": "bodyos-group.v1",
            "channel": "group",
            "behavior_token": "contact_bodyos",
        },
    }
    assert gateway.envelopes == []
    assert "10.2" not in response.text
    assert raw_group_text not in response.text


def test_openai_compatible_proxy_routes_only_sanitized_dm_envelope(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    envelope = {
        "schema_version": "bodyos-model.v1",
        "intent": "glucose_coaching",
        "channel": "dm",
        "features": {"status": "insufficient_data"},
        "knowledge": [],
        "constraints": ["not_medical_diagnosis"],
    }
    import json

    response = client_for(session, field_cipher, gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer model-proxy-secret"},
        json={
            "model": "bodyos-codex",
            "messages": [
                {
                    "role": "user",
                    "content": "BODYOS_SANITIZED_ENVELOPE=" + json.dumps(envelope),
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "安全建议"
    assert gateway.envelopes == [envelope]


def test_openai_compatible_proxy_streams_only_sanitized_dm_envelope(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    envelope = {
        "schema_version": "bodyos-model.v1",
        "intent": "general_health_coaching",
        "channel": "dm",
        "features": {"status": "insufficient_data"},
        "knowledge": [],
        "constraints": ["not_medical_diagnosis"],
    }
    import json

    response = client_for(session, field_cipher, gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer model-proxy-secret"},
        json={
            "model": "bodyos-codex",
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": "BODYOS_SANITIZED_ENVELOPE=" + json.dumps(envelope),
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    chunks = [json.loads(event) for event in events[:-1]]
    assert events[-1] == "[DONE]"
    assert chunks[0]["object"] == "chat.completion.chunk"
    assert chunks[0]["choices"][0]["delta"] == {
        "role": "assistant",
        "content": "安全建议",
    }
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"
    assert gateway.envelopes == [envelope]


def test_sync_status_proxy_is_deterministic_and_never_calls_model(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    envelope = {
        "schema_version": "bodyos-model.v1",
        "intent": "sync_status",
        "channel": "dm",
        "features": {
            "connection_status": "connected",
            "latest_sync_at": "2026-08-03T00:43:26+00:00",
            "category_coverage": ["血糖", "睡眠", "健身与活动"],
        },
        "knowledge": [],
        "constraints": ["no_raw_health_values"],
    }
    import json

    response = client_for(session, field_cipher, gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer model-proxy-secret"},
        json={
            "model": "bodyos-codex",
            "messages": [
                {
                    "role": "user",
                    "content": "BODYOS_SANITIZED_ENVELOPE=" + json.dumps(envelope),
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == (
        "同步状态：已连接\n"
        "最新同步时间：2026-08-03T00:43:26+00:00\n"
        "数据类别覆盖：血糖、睡眠、健身与活动"
    )
    assert response.json()["bodyos_route"] == "deterministic"
    assert gateway.envelopes == []


def test_dm_sync_status_isolated_between_two_feishu_users(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher)
    seed_identity(
        session,
        field_cipher,
        user_id=SECOND_USER_ID,
        subject=SECOND_SUBJECT,
        binding_id="binding-2",
    )
    owner_synced_at = datetime(2026, 8, 3, 0, 43, 26, tzinfo=UTC)
    invited_synced_at = datetime(2026, 8, 4, 1, 2, 3, tzinfo=UTC)
    seed_private_sync_status(
        session,
        user_id=USER_ID,
        prefix="11111111",
        kinds=["blood_glucose", "sleep_asleep"],
        synced_at=owner_synced_at,
    )
    seed_private_sync_status(
        session,
        user_id=SECOND_USER_ID,
        prefix="22222222",
        kinds=["heart_rate_variability", "workout"],
        synced_at=invited_synced_at,
    )
    client = client_for(session, field_cipher, RecordingGateway())

    owner = client.post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "dm", "text": "同步状态"},
    )
    invited = client.post(
        "/v1/bodyos/envelope",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={
            "provider": "feishu",
            "subject": SECOND_SUBJECT,
            "channel": "dm",
            "text": "同步状态",
        },
    )

    assert owner.status_code == invited.status_code == 200
    owner_features = owner.json()["envelope"]["features"]
    invited_features = invited.json()["envelope"]["features"]
    assert owner_features == {
        "connection_status": "connected",
        "latest_sync_at": owner_synced_at.isoformat(),
        "category_coverage": ["血糖", "睡眠"],
    }
    assert invited_features == {
        "connection_status": "connected",
        "latest_sync_at": invited_synced_at.isoformat(),
        "category_coverage": ["心率与恢复", "健身与活动"],
    }
    assert "opaque" not in owner.text + invited.text
    assert SECOND_SUBJECT not in owner.text
    assert SUBJECT not in invited.text
    assert SECOND_USER_ID not in owner.text
    assert USER_ID not in invited.text


def test_proxy_rejects_raw_chat_even_with_valid_proxy_token(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    response = client_for(session, field_cipher, gateway).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer model-proxy-secret"},
        json={"model": "bodyos-codex", "messages": [{"role": "user", "content": "血糖10.2"}]},
    )

    assert response.status_code == 403
    assert gateway.envelopes == []


def test_reply_endpoint_returns_a_checked_public_group_answer_without_private_context(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    seed_shared_glucose_book(session, field_cipher)

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={
            "provider": "feishu",
            "subject": SUBJECT,
            "channel": "group",
            "text": "晚饭后散步为什么有助于控糖？",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "group_public",
        "reply": render_public_knowledge_answer("glucose_coaching", "控糖革命", 12),
        "route": "deterministic_public_knowledge",
    }
    assert gateway.envelopes == []


def test_reply_endpoint_fails_closed_for_third_person_health_context(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={
            "provider": "feishu",
            "subject": SUBJECT,
            "channel": "group",
            "text": "小王最近晚饭后犯困，和血糖有关吗？",
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "deterministic"
    assert response.json()["route"] == "deterministic"
    assert "私聊" in response.json()["reply"]
    assert gateway.envelopes == []


def test_reply_endpoint_returns_a_private_answer_without_identifiers_or_raw_values(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher)
    gateway = RecordingGateway()
    raw_text = "我的鱼跃血糖是 10.2，晚饭后困，怎么调整？"

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "dm", "text": raw_text},
    )

    assert response.status_code == 200
    assert response.json() == {"mode": "private", "reply": "安全建议", "route": "codex"}
    rendered = response.text
    assert SUBJECT not in rendered
    assert USER_ID not in rendered
    assert raw_text not in rendered
    assert "10.2" not in rendered
    assert gateway.envelopes[0]["schema_version"] == "bodyos-model.v1"


def test_reply_endpoint_keeps_sync_status_deterministic_and_user_isolated(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher)
    synced_at = datetime(2026, 8, 3, 0, 43, 26, tzinfo=UTC)
    seed_private_sync_status(
        session,
        user_id=USER_ID,
        prefix="11111111",
        kinds=["blood_glucose", "sleep_asleep"],
        synced_at=synced_at,
    )
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "dm", "text": "同步状态"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "mode": "private",
        "reply": (
            "同步状态：已连接\n"
            "最新同步时间：2026-08-03T00:43:26+00:00\n"
            "数据类别覆盖：血糖、睡眠"
        ),
        "route": "deterministic",
    }
    assert gateway.envelopes == []


def test_reply_endpoint_denies_an_unbound_private_identity_before_model_use(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={
            "provider": "feishu",
            "subject": "ou_unknown_user",
            "channel": "dm",
            "text": "今天睡眠怎么样？",
        },
    )

    assert response.status_code == 403
    assert gateway.envelopes == []


def test_reply_endpoint_denies_an_unverified_private_identity_before_model_use(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher, verified=False)
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "dm", "text": "睡眠建议"},
    )

    assert response.status_code == 403
    assert gateway.envelopes == []


def test_reply_endpoint_denies_an_inactive_private_user_before_model_use(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_identity(session, field_cipher, user_status="revoked")
    gateway = RecordingGateway()

    response = client_for(session, field_cipher, gateway).post(
        "/v1/bodyos/reply",
        headers={"X-BodyOS-Token": "bodyos-internal-secret"},
        json={"provider": "feishu", "subject": SUBJECT, "channel": "dm", "text": "睡眠建议"},
    )

    assert response.status_code == 403
    assert gateway.envelopes == []
