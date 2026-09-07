"""Consent-filtered calendar-day observations, never a health score or model input."""

from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from math import isfinite
from zoneinfo import ZoneInfo

from sqlalchemy import select

from bodyos_api.crypto import EncryptedValue
from bodyos_api.features import DecryptedSample, compute_daily_features
from bodyos_api.models import HealthSample

METRICS = {
    "sleep": ({"sleep_asleep", "sleep_core", "sleep_deep", "sleep_rem"}, "小时"),
    "steps": ({"step_count"}, "步"),
    "hrv": ({"heart_rate_variability"}, "毫秒"),
}


def health_trends(session, cipher, user_id, categories, today, timezone):
    zone = ZoneInfo(timezone)
    end = datetime.fromisoformat(today).date()
    start = end - timedelta(days=89)
    window_start = datetime.combine(start, time.min, zone).astimezone(UTC)
    window_end = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC)
    allowed = set(categories) & set.union(*(kinds for kinds, _ in METRICS.values()))
    grouped = defaultdict(list)
    if allowed:
        rows = session.scalars(
            select(HealthSample).where(
                HealthSample.fitcrew_user_id == user_id,
                HealthSample.kind.in_(allowed),
                HealthSample.start_at < window_end,
                HealthSample.end_at >= window_start,
            )
        ).all()
        for row in rows:
            a = (
                row.start_at.replace(tzinfo=UTC)
                if row.start_at.tzinfo is None
                else row.start_at.astimezone(UTC)
            )
            b = (
                row.end_at.replace(tzinfo=UTC)
                if row.end_at.tzinfo is None
                else row.end_at.astimezone(UTC)
            )
            payload = cipher.decrypt_json(
                EncryptedValue(row.value_nonce, row.value_ciphertext),
                aad=f"{user_id}:{row.sample_id}",
            )
            value = float(payload["value"])
            first = max(start, a.astimezone(zone).date())
            last = first
            if row.kind in METRICS["sleep"][0] and b > a:
                last = min(end, (b - timedelta(microseconds=1)).astimezone(zone).date())
            for offset in range(max(0, (last - first).days + 1)):
                day = first + timedelta(days=offset)
                if day > end or (
                    row.kind not in METRICS["sleep"][0] and a.astimezone(zone).date() != day
                ):
                    continue
                left = datetime.combine(day, time.min, zone).astimezone(UTC)
                right = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC)
                if row.kind in METRICS["sleep"][0]:
                    a_day, b_day = max(a, left), min(b, right)
                else:
                    a_day, b_day = a, b
                grouped[day].append((row.kind, a_day, b_day, value, row.source))
    points = []
    for offset in range(90):
        day = start + timedelta(days=offset)
        metrics = {}
        for name, (kinds, unit) in METRICS.items():
            records = [r for r in grouped[day] if r[0] in kinds]
            sources = sorted({r[4] for r in records})
            value = None
            status = "not_authorized" if not kinds & allowed else "missing"
            if records:
                status = "partial"
                if any(not isfinite(r[3]) or r[3] < 0 or r[2] < r[1] for r in records):
                    status = "invalid"
                elif name != "sleep" and len(sources) > 1:
                    status = "source_conflict"
                else:
                    unique = {(r[0], r[1], r[2], r[3]) for r in records}
                    if name == "sleep":
                        samples = [DecryptedSample(*r) for r in unique]
                        value = compute_daily_features(samples)["sleep"]["total_hours"]
                    elif name == "steps":
                        intervals = sorted((r[1], r[2]) for r in unique)
                        if len(set(intervals)) != len(intervals) or any(
                            b[0] < a[1] for a, b in zip(intervals, intervals[1:], strict=False)
                        ):
                            status = "source_conflict"
                        else:
                            value = sum(r[3] for r in unique)
                    else:
                        value = sum(r[3] for r in unique) / len(unique)
            metrics[name] = {
                "value": round(value, 2) if value is not None else None,
                "unit": unit,
                "status": status,
                "sample_count": len(records),
                "sources": sources,
            }
        points.append({"date": day.isoformat(), "metrics": metrics})
    return {
        "window_end": today,
        "timezone": timezone,
        "points": points,
        "notice": (
            "来自当前获准上传的健康样本，按日历日汇总；有样本也不保证全天覆盖。"
            "来源冲突或缺失不填零，不用于诊断或证明行动效果。"
        ),
    }
