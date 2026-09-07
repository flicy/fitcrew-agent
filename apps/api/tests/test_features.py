from datetime import UTC, datetime, timedelta

import pytest
from bodyos_api.features import DecryptedSample, compute_daily_features, normalize_cached_features


def test_daily_features_are_aggregates_without_raw_series() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    samples = [
        DecryptedSample(
            kind="blood_glucose",
            start_at=start + timedelta(minutes=index * 5),
            end_at=start + timedelta(minutes=index * 5),
            value_mg_dl=value,
        )
        for index, value in enumerate([90.0, 100.0, 110.0])
    ]

    features = compute_daily_features(samples, expected_glucose_interval_minutes=5)

    assert features["glucose"]["count"] == 3
    assert features["glucose"]["mean_mg_dl"] == pytest.approx(100.0)
    assert features["glucose"]["stdev_mg_dl"] == pytest.approx(10.0)
    assert features["glucose"]["coefficient_of_variation"] == pytest.approx(0.1)
    assert features["data_quality"]["duplicate_count"] == 0
    assert "raw_values" not in features["glucose"]


def test_daily_features_count_duplicate_timestamps() -> None:
    instant = datetime(2026, 8, 1, tzinfo=UTC)
    samples = [
        DecryptedSample("blood_glucose", instant, instant, 90.0),
        DecryptedSample("blood_glucose", instant, instant, 90.0),
    ]

    features = compute_daily_features(samples)

    assert features["data_quality"]["duplicate_count"] == 1


def test_daily_features_cover_apple_health_and_fitness_aggregates() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    samples = [
        DecryptedSample("sleep_deep", start, start + timedelta(hours=1), 3600.0),
        DecryptedSample("sleep_rem", start, start + timedelta(minutes=90), 5400.0),
        DecryptedSample("step_count", start, start, 4200.0),
        DecryptedSample("step_count", start + timedelta(hours=4), start, 1800.0),
        DecryptedSample("active_energy", start, start, 320.0),
        DecryptedSample("stand_hours", start, start, 8.0),
        DecryptedSample("workout", start, start + timedelta(minutes=45), 2700.0),
        DecryptedSample("heart_rate_variability", start, start, 42.0),
        DecryptedSample("heart_rate_variability", start, start, 48.0),
        DecryptedSample("resting_heart_rate", start, start, 60.0),
    ]

    features = compute_daily_features(samples)

    assert features["sleep"]["total_hours"] == pytest.approx(2.5)
    assert features["sleep"]["deep_hours"] == pytest.approx(1.0)
    assert features["activity"]["steps"] == pytest.approx(6000.0)
    assert features["activity"]["active_energy_kcal"] == pytest.approx(320.0)
    assert features["activity"]["stand_hours"] == pytest.approx(8.0)
    assert features["activity"]["workout_count"] == 1
    assert features["activity"]["workout_minutes"] == pytest.approx(45.0)
    assert features["recovery"]["hrv_ms_mean"] == pytest.approx(45.0)
    assert features["recovery"]["resting_heart_rate_bpm_mean"] == pytest.approx(60.0)
    assert "raw_values" not in features


def test_absent_health_categories_are_unknown_not_zero():
    features = compute_daily_features([])
    assert features["algorithm_version"] == "features.v2"
    assert all(value is None for value in features["sleep"].values())
    assert all(value is None for value in features["activity"].values())
    assert all(value is None for value in features["recovery"].values())
    assert features["data_quality"]["sample_counts"] == {}


def test_measured_zero_is_distinct_from_missing_category():
    instant = datetime(2026, 8, 1, tzinfo=UTC)
    features = compute_daily_features([DecryptedSample("step_count", instant, instant, 0.0)])
    assert features["activity"]["steps"] == 0
    assert features["activity"]["active_energy_kcal"] is None
    assert features["sleep"]["total_hours"] is None
    assert features["data_quality"]["sample_counts"] == {"step_count": 1}


def test_legacy_normalization_masks_unproven_values_without_rewriting_original():
    legacy = {
        "algorithm_version": "features.v1",
        "sleep": {"total_hours": 0, "deep_hours": 0},
        "activity": {"steps": 0, "active_energy_kcal": 0},
        "data_quality": {"sample_counts": {"step_count": 1}},
    }
    normalized = normalize_cached_features(legacy)
    assert normalized["sleep"]["total_hours"] is None
    assert normalized["activity"]["steps"] == 0
    assert normalized["activity"]["active_energy_kcal"] is None
    assert normalized["algorithm_version"] == "features.v1"
    assert legacy["sleep"]["total_hours"] == 0
    assert "read_policy_version" not in legacy
    assert normalize_cached_features({"sleep": {"total_hours": 8}})["sleep"]["total_hours"] is None
