import importlib

import pytest
from bodyos_api.models import Base


def test_manifest_uses_private_schema_and_current_model_tables() -> None:
    manifest = importlib.import_module("bodyos_api.cloudbase_pg_manifest").build_manifest()
    statements = [item["sql"] for item in manifest["statements"]]

    assert manifest["schema"] == "fitcrew"
    assert manifest["requires_empty_schema"] is True
    assert statements[0] == "CREATE SCHEMA fitcrew"
    assert (
        "REVOKE ALL ON ALL TABLES IN SCHEMA fitcrew FROM PUBLIC, anon, authenticated" in statements
    )
    for table_name in Base.metadata.tables:
        assert any(sql.startswith(f"CREATE TABLE fitcrew.{table_name} ") for sql in statements)
    assert any("REFERENCES fitcrew.users" in sql for sql in statements)
    assert any("CREATE TABLE fitcrew.alembic_version" in sql for sql in statements)
    assert all("CREATE TABLE public." not in sql for sql in statements)
    assert all(not sql.startswith("DROP ") for sql in statements)


def test_manifest_includes_indexes_and_current_alembic_stamp() -> None:
    build_manifest = importlib.import_module("bodyos_api.cloudbase_pg_manifest").build_manifest
    manifest = build_manifest()
    statements = [item["sql"] for item in manifest["statements"]]

    assert manifest["revision"] == "0005_device_only_pairing"
    assert any(sql.startswith("CREATE INDEX ix_fitcrew_audit_events") for sql in statements)
    assert sum(item["kind"] == "index" for item in manifest["statements"]) == sum(
        len(table.indexes) for table in Base.metadata.tables.values()
    )
    assert statements[-1] == (
        "INSERT INTO fitcrew.alembic_version (version_num) VALUES ('0005_device_only_pairing')"
    )
    assert manifest["sha256"] == build_manifest()["sha256"]


def test_manifest_grants_only_explicit_server_role() -> None:
    build_manifest = importlib.import_module("bodyos_api.cloudbase_pg_manifest").build_manifest
    default_sql = [item["sql"] for item in build_manifest()["statements"]]
    assert not any(sql.startswith("GRANT ") for sql in default_sql)

    statements = [item["sql"] for item in build_manifest(app_role="fitcrew_app")["statements"]]
    assert "GRANT USAGE ON SCHEMA fitcrew TO fitcrew_app" in statements
    assert (
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA fitcrew TO fitcrew_app"
        in statements
    )
    assert not any(sql.startswith("GRANT ") and " TO anon" in sql for sql in statements)
    with pytest.raises(ValueError):
        build_manifest(app_role="fitcrew_app; DROP SCHEMA public")
