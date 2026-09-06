from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.feature_store import affected_dates, materialize_daily_feature
from bodyos_api.models import (
    Consent,
    DailyFeature,
    DeviceBinding,
    HealthSample,
    Insight,
    SyncBatch,
    User,
)
from bodyos_api.schemas import HealthKind, HealthSampleIn, HealthSyncBatchIn


class ConsentRequired(PermissionError):
    pass


class DeviceBindingRejected(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class IngestResult:
    batch_id: str
    inserted_samples: int
    replayed: bool


def normalize_value(sample: HealthSampleIn) -> tuple[float, str]:
    if sample.kind != HealthKind.BLOOD_GLUCOSE:
        return sample.value, sample.unit
    unit = sample.unit.casefold().replace(" ", "")
    if unit == "mmol/l":
        return sample.value * 18.0182, "mg/dL"
    if unit == "mg/dl":
        return sample.value, "mg/dL"
    raise ValueError(f"unsupported blood glucose unit: {sample.unit}")


class HealthIngestionService:
    def __init__(self, session: Session, cipher: FieldCipher):
        self._session = session
        self._cipher = cipher

    def ingest(self, fitcrew_user_id: str, batch: HealthSyncBatchIn) -> IngestResult:
        user = self._session.scalar(
            select(User)
            .where(User.fitcrew_user_id == fitcrew_user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not user or user.status != "active":
            raise DeviceBindingRejected("account is not active")
        existing = self._session.scalar(
            select(SyncBatch).where(
                SyncBatch.fitcrew_user_id == fitcrew_user_id,
                SyncBatch.batch_id == str(batch.batch_id),
            )
        )
        if existing is not None:
            return IngestResult(str(batch.batch_id), inserted_samples=0, replayed=True)

        device = self._session.get(
            DeviceBinding, str(batch.device_binding_id), populate_existing=True
        )
        if (
            device is None
            or device.fitcrew_user_id != fitcrew_user_id
            or device.revoked_at is not None
        ):
            raise DeviceBindingRejected("device binding is not active for this user")

        consent = self._session.get(Consent, str(batch.consent_id), populate_existing=True)
        sample_categories = {sample.kind.value for sample in batch.samples}
        if (
            consent is None
            or consent.fitcrew_user_id != fitcrew_user_id
            or not consent.granted
            or consent.withdrawn_at is not None
            or consent.purpose != "private_coaching"
            or sample_categories != {consent.category}
        ):
            raise ConsentRequired("active category and purpose consent is required")

        sync_batch = SyncBatch(
            fitcrew_user_id=fitcrew_user_id,
            batch_id=str(batch.batch_id),
            device_binding_id=str(batch.device_binding_id),
            consent_id=str(batch.consent_id),
            source=batch.source,
            timezone=batch.timezone,
            full_reconciliation=batch.full_reconciliation,
            status="accepted",
        )
        self._session.add(sync_batch)
        self._session.flush()

        inserted = 0
        for sample in batch.samples:
            if self._sample_exists(fitcrew_user_id, str(sample.sample_id)):
                continue
            normalized_value, normalized_unit = normalize_value(sample)
            aad = f"{fitcrew_user_id}:{sample.sample_id}"
            encrypted = self._cipher.encrypt_json(
                {"value": normalized_value, "unit": normalized_unit}, aad=aad
            )
            self._session.add(
                HealthSample(
                    fitcrew_user_id=fitcrew_user_id,
                    sync_batch_id=sync_batch.id,
                    sample_id=str(sample.sample_id),
                    kind=sample.kind.value,
                    start_at=sample.start_at,
                    end_at=sample.end_at,
                    original_unit=sample.unit,
                    normalized_unit=normalized_unit,
                    source=sample.source,
                    device=sample.device,
                    value_nonce=encrypted.nonce,
                    value_ciphertext=encrypted.ciphertext,
                )
            )
            inserted += 1
        sync_batch.sample_count = inserted
        device.last_sync_at = batch.sent_at
        self._session.flush()
        for feature_date in affected_dates(batch.samples, timezone=batch.timezone):
            materialize_daily_feature(
                self._session,
                self._cipher,
                fitcrew_user_id=fitcrew_user_id,
                feature_date=feature_date,
                timezone=batch.timezone,
            )
        self._session.commit()
        return IngestResult(str(batch.batch_id), inserted_samples=inserted, replayed=False)

    def _sample_exists(self, fitcrew_user_id: str, sample_id: str) -> bool:
        return (
            self._session.scalar(
                select(HealthSample.id).where(
                    HealthSample.fitcrew_user_id == fitcrew_user_id,
                    HealthSample.sample_id == sample_id,
                )
            )
            is not None
        )

    def export_user_health(self, fitcrew_user_id: str) -> dict[str, Any]:
        samples = self._session.scalars(
            select(HealthSample)
            .where(HealthSample.fitcrew_user_id == fitcrew_user_id)
            .order_by(HealthSample.start_at)
        ).all()
        exported = []
        for sample in samples:
            aad = f"{fitcrew_user_id}:{sample.sample_id}"
            value = self._cipher.decrypt_json(
                EncryptedValue(sample.value_nonce, sample.value_ciphertext), aad=aad
            )
            exported.append(
                {
                    "sample_id": sample.sample_id,
                    "kind": sample.kind,
                    "start_at": sample.start_at.isoformat(),
                    "end_at": sample.end_at.isoformat(),
                    "value": value["value"],
                    "unit": value["unit"],
                    "source": sample.source,
                }
            )
        return {"fitcrew_user_id": fitcrew_user_id, "samples": exported}

    def withdraw_consent(self, fitcrew_user_id: str, consent_id: str, *, at: datetime) -> None:
        self._session.scalar(
            select(User)
            .where(User.fitcrew_user_id == fitcrew_user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        consent = self._session.get(Consent, consent_id)
        if consent is None or consent.fitcrew_user_id != fitcrew_user_id:
            raise ConsentRequired("consent does not belong to user")
        consent.granted = False
        consent.withdrawn_at = at
        self._session.commit()

    def delete_user_health(self, fitcrew_user_id: str) -> dict[str, int]:
        self._session.scalar(
            select(User)
            .where(User.fitcrew_user_id == fitcrew_user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        counts = {
            "health_samples": self._session.execute(
                delete(HealthSample).where(HealthSample.fitcrew_user_id == fitcrew_user_id)
            ).rowcount,
            "daily_features": self._session.execute(
                delete(DailyFeature).where(DailyFeature.fitcrew_user_id == fitcrew_user_id)
            ).rowcount,
            "insights": self._session.execute(
                delete(Insight).where(Insight.fitcrew_user_id == fitcrew_user_id)
            ).rowcount,
            "sync_batches": self._session.execute(
                delete(SyncBatch).where(SyncBatch.fitcrew_user_id == fitcrew_user_id)
            ).rowcount,
        }
        self._session.commit()
        return {key: int(value or 0) for key, value in counts.items()}
