import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from bodyos_api import group_coach as group_coach_module
from bodyos_api.config import Settings
from bodyos_api.dlp import sanitize_public_group_question
from bodyos_api.group_coach import FeishuDeliveryError, FeishuGroupDispatcher, GroupCoachScheduler
from bodyos_api.models import OutboxEvent
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def enabled_settings(**overrides) -> Settings:
    values = {
        "proactive_group_enabled": True,
        "feishu_allowed_group_id": "oc_test_group",
        "feishu_app_id": "cli_test_app",
        "feishu_app_secret": "test-secret",
        "group_timezone": "Asia/Shanghai",
        "group_morning_time": "09:00",
        "group_evening_time": "20:30",
        "group_weekly_weekday": 2,
        "group_weekly_time": "12:15",
        "group_quiet_start": "22:00",
        "group_quiet_end": "08:00",
    }
    values.update(overrides)
    return Settings(**values)


def test_scheduler_creates_each_due_shanghai_event_once(session: Session) -> None:
    now = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    scheduler = GroupCoachScheduler(session, enabled_settings())

    first = scheduler.enqueue_due(now)
    second = scheduler.enqueue_due(now)

    assert first == 1
    assert second == 0
    event = session.scalar(select(OutboxEvent))
    assert event is not None
    assert event.fitcrew_user_id is None
    assert event.destination == "feishu_group"
    assert event.event_type == "morning_action"
    assert event.idempotency_key == "feishu-group:morning_action:2026-08-12"
    assert event.status == "pending"
    assert event.attempt_count == 0
    assert event.scheduled_for == datetime(2026, 8, 12, 1, 0)
    assert json.loads(event.payload_json) == {"template_id": "morning_action"}


def test_scheduler_has_a_bounded_grace_window_for_worker_clock_drift(
    session: Session,
) -> None:
    settings = enabled_settings()

    inside_grace = GroupCoachScheduler(session, settings).enqueue_due(
        datetime(2026, 8, 12, 1, 4, tzinfo=UTC)
    )
    outside_grace = GroupCoachScheduler(session, settings).enqueue_due(
        datetime(2026, 8, 13, 1, 5, tzinfo=UTC)
    )

    assert inside_grace == 1
    assert outside_grace == 0
    event = session.scalar(select(OutboxEvent))
    assert event is not None
    assert event.scheduled_for == datetime(2026, 8, 12, 1, 0)


def test_scheduler_creates_evening_and_weekly_events_at_their_own_times(
    session: Session,
) -> None:
    scheduler = GroupCoachScheduler(session, enabled_settings())

    evening = scheduler.enqueue_due(datetime(2026, 8, 12, 12, 30, tzinfo=UTC))
    weekly = scheduler.enqueue_due(datetime(2026, 8, 12, 4, 15, tzinfo=UTC))

    assert evening == 1
    assert weekly == 1
    events = session.scalars(select(OutboxEvent).order_by(OutboxEvent.event_type)).all()
    assert {event.event_type for event in events} == {"evening_checkin", "weekly_expert"}
    weekly_event = next(event for event in events if event.event_type == "weekly_expert")
    assert json.loads(weekly_event.payload_json) == {"topic_id": "meal_order"}


def test_every_production_weekly_question_passes_the_public_question_gate() -> None:
    for question in group_coach_module._WEEKLY_QUESTIONS.values():
        assert sanitize_public_group_question(question) == question


def test_scheduler_does_not_enqueue_when_disabled_missing_group_or_inside_quiet_hours(
    session: Session,
) -> None:
    morning = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    quiet = datetime(2026, 8, 12, 23, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert GroupCoachScheduler(
        session, enabled_settings(proactive_group_enabled=False)
    ).enqueue_due(morning) == 0
    assert GroupCoachScheduler(
        session, enabled_settings(feishu_allowed_group_id="")
    ).enqueue_due(morning) == 0
    assert GroupCoachScheduler(session, enabled_settings()).enqueue_due(quiet) == 0
    assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 0


def test_scheduler_rejects_invalid_schedule_configuration_before_writing(
    session: Session,
) -> None:
    scheduler = GroupCoachScheduler(session, enabled_settings(group_morning_time="25:00"))

    try:
        scheduler.enqueue_due(datetime(2026, 8, 12, 1, 0, tzinfo=UTC))
    except ValueError as error:
        assert "group schedule" in str(error)
    else:
        raise AssertionError("invalid schedule was accepted")
    assert session.scalar(select(func.count()).select_from(OutboxEvent)) == 0


class FakeTransport:
    def __init__(self, error_code: str | None = None):
        self.error_code = error_code
        self.calls: list[dict[str, str]] = []

    def send_text(
        self,
        *,
        app_id: str,
        app_secret: str,
        group_id: str,
        text: str,
        idempotency_key: str,
    ) -> None:
        self.calls.append(
            {
                "app_id": app_id,
                "app_secret": app_secret,
                "group_id": group_id,
                "text": text,
                "idempotency_key": idempotency_key,
            }
        )
        if self.error_code:
            raise FeishuDeliveryError(self.error_code)


def test_dispatcher_sends_only_to_configured_group_and_marks_delivered(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    settings = enabled_settings()
    GroupCoachScheduler(session, settings).enqueue_due(now)
    transport = FakeTransport()

    counts = FeishuGroupDispatcher(
        session, settings, transport=transport, clock=lambda: now
    ).dispatch_due(now)

    assert counts == {"delivered": 1, "retried": 0, "failed": 0}
    event = session.scalar(select(OutboxEvent))
    assert event is not None
    assert event.status == "delivered"
    assert event.attempt_count == 1
    assert event.last_error_code is None
    assert transport.calls[0]["group_id"] == settings.feishu_allowed_group_id
    assert transport.calls[0]["idempotency_key"] == event.idempotency_key
    assert "小行动" in transport.calls[0]["text"]
    assert "oc_test_group" not in event.payload_json


def test_dispatcher_retries_three_times_without_persisting_message_or_provider_details(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    settings = enabled_settings()
    GroupCoachScheduler(session, settings).enqueue_due(now)
    transport = FakeTransport("network_unavailable")
    clock_now = [now]
    dispatcher = FeishuGroupDispatcher(
        session, settings, transport=transport, clock=lambda: clock_now[0]
    )

    first = dispatcher.dispatch_due(now)
    clock_now[0] = datetime(2026, 8, 12, 1, 1, tzinfo=UTC)
    second = dispatcher.dispatch_due(clock_now[0])
    clock_now[0] = datetime(2026, 8, 12, 1, 3, tzinfo=UTC)
    third = dispatcher.dispatch_due(clock_now[0])

    event = session.scalar(select(OutboxEvent))
    assert first == {"delivered": 0, "retried": 1, "failed": 0}
    assert second == {"delivered": 0, "retried": 1, "failed": 0}
    assert third == {"delivered": 0, "retried": 0, "failed": 1}
    assert event is not None
    assert event.status == "failed"
    assert event.attempt_count == 3
    assert event.last_error_code == "network_unavailable"
    assert json.loads(event.payload_json) == {"template_id": "morning_action"}
    assert "text" not in event.payload_json


def test_weekly_dispatch_uses_checked_expert_answer_and_fixed_fallback(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 4, 15, tzinfo=UTC)
    settings = enabled_settings()
    GroupCoachScheduler(session, settings).enqueue_due(now)
    transport = FakeTransport()
    questions: list[str] = []

    def expert_answer(question: str) -> str:
        questions.append(question)
        return "饭前先安排蔬菜有助于形成更均衡的进食顺序（《控糖革命》第12页）。"

    counts = FeishuGroupDispatcher(
        session,
        settings,
        transport=transport,
        weekly_answer=expert_answer,
        clock=lambda: now,
    ).dispatch_due(now)

    assert counts["delivered"] == 1
    assert questions == ["蔬菜和主食的进食顺序通常有什么意义？"]
    assert "《控糖革命》第12页" in transport.calls[0]["text"]


def test_weekly_dispatch_falls_back_without_exposing_model_error(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 4, 15, tzinfo=UTC)
    settings = enabled_settings()
    GroupCoachScheduler(session, settings).enqueue_due(now)
    transport = FakeTransport()

    def failed_answer(question: str) -> str:
        del question
        raise RuntimeError("HTTP 401 provider secret")

    counts = FeishuGroupDispatcher(
        session,
        settings,
        transport=transport,
        weekly_answer=failed_answer,
        clock=lambda: now,
    ).dispatch_due(now)

    assert counts["delivered"] == 1
    assert "HTTP" not in transport.calls[0]["text"]
    assert "provider" not in transport.calls[0]["text"]
    assert "一起讨论" in transport.calls[0]["text"]


def test_dispatcher_cancels_pending_delivery_when_proactive_coaching_is_disabled(
    session: Session,
) -> None:
    now = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    GroupCoachScheduler(session, enabled_settings()).enqueue_due(now)
    transport = FakeTransport()

    counts = FeishuGroupDispatcher(
        session,
        enabled_settings(proactive_group_enabled=False),
        transport=transport,
        clock=lambda: now,
    ).dispatch_due(now)

    event = session.scalar(select(OutboxEvent))
    assert counts["failed"] == 1
    assert transport.calls == []
    assert event is not None and event.status == "cancelled"
    assert event.last_error_code == "proactive_disabled"


def test_dispatcher_never_sends_a_stale_or_quiet_hour_event(session: Session) -> None:
    settings = enabled_settings()
    morning = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)
    GroupCoachScheduler(session, settings).enqueue_due(morning)
    quiet_now = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)
    session.add(
        OutboxEvent(
            fitcrew_user_id=None,
            destination="feishu_group",
            event_type="evening_checkin",
            payload_json=json.dumps({"template_id": "evening_checkin"}),
            status="pending",
            attempt_count=0,
            idempotency_key="quiet-event",
            scheduled_for=quiet_now,
            next_attempt_at=quiet_now,
        )
    )
    session.commit()
    transport = FakeTransport()

    stale_counts = FeishuGroupDispatcher(session, settings, transport=transport).dispatch_due(
        datetime(2026, 8, 12, 1, 5, tzinfo=UTC)
    )
    quiet_counts = FeishuGroupDispatcher(session, settings, transport=transport).dispatch_due(
        quiet_now
    )

    assert stale_counts["failed"] == 1
    assert quiet_counts["failed"] == 1
    assert transport.calls == []
    statuses = {
        event.idempotency_key: event.status
        for event in session.scalars(select(OutboxEvent))
    }
    assert statuses["feishu-group:morning_action:2026-08-12"] == "expired"
    assert statuses["quiet-event"] == "expired"


def test_dispatch_window_is_measured_from_configured_schedule_not_worker_observation(
    session: Session,
) -> None:
    settings = enabled_settings()
    observed_late = datetime(2026, 8, 12, 1, 4, 59, tzinfo=UTC)
    assert GroupCoachScheduler(session, settings).enqueue_due(observed_late) == 1
    transport = FakeTransport()

    counts = FeishuGroupDispatcher(session, settings, transport=transport).dispatch_due(
        datetime(2026, 8, 12, 1, 5, tzinfo=UTC)
    )

    event = session.scalar(select(OutboxEvent))
    assert counts["failed"] == 1
    assert transport.calls == []
    assert event is not None and event.status == "expired"


def test_dispatcher_rechecks_window_and_disable_immediately_before_transport(
    session: Session,
) -> None:
    scheduled = datetime(2026, 8, 12, 4, 15, tzinfo=UTC)
    settings = enabled_settings()
    assert GroupCoachScheduler(session, settings).enqueue_due(scheduled) == 1
    transport = FakeTransport()

    def delayed_answer(question: str) -> str:
        del question
        settings.proactive_group_enabled = False
        return "蔬菜和主食的顺序可作为一般讨论（《控糖革命》第12页）。"

    counts = FeishuGroupDispatcher(
        session,
        settings,
        transport=transport,
        weekly_answer=delayed_answer,
        clock=lambda: scheduled + timedelta(minutes=5, milliseconds=1),
    ).dispatch_due(scheduled + timedelta(minutes=4, seconds=59, milliseconds=500))

    event = session.scalar(select(OutboxEvent))
    assert counts["failed"] == 1
    assert transport.calls == []
    assert event is not None and event.status == "cancelled"
    assert event.last_error_code == "proactive_disabled"
