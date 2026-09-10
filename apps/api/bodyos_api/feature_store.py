from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.features import DecryptedSample, compute_daily_features
from bodyos_api.models import DailyFeature, HealthSample

FEATURE_SET = "daily.v1"
SLEEP_KINDS = {"sleep_deep", "sleep_rem", "sleep_core", "sleep_asleep"}


def _timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unsupported timezone: {name}") from exc


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def materialize_daily_feature(
    session: Session,
    cipher: FieldCipher,
    *,
    fitcrew_user_id: str,
    feature_date: date,
    timezone: str,
) -> DailyFeature:
    zone = _timezone(timezone)
    day_start = datetime.combine(feature_date, time.min, zone).astimezone(UTC)
    day_end = datetime.combine(feature_date + timedelta(days=1), time.min, zone).astimezone(UTC)
    stored_samples = session.scalars(
        select(HealthSample).where(HealthSample.fitcrew_user_id == fitcrew_user_id)
    ).all()
    decrypted: list[DecryptedSample] = []
    for sample in stored_samples:
        start_at, end_at = (
            _aware(sample.start_at).astimezone(UTC),
            _aware(sample.end_at).astimezone(UTC),
        )
        if sample.kind in SLEEP_KINDS and end_at > start_at:
            if start_at >= day_end or end_at <= day_start:
                continue
            start_at, end_at = max(start_at, day_start), min(end_at, day_end)
        elif start_at.astimezone(zone).date() != feature_date:
            continue
        value = cipher.decrypt_json(
            EncryptedValue(sample.value_nonce, sample.value_ciphertext),
            aad=f"{fitcrew_user_id}:{sample.sample_id}",
        )
        decrypted.append(
            DecryptedSample(
                kind=sample.kind,
                start_at=start_at,
                end_at=end_at,
                value_mg_dl=float(value["value"]),
            )
        )

    payload = compute_daily_features(decrypted)
    payload["day_timezone"] = timezone
    payload["sleep_day_policy"] = "calendar_day_clipped.v1"
    date_text = feature_date.isoformat()
    aad = f"feature:{fitcrew_user_id}:{date_text}:{FEATURE_SET}"
    encrypted = cipher.encrypt_json(payload, aad=aad)
    feature = session.scalar(
        select(DailyFeature).where(
            DailyFeature.fitcrew_user_id == fitcrew_user_id,
            DailyFeature.feature_date == date_text,
            DailyFeature.feature_set == FEATURE_SET,
        )
    )
    if feature is None:
        feature = DailyFeature(
            fitcrew_user_id=fitcrew_user_id,
            feature_date=date_text,
            feature_set=FEATURE_SET,
            quality_status="partial",
            algorithm_version=payload["algorithm_version"],
            payload_nonce=encrypted.nonce,
            payload_ciphertext=encrypted.ciphertext,
        )
        session.add(feature)
    else:
        feature.quality_status = "partial"
        feature.algorithm_version = payload["algorithm_version"]
        feature.payload_nonce = encrypted.nonce
        feature.payload_ciphertext = encrypted.ciphertext
    session.flush()
    return feature


def affected_dates(samples, *, timezone: str) -> set[date]:
    zone = _timezone(timezone)
    dates = set()
    for sample in samples:
        start, end = _aware(sample.start_at), _aware(sample.end_at)
        first = start.astimezone(zone).date()
        last = first
        if sample.kind in SLEEP_KINDS and end > start:
            last = (end.astimezone(UTC) - timedelta(microseconds=1)).astimezone(zone).date()
        dates.update(first + timedelta(days=offset) for offset in range((last - first).days + 1))
    return dates
