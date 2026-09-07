from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class HealthKind(StrEnum):
    BLOOD_GLUCOSE = "blood_glucose"
    SLEEP_ASLEEP = "sleep_asleep"
    SLEEP_CORE = "sleep_core"
    SLEEP_DEEP = "sleep_deep"
    SLEEP_REM = "sleep_rem"
    HEART_RATE_VARIABILITY = "heart_rate_variability"
    RESTING_HEART_RATE = "resting_heart_rate"
    WORKOUT = "workout"
    ACTIVE_ENERGY = "active_energy"
    STEP_COUNT = "step_count"
    STAND_HOURS = "stand_hours"
    ACTIVITY_SUMMARY = "activity_summary"


class HealthSampleIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: UUID
    kind: HealthKind
    start_at: AwareDatetime
    end_at: AwareDatetime
    value: float
    unit: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=200)
    device: str | None = Field(default=None, max_length=200)
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_interval(self):
        if self.end_at < self.start_at:
            raise ValueError("end_at must not be before start_at")
        return self


class HealthSyncBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "health-sync.v1"
    batch_id: UUID
    device_binding_id: UUID
    consent_id: UUID
    source: str = Field(min_length=1, max_length=200)
    timezone: str = Field(min_length=1, max_length=64)
    sent_at: datetime
    full_reconciliation: bool = False
    samples: list[HealthSampleIn] = Field(max_length=10_000)
