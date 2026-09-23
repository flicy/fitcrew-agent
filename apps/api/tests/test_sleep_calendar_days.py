from datetime import date, datetime

import pytest
from bodyos_api.crypto import EncryptedValue
from bodyos_api.feature_store import affected_dates
from bodyos_api.health_service import HealthIngestionService
from bodyos_api.models import Consent, DailyFeature
from bodyos_api.schemas import HealthSyncBatchIn
from sqlalchemy import select
from test_health_ingest import CONSENT_ID, USER_ID, glucose_batch, seed_authorized_owner


@pytest.mark.parametrize(
    "start,end,zone,expected",
    [
        (
            "2026-08-01T22:00:00+08:00",
            "2026-08-02T07:00:00+08:00",
            "Asia/Shanghai",
            {"2026-08-01": 2, "2026-08-02": 7},
        ),
        (
            "2026-03-08T00:00:00-05:00",
            "2026-03-08T04:00:00-04:00",
            "America/New_York",
            {"2026-03-08": 3},
        ),
        (
            "2026-08-01T22:00:00+08:00",
            "2026-08-02T00:00:00+08:00",
            "Asia/Shanghai",
            {"2026-08-01": 2},
        ),
    ],
)
def test_sleep_ingestion_clips_civil_days_without_dst_or_midnight_double_count(
    session, field_cipher, start, end, zone, expected
):
    seed_authorized_owner(session)
    session.get(Consent, CONSENT_ID).category = "sleep_core"
    session.commit()
    data = glucose_batch().model_dump(mode="json")
    data["timezone"] = zone
    data["sent_at"] = end
    data["samples"][0].update(
        kind="sleep_core",
        start_at=start,
        end_at=end,
        unit="s",
        value=(datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds(),
    )
    batch = HealthSyncBatchIn.model_validate(data)
    assert affected_dates(batch.samples, timezone=zone) == {date.fromisoformat(d) for d in expected}
    HealthIngestionService(session, field_cipher).ingest(USER_ID, batch)
    features = session.scalars(
        select(DailyFeature).where(DailyFeature.fitcrew_user_id == USER_ID)
    ).all()
    assert len(features) == len(expected)
    for feature in features:
        payload = field_cipher.decrypt_json(
            EncryptedValue(feature.payload_nonce, feature.payload_ciphertext),
            aad=f"feature:{USER_ID}:{feature.feature_date}:daily.v1",
        )
        assert payload["sleep"]["total_hours"] == expected[feature.feature_date]
        assert payload["day_timezone"] == zone
        assert payload["sleep_day_policy"] == "calendar_day_clipped.v1"


def test_health_sample_without_timezone_is_rejected_before_aggregation():
    from pydantic import ValidationError

    payload = glucose_batch().model_dump(mode="json")
    payload["samples"][0]["start_at"] = "2026-08-01T23:00:00"
    payload["samples"][0]["end_at"] = "2026-08-01T23:01:00"
    with pytest.raises(ValidationError):
        HealthSyncBatchIn.model_validate(payload)
