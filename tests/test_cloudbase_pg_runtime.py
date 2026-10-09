import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from bodyos_api.models import Base, User
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

ROOT = Path(__file__).resolve().parents[1]


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

    inspector = MagicMock()
    inspector.get_table_names.return_value = [*Base.metadata.tables, "alembic_version"]
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
    assert str(connection.execute.call_args.args[0]) == (
        "SELECT version_num FROM fitcrew.alembic_version"
    )


def test_cloudbase_preflight_rejects_missing_table_or_wrong_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bodyos_api import cloudbase_pg_runtime as runtime

    inspector = MagicMock()
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
