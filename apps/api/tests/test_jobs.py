from datetime import UTC, date, datetime

import pytest
from bodyos_api.bodyos import ConversationReply
from bodyos_api.config import Settings
from bodyos_api.dlp import render_public_knowledge_answer
from bodyos_api.jobs import _weekly_public_answer, run_once, run_worker_cycle
from bodyos_api.models import DailyFeature, OutboxEvent, User
from sqlalchemy import func, select
from sqlalchemy.orm import Session

OWNER = "11111111-1111-4111-8111-111111111111"


class RecordingDispatcher:
    def __init__(self):
        self.calls: list[datetime] = []

    def dispatch_due(self, now: datetime) -> dict[str, int]:
        self.calls.append(now)
        return {"delivered": 1, "retried": 0, "failed": 0}


class StubWeeklyService:
    def __init__(self, reply: ConversationReply):
        self.reply = reply

    def handle(self, fitcrew_user_id: str, request):
        del fitcrew_user_id, request
        return self.reply


def test_weekly_worker_accepts_only_a_reviewed_public_knowledge_answer() -> None:
    reviewed_answer = render_public_knowledge_answer("glucose_coaching", "控糖革命", 12)
    assert (
        _weekly_public_answer(
            StubWeeklyService(
                ConversationReply(reviewed_answer, "deterministic_public_knowledge")
            ),
            "公共问题",
        )
        == reviewed_answer
    )
    for route in ("deterministic", "deterministic_public"):
        with pytest.raises(RuntimeError, match="weekly public answer unavailable"):
            _weekly_public_answer(
                StubWeeklyService(ConversationReply("个性化健康建议请私聊 BodyOS。", route)),
                "公共问题",
            )
    with pytest.raises(RuntimeError, match="weekly public answer unavailable"):
        _weekly_public_answer(
            StubWeeklyService(ConversationReply("没有引用的公共回答", "deterministic_public")),
            "公共问题",
        )


def test_maintenance_enforces_aggregate_retention_and_idempotent_day16_event(
    session: Session,
) -> None:
    session.add(User(fitcrew_user_id=OWNER))
    session.add(
        DailyFeature(
            fitcrew_user_id=OWNER,
            feature_date="2025-06-30",
            feature_set="daily.v1",
            payload_nonce=b"nonce",
            payload_ciphertext=b"ciphertext",
            quality_status="partial",
            algorithm_version="features.v1",
        )
    )
    session.commit()
    now = datetime(2026, 8, 1, 8, tzinfo=UTC)

    first = run_once(session, now=now, study_start=date(2026, 7, 17))
    second = run_once(session, now=now, study_start=date(2026, 7, 17))

    assert first == {"raw_deleted": 0, "aggregates_deleted": 1, "checkpoint_events": 1}
    assert second == {"raw_deleted": 0, "aggregates_deleted": 0, "checkpoint_events": 0}
    event = session.scalar(select(OutboxEvent))
    assert event is not None
    assert event.destination == "ios_bridge"
    assert event.event_type == "owner_study_day_16_full_reconciliation"
    assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 1


def test_worker_cycle_enqueues_and_dispatches_group_events_without_running_maintenance(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    settings = Settings(
        proactive_group_enabled=True,
        feishu_allowed_group_id="oc_test_group",
    )
    dispatcher = RecordingDispatcher()

    counts = run_worker_cycle(
        session,
        now=now,
        settings=settings,
        dispatcher=dispatcher,
        run_maintenance=False,
        study_start=None,
    )

    assert counts == {
        "group_events_enqueued": 1,
        "group_events_delivered": 1,
        "group_events_retried": 0,
        "group_events_failed": 0,
        "raw_deleted": 0,
        "aggregates_deleted": 0,
        "checkpoint_events": 0,
    }
    assert dispatcher.calls == [now]


def test_worker_cycle_can_run_maintenance_without_changing_group_counts(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 2, 0, tzinfo=UTC)
    settings = Settings(proactive_group_enabled=False)
    dispatcher = RecordingDispatcher()

    counts = run_worker_cycle(
        session,
        now=now,
        settings=settings,
        dispatcher=dispatcher,
        run_maintenance=True,
        study_start=None,
    )

    assert counts["group_events_enqueued"] == 0
    assert counts["group_events_delivered"] == 1
    assert counts["raw_deleted"] == 0
