"""Read-through observations with an experiment's disclosed, unrevoked health scope."""

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from bodyos_api.health_trends import METRICS, health_trends
from bodyos_api.models import Consent

LABELS = {"sleep": "睡眠样本时长", "steps": "步数", "hrv": "心率变异性"}
CATEGORY_LABELS = {
    "sleep_asleep": "睡眠",
    "sleep_core": "核心睡眠",
    "sleep_deep": "深度睡眠",
    "sleep_rem": "快速眼动睡眠",
    "step_count": "步数",
    "heart_rate_variability": "心率变异性",
}
NOTICE = (
    "健康数据只作描述性观察，不发送给 AI。按实验开始时的时区统计完整日历日，"
    "与暂停区间重叠的整日排除；两窗各至少四天有可用数值才比较样本均值。"
    "部分样本不保证全天覆盖，变化不代表行动效果。"
)


def experiment_health_metric_labels(scope):
    return [
        LABELS[key] + "（可用健康样本）"
        for key, (kinds, _) in METRICS.items()
        if kinds & set(scope.values())
    ]


def experiment_health_scope(session, user_id):
    supported = set.union(*(kinds for kinds, _ in METRICS.values()))
    grants = session.scalars(
        select(Consent).where(
            Consent.fitcrew_user_id == user_id,
            Consent.category.in_(supported),
            Consent.purpose == "private_coaching",
            Consent.granted.is_(True),
            Consent.withdrawn_at.is_(None),
        )
    ).all()
    return {grant.id: grant.category for grant in grants}


def experiment_health_observation(session, cipher, user_id, item):
    scope = item.get("health_scope", {})
    if not scope or not item.get("accepted_at") or item["status"] != "completed":
        return None
    if item.get("result", {}).get("status") == "invalidated":
        return None
    active = experiment_health_scope(session, user_id)
    # A later grant must not silently expand or reactivate an old experiment's scope.
    categories = sorted({kind for key, kind in scope.items() if active.get(key) == kind})
    timezone = item["health_timezone"]
    zone = ZoneInfo(timezone)
    accepted = datetime.fromisoformat(item["accepted_at"]).astimezone(UTC)
    end = datetime.fromisoformat(item["ends_at"]).astimezone(UTC)
    start = datetime.fromisoformat(item["baseline_start"]).astimezone(UTC)
    pauses = [
        (datetime.fromisoformat(a).astimezone(UTC), datetime.fromisoformat(b).astimezone(UTC))
        for a, b in item.get("pause_intervals", [])
    ]
    points = health_trends(
        session,
        cipher,
        user_id,
        categories,
        end.astimezone(zone).date().isoformat(),
        timezone,
        start_date=start.astimezone(zone).date().isoformat(),
    )["points"]

    def in_window(point, left, right):
        day = datetime.fromisoformat(point["date"]).date()
        a = datetime.combine(day, time.min, zone).astimezone(UTC)
        b = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC)
        return left <= a and b <= right and not any(a < q and p < b for p, q in pauses)

    baseline = [point for point in points if in_window(point, start, accepted)]
    observation = [point for point in points if in_window(point, accepted, end)]
    metrics = []
    for key, (kinds, unit) in METRICS.items():
        if not kinds & set(scope.values()):
            continue
        allowed = bool(kinds & set(categories))

        def values(window, metric=key):
            return [
                p["metrics"][metric]["value"]
                for p in window
                if p["metrics"][metric]["status"] == "partial"
                and p["metrics"][metric]["value"] is not None
            ]

        before, after = values(baseline), values(observation)
        source_text = (
            "、".join(
                sorted(
                    {
                        source
                        for point in baseline + observation
                        if point["metrics"][key]["status"] == "partial"
                        for source in point["metrics"][key]["sources"]
                    }
                )
            )
            or "暂无可用来源"
        )
        enough = len(before) >= 4 and len(after) >= 4
        difference = (
            round(sum(after) / len(after) - sum(before) / len(before), 2) if enough else None
        )
        excluded = sum(
            p["metrics"][key]["status"] in {"source_conflict", "invalid"}
            for p in baseline + observation
        )
        summary = (
            (
                f"基线 {len(before)} 天、观察期 {len(after)} 天有可用样本。"
                + (
                    f"两窗样本日均值变化 {difference:+g} {unit}，仅作描述。"
                    if enough
                    else "两窗均需至少四天有可用数值，暂不比较。"
                )
            )
            if allowed
            else "本次实验对应的健康授权已撤回，不再显示该类观察值。"
        )
        if excluded:
            summary += f"另有 {excluded} 天因来源冲突或异常排除。"
        metrics.append(
            {
                "key": key,
                "label": LABELS[key],
                "unit": unit,
                "status": "not_authorized"
                if not allowed
                else "descriptive_only"
                if enough
                else "insufficient_data",
                "baseline_days": len(before),
                "observation_days": len(after),
                "excluded_days": excluded,
                "source_text": source_text,
                "baseline_dates": [
                    p["date"] for p in baseline if p["metrics"][key]["value"] is not None
                ],
                "observation_dates": [
                    p["date"] for p in observation if p["metrics"][key]["value"] is not None
                ],
                "change": difference,
                "summary": summary,
            }
        )
    return {"timezone": timezone, "notice": NOTICE, "metrics": metrics}
