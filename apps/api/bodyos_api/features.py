from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, stdev
from typing import Any


@dataclass(frozen=True, slots=True)
class DecryptedSample:
    kind: str
    start_at: datetime
    end_at: datetime
    value_mg_dl: float


def _values(samples: list[DecryptedSample], kind: str) -> list[float]:
    return [sample.value_mg_dl for sample in samples if sample.kind == kind]


def _mean_or_none(values: list[float]) -> float | None:
    return mean(values) if values else None


def _sum_or_none(values: list[float], divisor: float = 1) -> float | None:
    return sum(values) / divisor if values else None


def _sleep_hours(samples: list[DecryptedSample]) -> float | None:
    if not samples or any(s.end_at < s.start_at for s in samples):
        return None
    intervals = sorted((s.start_at, s.end_at) for s in samples)
    start, end = intervals[0]
    seconds = 0.0
    for next_start, next_end in intervals[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            seconds += (end - start).total_seconds()
            start, end = next_start, next_end
    return (seconds + (end - start).total_seconds()) / 3600


def compute_daily_features(
    samples: list[DecryptedSample], *, expected_glucose_interval_minutes: int = 5
) -> dict[str, Any]:
    glucose_samples = [sample for sample in samples if sample.kind == "blood_glucose"]
    seen: set[tuple[str, datetime, float]] = set()
    duplicate_count = 0
    unique_glucose: list[DecryptedSample] = []
    for sample in glucose_samples:
        key = (sample.kind, sample.start_at, sample.value_mg_dl)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        unique_glucose.append(sample)

    values = [sample.value_mg_dl for sample in unique_glucose]
    expected_points = max(1, (24 * 60) // expected_glucose_interval_minutes)
    glucose: dict[str, float | int | None] = {
        "count": len(values),
        "mean_mg_dl": mean(values) if values else None,
        "min_mg_dl": min(values) if values else None,
        "max_mg_dl": max(values) if values else None,
        "stdev_mg_dl": stdev(values) if len(values) > 1 else 0.0 if values else None,
        "coefficient_of_variation": None,
    }
    if values and glucose["mean_mg_dl"]:
        glucose["coefficient_of_variation"] = float(glucose["stdev_mg_dl"] or 0.0) / float(
            glucose["mean_mg_dl"]
        )

    sleep_kinds = {"sleep_deep", "sleep_rem", "sleep_core", "sleep_asleep"}
    sleep_samples = [s for s in samples if s.kind in sleep_kinds]
    workouts = _values(samples, "workout")

    return {
        "algorithm_version": "features.v3",
        "glucose": glucose,
        "sleep": {
            "total_hours": _sleep_hours(sleep_samples),
            "deep_hours": _sleep_hours([s for s in sleep_samples if s.kind == "sleep_deep"]),
            "rem_hours": _sleep_hours([s for s in sleep_samples if s.kind == "sleep_rem"]),
            "core_hours": _sleep_hours([s for s in sleep_samples if s.kind == "sleep_core"]),
        },
        "activity": {
            "steps": _sum_or_none(_values(samples, "step_count")),
            "active_energy_kcal": _sum_or_none(_values(samples, "active_energy")),
            "stand_hours": _sum_or_none(_values(samples, "stand_hours")),
            "workout_count": len(workouts) if workouts else None,
            "workout_minutes": _sum_or_none(workouts, 60),
        },
        "recovery": {
            "hrv_ms_mean": _mean_or_none(_values(samples, "heart_rate_variability")),
            "resting_heart_rate_bpm_mean": _mean_or_none(_values(samples, "resting_heart_rate")),
        },
        "data_quality": {
            "duplicate_count": duplicate_count,
            "invalid_sleep_intervals": sum(s.end_at < s.start_at for s in sleep_samples),
            "expected_glucose_points": expected_points,
            "glucose_completeness": min(1.0, len(values) / expected_points),
            "sample_counts": {
                kind: sum(1 for sample in samples if sample.kind == kind)
                for kind in sorted({sample.kind for sample in samples})
            },
        },
    }


def normalize_cached_features(payload: dict[str, Any]) -> dict[str, Any]:
    """Mask unsupported legacy values without mutating stored historical evidence."""
    result = deepcopy(payload)
    counts = result.get("data_quality", {}).get("sample_counts", {})
    fields = {
        "sleep": {
            "total_hours": ("sleep_deep", "sleep_rem", "sleep_core", "sleep_asleep"),
            "deep_hours": ("sleep_deep",),
            "rem_hours": ("sleep_rem",),
            "core_hours": ("sleep_core",),
        },
        "activity": {
            "steps": ("step_count",),
            "active_energy_kcal": ("active_energy",),
            "stand_hours": ("stand_hours",),
            "workout_count": ("workout",),
            "workout_minutes": ("workout",),
        },
        "recovery": {
            "hrv_ms_mean": ("heart_rate_variability",),
            "resting_heart_rate_bpm_mean": ("resting_heart_rate",),
        },
    }
    for group, metrics in fields.items():
        for metric, kinds in metrics.items():
            if metric in result.get(group, {}) and not any(
                counts.get(kind, 0) > 0 for kind in kinds
            ):
                result[group][metric] = None
    result["read_policy_version"] = "missing-values.v1"
    return result
