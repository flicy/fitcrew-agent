from datetime import UTC, datetime

from bodyos_api.bodyos import BodyOSService, ConversationRequest
from bodyos_api.crypto import FieldCipher
from bodyos_api.models import DailyFeature, DeviceBinding, HealthSample, User
from sqlalchemy.orm import Session

USER_ID = "11111111-1111-4111-8111-111111111111"


class RecordingGateway:
    def __init__(self):
        self.envelopes: list[dict] = []

    def respond(self, envelope: dict):
        self.envelopes.append(envelope)
        return type("Reply", (), {"text": "从一顿饭的进食顺序开始。", "route": "codex"})()


def seed_feature(session: Session, cipher: FieldCipher) -> None:
    session.add(User(fitcrew_user_id=USER_ID))
    encrypted = cipher.encrypt_json(
        {
            "glucose": {"mean_mg_dl": 101.2, "coefficient_of_variation": 0.12},
            "data_quality": {"glucose_completeness": 0.92},
        },
        aad=f"feature:{USER_ID}:2026-08-01:daily_health_v1",
    )
    session.add(
        DailyFeature(
            fitcrew_user_id=USER_ID,
            feature_date="2026-08-01",
            feature_set="daily_health_v1",
            payload_nonce=encrypted.nonce,
            payload_ciphertext=encrypted.ciphertext,
            quality_status="good",
            algorithm_version="features.v1",
        )
    )
    session.commit()


def test_group_never_calls_model_and_only_returns_a_fixed_behavior_token(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    service = BodyOSService(session, field_cipher, gateway)

    result = service.handle(
        USER_ID,
        ConversationRequest(channel="group", text="我的餐后血糖今天有 10.2"),
    )

    assert result.route == "deterministic"
    assert result.text == "个性化健康建议请私聊 BodyOS。"
    assert gateway.envelopes == []
    assert "10.2" not in result.text


def test_group_contact_request_returns_only_a_fixed_bodyos_join_route(
    session: Session, field_cipher: FieldCipher
) -> None:
    gateway = RecordingGateway()
    raw_group_text = "请提供 BodyOS 的联系方式；我刚测到血糖 10.2，想加入。"

    result = BodyOSService(session, field_cipher, gateway).handle(
        USER_ID,
        ConversationRequest(channel="group", text=raw_group_text),
    )

    assert result.route == "deterministic"
    assert result.text == "请私聊 BodyOS 并发送“加入 BodyOS”，获取加入流程。"
    assert gateway.envelopes == []
    assert "10.2" not in result.text
    assert raw_group_text not in result.text


def test_dm_sends_only_deterministic_features_not_raw_question_or_identity(
    session: Session, field_cipher: FieldCipher
) -> None:
    seed_feature(session, field_cipher)
    gateway = RecordingGateway()
    raw_question = "我叫 Chris，鱼跃餐后血糖 10.2，该怎么办？"

    result = BodyOSService(session, field_cipher, gateway).handle(
        USER_ID, ConversationRequest(channel="dm", text=raw_question)
    )

    assert result.route == "codex"
    envelope = gateway.envelopes[0]
    rendered = str(envelope)
    assert envelope["intent"] == "glucose_coaching"
    assert envelope["features"]["glucose"]["mean_mg_dl"] == 101.2
    assert raw_question not in rendered
    assert "Chris" not in rendered
    assert "10.2" not in rendered
    assert USER_ID not in rendered


def test_sync_status_envelope_contains_only_connection_time_and_category_coverage(
    session: Session, field_cipher: FieldCipher
) -> None:
    session.add(User(fitcrew_user_id=USER_ID))
    session.add(
        DeviceBinding(
            fitcrew_user_id=USER_ID,
            device_public_id="owner-iphone",
            token_hash="token-hash",
            last_sync_at=datetime(2026, 8, 3, 0, 43, 26, tzinfo=UTC),
        )
    )
    for index, kind in enumerate(("blood_glucose", "sleep_deep", "step_count")):
        session.add(
            HealthSample(
                fitcrew_user_id=USER_ID,
                sync_batch_id="batch-id",
                sample_id=f"sample-{index}",
                kind=kind,
                start_at=datetime(2026, 8, 3, tzinfo=UTC),
                end_at=datetime(2026, 8, 3, tzinfo=UTC),
                original_unit="redacted",
                normalized_unit="redacted",
                source="HealthKit",
                value_nonce=b"nonce",
                value_ciphertext=b"ciphertext",
            )
        )
    session.commit()

    envelope = BodyOSService(session, field_cipher, RecordingGateway()).build_envelope(
        USER_ID,
        "请只返回健康数据同步状态、最新同步时间和数据类别覆盖，不要返回任何原始健康数值。",
    )

    assert envelope == {
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
