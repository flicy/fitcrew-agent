import importlib.util
from pathlib import Path

ROOT = Path(__file__).parents[3]


def load_migration():
    path = ROOT / "apps/api/migrations/versions/0003_group_coach_outbox.py"
    spec = importlib.util.spec_from_file_location("migration_0003_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeInspector:
    def __init__(self, *, fresh: bool):
        self.fresh = fresh

    def get_columns(self, table: str) -> list[dict]:
        assert table == "outbox_events"
        columns = [{"name": "fitcrew_user_id", "nullable": self.fresh}]
        if self.fresh:
            columns.extend(
                {"name": name, "nullable": True}
                for name in (
                    "idempotency_key",
                    "scheduled_for",
                    "next_attempt_at",
                    "last_error_code",
                )
            )
        return columns

    def get_unique_constraints(self, table: str) -> list[dict]:
        assert table == "outbox_events"
        if not self.fresh:
            return []
        return [
            {
                "name": "outbox_events_idempotency_key_key",
                "column_names": ["idempotency_key"],
            }
        ]

    def get_indexes(self, table: str) -> list[dict]:
        assert table == "outbox_events"
        if not self.fresh:
            return []
        return [
            {"name": "ix_outbox_events_scheduled_for"},
            {"name": "ix_outbox_events_next_attempt_at"},
        ]


class FakeOp:
    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []

    def get_bind(self):
        return object()

    def __getattr__(self, name: str):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return record


def test_upgrade_is_a_noop_for_a_fresh_schema_that_already_has_current_metadata(
    monkeypatch,
) -> None:
    migration = load_migration()
    fake_op = FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: FakeInspector(fresh=True))

    migration.upgrade()

    assert fake_op.calls == []


def test_upgrade_adds_every_group_outbox_control_to_the_legacy_schema(monkeypatch) -> None:
    migration = load_migration()
    fake_op = FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: FakeInspector(fresh=False))

    migration.upgrade()

    names = [name for name, _args, _kwargs in fake_op.calls]
    assert names.count("alter_column") == 1
    assert names.count("add_column") == 4
    assert names.count("create_unique_constraint") == 1
    assert names.count("create_index") == 2


def test_fresh_schema_downgrade_drops_the_actual_generated_unique_name(monkeypatch) -> None:
    migration = load_migration()
    fake_op = FakeOp()
    monkeypatch.setattr(migration, "op", fake_op)
    monkeypatch.setattr(migration.sa, "inspect", lambda bind: FakeInspector(fresh=True))

    migration.downgrade()

    constraint_calls = [call for call in fake_op.calls if call[0] == "drop_constraint"]
    assert constraint_calls[0][1][0] == "outbox_events_idempotency_key_key"
    names = [name for name, _args, _kwargs in fake_op.calls]
    assert names.count("drop_column") == 4
    assert names.index("execute") < names.index("alter_column")
