import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from bodyos_api.config import Settings
from bodyos_api.group_coach import GroupCoachScheduler
from bodyos_api.models import OutboxEvent
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def enabled_settings(**overrides) -> Settings:
    values = {
        "proactive_group_enabled": True,
        "feishu_allowed_group_id": "oc_test_group",
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
    assert json.loads(event.payload_json) == {"template_id": "morning_action"}


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
