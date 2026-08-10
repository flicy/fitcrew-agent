from bodyos_api.models import Base


def test_owner_alpha_schema_contains_required_tables() -> None:
    assert set(Base.metadata.tables) == {
        "audit_events",
        "consents",
        "daily_features",
        "demand_items",
        "device_bindings",
        "health_samples",
        "identity_bindings",
        "insights",
        "knowledge_chunks",
        "knowledge_reviews",
        "knowledge_sources",
        "memories",
            "outbox_events",
            "pairing_exchange_sessions",
            "sync_batches",
        "users",
    }


def test_health_samples_have_owner_scoped_idempotency_key() -> None:
    table = Base.metadata.tables["health_samples"]
    unique_column_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("fitcrew_user_id", "sample_id") in unique_column_sets


def test_group_outbox_has_idempotent_schedule_and_retry_fields() -> None:
    table = Base.metadata.tables["outbox_events"]

    assert table.c.fitcrew_user_id.nullable is True
    for name in ("idempotency_key", "scheduled_for", "next_attempt_at", "last_error_code"):
        assert name in table.c
