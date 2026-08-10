import argparse
import json
import re
import time
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bodyos_api.bodyos import BodyOSService, ConversationRequest
from bodyos_api.config import get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import make_engine
from bodyos_api.group_coach import FeishuGroupDispatcher, GroupCoachScheduler
from bodyos_api.models import DailyFeature, HealthSample, OutboxEvent, User
from bodyos_api.runtime import get_model_gateway

RAW_RETENTION_DAYS = 30
AGGREGATE_RETENTION_MONTHS = 13
STUDY_CHECKPOINTS = {
    3: "stage_summary",
    8: "stage_summary",
    15: "stage_summary",
    16: "full_reconciliation",
}
_SHARED_CITATION_RE = re.compile(
    r"《(?:控糖革命|百岁人生行动手册|睡眠优化完全指南：科学与实践)》"
    r"[，,\s]*第\s*\d{1,5}\s*页"
)


def _weekly_public_answer(service: BodyOSService, question: str) -> str:
    result = service.handle("", ConversationRequest(channel="group", text=question))
    if result.route in {"deterministic", "deterministic_public"}:
        raise RuntimeError("weekly public answer unavailable")
    if _SHARED_CITATION_RE.search(result.text) is None:
        raise RuntimeError("weekly public answer unavailable")
    return result.text


def _subtract_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(value.day, 28)
    return date(year, month, day)


def run_once(session: Session, *, now: datetime, study_start: date | None) -> dict[str, int]:
    raw_cutoff = now - timedelta(days=RAW_RETENTION_DAYS)
    raw_deleted = session.execute(delete(HealthSample).where(HealthSample.end_at < raw_cutoff))
    aggregate_cutoff = _subtract_months(now.date(), AGGREGATE_RETENTION_MONTHS).isoformat()
    aggregates_deleted = session.execute(
        delete(DailyFeature).where(DailyFeature.feature_date < aggregate_cutoff)
    )

    checkpoint_events = 0
    if study_start is not None:
        day = (now.date() - study_start).days + 1
        action = STUDY_CHECKPOINTS.get(day)
        if action:
            event_type = f"owner_study_day_{day}_{action}"
            for user_id in session.scalars(
                select(User.fitcrew_user_id).where(User.status == "active")
            ):
                exists = session.scalar(
                    select(OutboxEvent.id).where(
                        OutboxEvent.fitcrew_user_id == user_id,
                        OutboxEvent.event_type == event_type,
                    )
                )
                if exists is None:
                    session.add(
                        OutboxEvent(
                            fitcrew_user_id=user_id,
                            destination="ios_bridge" if day == 16 else "bodyos_dm",
                            event_type=event_type,
                            payload_json=json.dumps(
                                {"study_day": day, "action": action}, separators=(",", ":")
                            ),
                        )
                    )
                    checkpoint_events += 1
    session.commit()
    return {
        "raw_deleted": int(raw_deleted.rowcount or 0),
        "aggregates_deleted": int(aggregates_deleted.rowcount or 0),
        "checkpoint_events": checkpoint_events,
    }


def run_worker_cycle(
    session: Session,
    *,
    now: datetime,
    settings,
    dispatcher,
    run_maintenance: bool,
    study_start: date | None,
) -> dict[str, int]:
    enqueued = GroupCoachScheduler(session, settings).enqueue_due(now)
    delivery = dispatcher.dispatch_due(now)
    maintenance = (
        run_once(session, now=now, study_start=study_start)
        if run_maintenance
        else {"raw_deleted": 0, "aggregates_deleted": 0, "checkpoint_events": 0}
    )
    return {
        "group_events_enqueued": enqueued,
        "group_events_delivered": delivery["delivered"],
        "group_events_retried": delivery["retried"],
        "group_events_failed": delivery["failed"],
        **maintenance,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run content-free BodyOS maintenance jobs")
    parser.add_argument("command", choices=("once", "loop"), nargs="?", default="once")
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--maintenance-seconds", type=int, default=21_600)
    args = parser.parse_args()
    settings = get_settings()
    study_start = (
        date.fromisoformat(settings.study_start_date) if settings.study_start_date else None
    )
    engine = make_engine(settings.database_url)
    encoded_key = settings.encryption_key.get_secret_value()
    if not encoded_key:
        raise RuntimeError("BODYOS_ENCRYPTION_KEY is required")
    cipher = FieldCipher.from_base64(encoded_key)
    gateway = get_model_gateway()
    last_maintenance_at: datetime | None = None
    while True:
        now = datetime.now(UTC)
        run_maintenance = (
            last_maintenance_at is None
            or (now - last_maintenance_at).total_seconds() >= max(300, args.maintenance_seconds)
        )
        with Session(engine) as session:
            service = BodyOSService(session, cipher, gateway)
            dispatcher = FeishuGroupDispatcher(
                session,
                settings,
                weekly_answer=lambda question, service=service: _weekly_public_answer(
                    service, question
                ),
            )
            counts = run_worker_cycle(
                session,
                now=now,
                settings=settings,
                dispatcher=dispatcher,
                run_maintenance=run_maintenance,
                study_start=study_start,
            )
        if run_maintenance:
            last_maintenance_at = now
        print(json.dumps({"job": "maintenance", **counts}, separators=(",", ":")), flush=True)
        if args.command == "once":
            break
        time.sleep(max(30, args.interval_seconds))


if __name__ == "__main__":
    main()
