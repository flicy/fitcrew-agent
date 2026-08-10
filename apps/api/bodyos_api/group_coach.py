"""Content-minimized scheduling for proactive BodyOS group coaching."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bodyos_api.config import Settings
from bodyos_api.dlp import SensitiveOutput, assert_public_group_answer
from bodyos_api.models import OutboxEvent

_WEEKLY_TOPICS = ("meal_order", "small_actions", "sleep_rhythm")
_FIXED_TEMPLATES = {
    "morning_action": (
        "早上好。今天你最想稳定完成的一个健康小行动是什么？可以从足够小的一步开始。"
    ),
    "evening_checkin": (
        "今晚的小行动完成了吗？可以回复：已完成、需要搭子，或行动小一点。"
    ),
}
_WEEKLY_QUESTIONS = {
    "meal_order": "蔬菜和主食的进食顺序通常有什么意义？",
    "small_actions": "训练计划中为什么可持续的小行动比短期冲刺更重要？",
    "sleep_rhythm": "睡眠通常怎样受稳定起床时间影响？",
}
_WEEKLY_FALLBACKS = {
    "meal_order": "本周一起讨论：一顿饭中的进食顺序，怎样帮助我们形成更稳定的饮食行动？",
    "small_actions": "本周一起讨论：怎样把健康目标变成今天可以完成的一小步？",
    "sleep_rhythm": "本周一起讨论：怎样用稳定作息支持睡眠与恢复？",
}
_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_DELIVERY_GRACE = timedelta(minutes=5)


class FeishuDeliveryError(RuntimeError):
    def __init__(self, code: str):
        safe_code = code if _ERROR_CODE_RE.fullmatch(code) else "delivery_failed"
        super().__init__(safe_code)
        self.code = safe_code


class FeishuTextTransport(Protocol):
    def send_text(
        self,
        *,
        app_id: str,
        app_secret: str,
        group_id: str,
        text: str,
        idempotency_key: str,
    ) -> None: ...


class HttpxFeishuTransport:
    def __init__(self, *, timeout_seconds: float = 10.0):
        self._timeout_seconds = timeout_seconds

    def send_text(
        self,
        *,
        app_id: str,
        app_secret: str,
        group_id: str,
        text: str,
        idempotency_key: str,
    ) -> None:
        if not app_id or not app_secret or not group_id or not idempotency_key:
            raise FeishuDeliveryError("configuration_missing")
        if len(idempotency_key) > 50:
            raise FeishuDeliveryError("invalid_idempotency_key")
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                token_response = client.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret},
                )
                token_payload = token_response.json()
                token = token_payload.get("tenant_access_token")
                if token_response.status_code != 200 or token_payload.get("code") != 0 or not token:
                    raise FeishuDeliveryError("authentication_failed")
                send_response = client.post(
                    "https://open.feishu.cn/open-apis/im/v1/messages",
                    params={"receive_id_type": "chat_id", "uuid": idempotency_key},
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "receive_id": group_id,
                        "msg_type": "text",
                        "content": json.dumps({"text": text}, ensure_ascii=False),
                    },
                )
                send_payload = send_response.json()
                if send_response.status_code != 200 or send_payload.get("code") != 0:
                    raise FeishuDeliveryError("send_rejected")
        except FeishuDeliveryError:
            raise
        except (httpx.HTTPError, TypeError, ValueError) as error:
            raise FeishuDeliveryError("network_unavailable") from error


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


def _within_delivery_window(current: datetime, scheduled: time) -> bool:
    scheduled_at = current.replace(
        hour=scheduled.hour,
        minute=scheduled.minute,
        second=0,
        microsecond=0,
    )
    elapsed = current - scheduled_at
    return timedelta(0) <= elapsed < _DELIVERY_GRACE


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

        due: list[tuple[str, dict[str, str], datetime]] = []
        if _within_delivery_window(local, morning):
            due.append(
                (
                    "morning_action",
                    {"template_id": "morning_action"},
                    local.replace(
                        hour=morning.hour, minute=morning.minute, second=0, microsecond=0
                    ),
                )
            )
        if _within_delivery_window(local, evening):
            due.append(
                (
                    "evening_checkin",
                    {"template_id": "evening_checkin"},
                    local.replace(
                        hour=evening.hour, minute=evening.minute, second=0, microsecond=0
                    ),
                )
            )
        if local.weekday() == self._settings.group_weekly_weekday and _within_delivery_window(
            local, weekly
        ):
            topic = _WEEKLY_TOPICS[local.isocalendar().week % len(_WEEKLY_TOPICS)]
            due.append(
                (
                    "weekly_expert",
                    {"topic_id": topic},
                    local.replace(
                        hour=weekly.hour, minute=weekly.minute, second=0, microsecond=0
                    ),
                )
            )

        created = 0
        for event_type, payload, scheduled_local in due:
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
                    scheduled_for=scheduled_local.astimezone(UTC),
                    next_attempt_at=now.astimezone(UTC),
                )
            )
            created += 1
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            return 0
        return created


class FeishuGroupDispatcher:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        transport: FeishuTextTransport | None = None,
        weekly_answer: Callable[[str], str] | None = None,
    ):
        self._session = session
        self._settings = settings
        self._transport = transport or HttpxFeishuTransport()
        self._weekly_answer = weekly_answer

    def dispatch_due(self, now: datetime) -> dict[str, int]:
        if now.tzinfo is None:
            raise ValueError("group dispatch requires timezone-aware time")
        try:
            local = now.astimezone(ZoneInfo(self._settings.group_timezone))
        except ZoneInfoNotFoundError as error:
            raise ValueError("invalid group schedule timezone") from error
        quiet_start = _parse_time(self._settings.group_quiet_start)
        quiet_end = _parse_time(self._settings.group_quiet_end)
        quiet = _inside_quiet_hours(
            local.time().replace(second=0, microsecond=0), quiet_start, quiet_end
        )
        now_utc = now.astimezone(UTC)
        counts = {"delivered": 0, "retried": 0, "failed": 0}
        events = self._session.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.destination == "feishu_group",
                OutboxEvent.status == "pending",
                or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now),
            )
            .order_by(OutboxEvent.scheduled_for, OutboxEvent.created_at)
            .with_for_update(skip_locked=True)
        ).all()
        for event in events:
            if not self._settings.proactive_group_enabled:
                event.status = "cancelled"
                event.last_error_code = "proactive_disabled"
                event.next_attempt_at = None
                counts["failed"] += 1
                continue
            if not self._settings.feishu_allowed_group_id.strip():
                event.status = "cancelled"
                event.last_error_code = "configuration_missing"
                event.next_attempt_at = None
                counts["failed"] += 1
                continue
            scheduled_for = event.scheduled_for
            if scheduled_for is not None and scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=UTC)
            if (
                quiet
                or scheduled_for is None
                or scheduled_for > now_utc
                or now_utc - scheduled_for >= _DELIVERY_GRACE
            ):
                event.status = "expired"
                event.last_error_code = "delivery_window_closed"
                event.next_attempt_at = None
                counts["failed"] += 1
                continue
            try:
                text = self._render(event)
                self._transport.send_text(
                    app_id=self._settings.feishu_app_id,
                    app_secret=self._settings.feishu_app_secret.get_secret_value(),
                    group_id=self._settings.feishu_allowed_group_id,
                    text=text,
                    idempotency_key=event.idempotency_key or event.id,
                )
            except FeishuDeliveryError as error:
                event.attempt_count += 1
                event.last_error_code = error.code
                if event.attempt_count >= 3:
                    event.status = "failed"
                    event.next_attempt_at = None
                    counts["failed"] += 1
                else:
                    event.next_attempt_at = now + timedelta(minutes=event.attempt_count)
                    counts["retried"] += 1
            else:
                event.attempt_count += 1
                event.status = "delivered"
                event.next_attempt_at = None
                event.last_error_code = None
                counts["delivered"] += 1
        self._session.commit()
        return counts

    def _render(self, event: OutboxEvent) -> str:
        try:
            payload = json.loads(event.payload_json)
        except (json.JSONDecodeError, TypeError) as error:
            raise FeishuDeliveryError("invalid_event") from error
        if not isinstance(payload, dict):
            raise FeishuDeliveryError("invalid_event")
        if event.event_type in _FIXED_TEMPLATES:
            if payload != {"template_id": event.event_type}:
                raise FeishuDeliveryError("invalid_event")
            return assert_public_group_answer(_FIXED_TEMPLATES[event.event_type])
        if event.event_type == "weekly_expert":
            topic = payload.get("topic_id")
            if set(payload) != {"topic_id"} or topic not in _WEEKLY_QUESTIONS:
                raise FeishuDeliveryError("invalid_event")
            if self._weekly_answer is not None:
                try:
                    return assert_public_group_answer(
                        self._weekly_answer(_WEEKLY_QUESTIONS[topic])
                    )
                except (Exception, SensitiveOutput):
                    pass
            return assert_public_group_answer(_WEEKLY_FALLBACKS[topic])
        raise FeishuDeliveryError("invalid_event")
