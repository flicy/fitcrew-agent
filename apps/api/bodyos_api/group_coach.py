"""Content-minimized scheduling for proactive BodyOS group coaching."""

import json
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.config import Settings
from bodyos_api.models import OutboxEvent

_WEEKLY_TOPICS = ("meal_order", "small_actions", "sleep_rhythm")


def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as error:
        raise ValueError("invalid group schedule time") from error


def _inside_quiet_hours(current: time, start: time, end: time) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


class GroupCoachScheduler:
    def __init__(self, session: Session, settings: Settings):
        self._session = session
        self._settings = settings

    def enqueue_due(self, now: datetime) -> int:
        if not self._settings.proactive_group_enabled:
            return 0
        if not self._settings.feishu_allowed_group_id.strip():
            return 0
        if now.tzinfo is None:
            raise ValueError("group schedule requires timezone-aware time")
        try:
            timezone = ZoneInfo(self._settings.group_timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("invalid group schedule timezone") from error
        morning = _parse_time(self._settings.group_morning_time)
        evening = _parse_time(self._settings.group_evening_time)
        weekly = _parse_time(self._settings.group_weekly_time)
        quiet_start = _parse_time(self._settings.group_quiet_start)
        quiet_end = _parse_time(self._settings.group_quiet_end)
        if not 0 <= self._settings.group_weekly_weekday <= 6:
            raise ValueError("invalid group schedule weekday")

        local = now.astimezone(timezone)
        minute = local.time().replace(second=0, microsecond=0)
        if _inside_quiet_hours(minute, quiet_start, quiet_end):
            return 0

        due: list[tuple[str, dict[str, str]]] = []
        if minute == morning:
            due.append(("morning_action", {"template_id": "morning_action"}))
        if minute == evening:
            due.append(("evening_checkin", {"template_id": "evening_checkin"}))
        if local.weekday() == self._settings.group_weekly_weekday and minute == weekly:
            topic = _WEEKLY_TOPICS[local.isocalendar().week % len(_WEEKLY_TOPICS)]
            due.append(("weekly_expert", {"topic_id": topic}))

        created = 0
        for event_type, payload in due:
            key = f"feishu-group:{event_type}:{local.date().isoformat()}"
            existing = self._session.scalar(
                select(OutboxEvent.id).where(OutboxEvent.idempotency_key == key)
            )
            if existing is not None:
                continue
            self._session.add(
                OutboxEvent(
                    fitcrew_user_id=None,
                    destination="feishu_group",
                    event_type=event_type,
                    payload_json=json.dumps(payload, separators=(",", ":"), sort_keys=True),
                    status="pending",
                    attempt_count=0,
                    idempotency_key=key,
                    scheduled_for=now.astimezone(UTC),
                    next_attempt_at=now.astimezone(UTC),
                )
            )
            created += 1
        self._session.commit()
        return created
