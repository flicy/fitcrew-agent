import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    fitcrew_user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai", nullable=False)


class IdentityBinding(TimestampMixin, Base):
    __tablename__ = "identity_bindings"
    __table_args__ = (UniqueConstraint("provider", "subject_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_subject: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceBinding(TimestampMixin, Base):
    __tablename__ = "device_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    device_public_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="ios", nullable=False)
    last_cursor: Mapped[str | None] = mapped_column(Text)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Consent(TimestampMixin, Base):
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    receipt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PairingExchangeSession(TimestampMixin, Base):
    __tablename__ = "pairing_exchange_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    device_public_id: Mapped[str] = mapped_column(String(128), nullable=False)
    categories_json: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    pairing_code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncBatch(TimestampMixin, Base):
    __tablename__ = "sync_batches"
    __table_args__ = (UniqueConstraint("fitcrew_user_id", "batch_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    device_binding_id: Mapped[str] = mapped_column(ForeignKey("device_bindings.id"))
    consent_id: Mapped[str] = mapped_column(ForeignKey("consents.id"))
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    full_reconciliation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="accepted", nullable=False)


class HealthSample(TimestampMixin, Base):
    __tablename__ = "health_samples"
    __table_args__ = (
        UniqueConstraint("fitcrew_user_id", "sample_id"),
        Index("ix_health_samples_user_kind_start", "fitcrew_user_id", "kind", "start_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"))
    sync_batch_id: Mapped[str] = mapped_column(ForeignKey("sync_batches.id"))
    sample_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    original_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    device: Mapped[str | None] = mapped_column(String(200))
    value_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    value_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class DailyFeature(TimestampMixin, Base):
    __tablename__ = "daily_features"
    __table_args__ = (UniqueConstraint("fitcrew_user_id", "feature_date", "feature_set"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    feature_date: Mapped[str] = mapped_column(String(10), nullable=False)
    feature_set: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    payload_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)


class Insight(TimestampMixin, Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_window: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    model_route: Mapped[str | None] = mapped_column(String(64))


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
    layer: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    content_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KnowledgeSource(TimestampMixin, Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.fitcrew_user_id"), index=True
    )
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rights_status: Mapped[str] = mapped_column(String(64), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class KnowledgeChunk(TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("source_id", "page_number", "chunk_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)


class KnowledgeReview(TimestampMixin, Base):
    __tablename__ = "knowledge_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), index=True)
    reviewer_role: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    applicability: Mapped[str] = mapped_column(Text, nullable=False)


class DemandItem(TimestampMixin, Base):
    __tablename__ = "demand_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.fitcrew_user_id"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    description_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    description_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cluster_key: Mapped[str | None] = mapped_column(String(128))
    decision_rationale: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str | None] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64))
    policy_result: Mapped[str] = mapped_column(String(32), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OutboxEvent(TimestampMixin, Base):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fitcrew_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.fitcrew_user_id"), index=True
    )
    destination: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), unique=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64))
