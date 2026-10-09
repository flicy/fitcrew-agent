"""Generate a review-only CloudBase PostgreSQL schema manifest; never execute it."""

import hashlib
import re
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from bodyos_api.models import Base

SCHEMA = "fitcrew"


def build_manifest(*, app_role: str | None = None) -> dict:
    if app_role is not None and not re.fullmatch(r"[a-z_][a-z0-9_]*", app_role):
        raise ValueError("invalid application database role")
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "migrations")
    )
    revision = ScriptDirectory.from_config(config).get_current_head()
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata, schema=SCHEMA)
    Table(
        "alembic_version",
        metadata,
        Column("version_num", String(32), primary_key=True),
        schema=SCHEMA,
    )

    dialect = postgresql.dialect()
    statements = [
        {"kind": "schema", "sql": f"CREATE SCHEMA {SCHEMA}"},
        {
            "kind": "deny-client-access",
            "sql": f"REVOKE ALL ON SCHEMA {SCHEMA} FROM PUBLIC, anon, authenticated",
        },
    ]
    statements.extend(
        {"kind": "table", "sql": str(CreateTable(table).compile(dialect=dialect)).strip()}
        for table in metadata.sorted_tables
    )
    statements.extend(
        {"kind": "index", "sql": str(CreateIndex(index).compile(dialect=dialect)).strip()}
        for table in metadata.sorted_tables
        for index in sorted(table.indexes, key=lambda item: item.name or "")
    )
    statements.append(
        {
            "kind": "deny-client-access",
            "sql": f"REVOKE ALL ON ALL TABLES IN SCHEMA {SCHEMA} FROM PUBLIC, anon, authenticated",
        }
    )
    if app_role:
        statements.extend(
            [
                {"kind": "server-grant", "sql": f"GRANT USAGE ON SCHEMA {SCHEMA} TO {app_role}"},
                {
                    "kind": "server-grant",
                    "sql": (
                        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                        f"IN SCHEMA {SCHEMA} TO {app_role}"
                    ),
                },
            ]
        )
    statements.append(
        {
            "kind": "alembic-stamp",
            "sql": f"INSERT INTO {SCHEMA}.alembic_version (version_num) VALUES ('{revision}')",
        }
    )
    digest = hashlib.sha256("\n".join(item["sql"] for item in statements).encode()).hexdigest()
    return {
        "schema": SCHEMA,
        "revision": revision,
        "requires_empty_schema": True,
        "sha256": digest,
        "statements": statements,
    }
