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
