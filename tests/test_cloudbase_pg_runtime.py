import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bodyos_api.models import Base, User
from sqlalchemy import UniqueConstraint, select
from sqlalchemy.dialects import postgresql

ROOT = Path(__file__).resolve().parents[1]


def test_cloudbase_entrypoint_rejects_invalid_field_encryption_key(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python").symlink_to(sys.executable)
    result = subprocess.run(
        ["sh", str(ROOT / "infra/tencent/cloudbase-api-entrypoint.sh")],
        cwd=tmp_path,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "PYTHONPATH": str(ROOT / "apps/api"),
            "BODYOS_ENVIRONMENT": "production",
            "BODYOS_PUBLIC_AUTH_ENABLED": "true",
            "BODYOS_PRIVATE_WECHAT_CLOUD_ENABLED": "true",
            "BODYOS_DATABASE_SCHEMA": "fitcrew",
            "BODYOS_DATABASE_MIGRATION_MODE": "verify-cloudbase-pg",
            "BODYOS_DATABASE_URL": "postgresql://unused:unused@127.0.0.1/unused",
            "BODYOS_PUBLIC_BASE_URL": "",
            "BODYOS_WECHAT_APP_ID": "wx-test",
            "BODYOS_WECHAT_APP_SECRET": "unused",
            "BODYOS_IDENTITY_PEPPER": "unused",
            "BODYOS_ENCRYPTION_KEY": "too-short",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "32-byte key" in result.stderr
    assert "No such file" not in result.stderr


def _schema_inspector() -> MagicMock:
    inspector = MagicMock()
    inspector.get_table_names.return_value = [*Base.metadata.tables, "alembic_version"]
    inspector.get_columns.side_effect = lambda name, **_kwargs: [
        {"name": column.name} for column in Base.metadata.tables[name].columns
    ]
    inspector.get_indexes.side_effect = lambda name, **_kwargs: [
        {
            "name": index.name,
            "column_names": list(index.columns.keys()),
            "unique": index.unique,
        }
        for index in Base.metadata.tables[name].indexes
    ]
    inspector.get_unique_constraints.side_effect = lambda name, **_kwargs: [
        {"column_names": list(constraint.columns.keys())}
        for constraint in Base.metadata.tables[name].constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    inspector.get_foreign_keys.side_effect = lambda name, **_kwargs: [
        {
            "constrained_columns": [element.parent.name for element in constraint.elements],
            "referred_schema": "fitcrew",
            "referred_table": constraint.elements[0].column.table.name,
            "referred_columns": [element.column.name for element in constraint.elements],
        }
        for constraint in Base.metadata.tables[name].foreign_key_constraints
    ]
    return inspector


def test_database_engine_maps_models_to_private_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    from bodyos_api import db

    fake_engine = MagicMock()
    monkeypatch.setattr(db, "create_engine", lambda *_args, **_kwargs: fake_engine)
    monkeypatch.setattr(
        db,
        "get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql+psycopg://localhost/fitcrew", database_schema="fitcrew"
        ),
    )

    db.make_engine()

    fake_engine.execution_options.assert_called_once_with(schema_translate_map={None: "fitcrew"})


def test_private_schema_rejects_non_postgres_and_unexpected_schema() -> None:
    from bodyos_api.db import make_engine

    with pytest.raises(ValueError):
        make_engine("sqlite+pysqlite:///:memory:", schema="fitcrew")
    with pytest.raises(ValueError):
        make_engine("postgresql+psycopg://localhost/fitcrew", schema="public")


def test_schema_translation_qualifies_orm_queries() -> None:
    sql = str(
        select(User).compile(
            dialect=postgresql.dialect(),
            schema_translate_map={None: "fitcrew"},
            render_schema_translate=True,
        )
    )
    assert "FROM fitcrew.users" in sql


def test_cloudbase_preflight_is_read_only_and_requires_current_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bodyos_api import cloudbase_pg_runtime as runtime

    inspector = _schema_inspector()
    monkeypatch.setattr(runtime, "inspect", lambda _engine: inspector)
    connection = MagicMock()
    connection.execute.return_value.scalars.return_value.all.return_value = [
        "0005_device_only_pairing"
    ]
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    engine.connect.return_value.__enter__.return_value = connection

    runtime.verify_cloudbase_schema(engine, schema="fitcrew")

    inspector.get_table_names.assert_called_once_with(schema="fitcrew")
    assert inspector.get_columns.call_count == len(Base.metadata.tables)
    assert inspector.get_unique_constraints.call_count == len(Base.metadata.tables)
    assert str(connection.execute.call_args.args[0]) == (
        "SELECT version_num FROM fitcrew.alembic_version"
    )


def test_cloudbase_preflight_rejects_missing_table_or_wrong_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bodyos_api import cloudbase_pg_runtime as runtime

    inspector = _schema_inspector()
    inspector.get_table_names.return_value = ["alembic_version"]
    monkeypatch.setattr(runtime, "inspect", lambda _engine: inspector)
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    with pytest.raises(RuntimeError, match="missing tables"):
        runtime.verify_cloudbase_schema(engine, schema="fitcrew")
    engine.connect.assert_not_called()

    inspector.get_table_names.return_value = [*Base.metadata.tables, "alembic_version"]
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalars.return_value.all.return_value = ["0004_product_records"]
    with pytest.raises(RuntimeError, match="revision"):
        runtime.verify_cloudbase_schema(engine, schema="fitcrew")


@pytest.mark.parametrize(
    ("method", "table_name", "message"),
    [
        ("get_columns", "identity_bindings", "missing columns"),
        ("get_indexes", "health_samples", "index mismatch"),
        ("get_unique_constraints", "identity_bindings", "unique constraint mismatch"),
        ("get_foreign_keys", "health_samples", "foreign key mismatch"),
    ],
)
def test_cloudbase_preflight_rejects_partial_privacy_schema(
    monkeypatch: pytest.MonkeyPatch, method: str, table_name: str, message: str
) -> None:
    from bodyos_api import cloudbase_pg_runtime as runtime

    inspector = _schema_inspector()
    original = getattr(inspector, method).side_effect
    getattr(inspector, method).side_effect = lambda name, **kwargs: (
        [] if name == table_name else original(name, **kwargs)
    )
    monkeypatch.setattr(runtime, "inspect", lambda _engine: inspector)
    engine = MagicMock()
    engine.dialect.name = "postgresql"

    with pytest.raises(RuntimeError, match=message):
        runtime.verify_cloudbase_schema(engine, schema="fitcrew")
    engine.connect.assert_not_called()


def test_cloudbase_preflight_rejects_foreign_key_into_public_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bodyos_api import cloudbase_pg_runtime as runtime

    inspector = _schema_inspector()
    original = inspector.get_foreign_keys.side_effect

    def foreign_keys(name: str, **kwargs: object) -> list[dict]:
        keys = original(name, **kwargs)
        if name == "health_samples":
            return [{**key, "referred_schema": "public"} for key in keys]
        return keys

    inspector.get_foreign_keys.side_effect = foreign_keys
    monkeypatch.setattr(runtime, "inspect", lambda _engine: inspector)
    engine = MagicMock()
    engine.dialect.name = "postgresql"

    with pytest.raises(RuntimeError, match="foreign key mismatch"):
        runtime.verify_cloudbase_schema(engine, schema="fitcrew")
    engine.connect.assert_not_called()
    inspector.get_foreign_keys.assert_any_call(
        "health_samples", schema="fitcrew", postgresql_ignore_search_path=True
    )


@pytest.mark.parametrize(
    ("mode", "schema", "expected"),
    [
        ("alembic", "fitcrew", "requires managed CloudBase verification"),
        ("verify-cloudbase-pg", "", "requires fitcrew schema"),
        ("unknown", "", "Unsupported database migration mode"),
    ],
)
def test_entrypoint_refuses_unsafe_database_modes(
    mode: str, schema: str, expected: str, tmp_path: Path
) -> None:
    env = {
        "PATH": "/usr/bin:/bin",
        "BODYOS_DATABASE_MIGRATION_MODE": mode,
        "BODYOS_DATABASE_SCHEMA": schema,
    }
    result = subprocess.run(
        ["sh", str(ROOT / "infra/tencent/api-entrypoint.sh")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert expected in result.stderr


def test_entrypoint_verifies_managed_schema_without_running_alembic(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("python", "uvicorn", "alembic"):
        executable = bin_dir / name
        executable.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "{name}:$*" >> "$CALL_LOG"\n')
        executable.chmod(0o700)
    call_log = tmp_path / "calls"
    result = subprocess.run(
        ["sh", str(ROOT / "infra/tencent/api-entrypoint.sh")],
        cwd=tmp_path,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "CALL_LOG": str(call_log),
            "BODYOS_DATABASE_MIGRATION_MODE": "verify-cloudbase-pg",
            "BODYOS_DATABASE_SCHEMA": "fitcrew",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert call_log.read_text().splitlines() == [
        "python:-m bodyos_api.cloudbase_pg_runtime",
        "uvicorn:bodyos_api.app:app --host 0.0.0.0 --port 8000 --proxy-headers --no-access-log",
    ]
