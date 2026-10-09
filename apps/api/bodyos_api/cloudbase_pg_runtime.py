"""Fail-closed, read-only startup verification for a separately initialized PG schema."""

from sqlalchemy import inspect, text

from bodyos_api.cloudbase_pg_manifest import SCHEMA, build_manifest
from bodyos_api.config import get_settings
from bodyos_api.db import make_engine
from bodyos_api.models import Base


def verify_cloudbase_schema(database_engine, *, schema: str) -> None:
    if schema != SCHEMA or database_engine.dialect.name != "postgresql":
        raise ValueError("CloudBase startup requires the private fitcrew PostgreSQL schema")

    expected_tables = set(Base.metadata.tables) | {"alembic_version"}
    existing_tables = set(inspect(database_engine).get_table_names(schema=schema))
    if missing := expected_tables - existing_tables:
        raise RuntimeError(f"CloudBase schema is missing tables: {', '.join(sorted(missing))}")

    with database_engine.connect() as connection:
        revisions = (
            connection.execute(text(f"SELECT version_num FROM {SCHEMA}.alembic_version"))
            .scalars()
            .all()
        )
    expected_revision = build_manifest()["revision"]
    if revisions != [expected_revision]:
        raise RuntimeError("CloudBase schema revision does not match the current API")


def main() -> None:
    settings = get_settings()
    if settings.database_schema != SCHEMA or not settings.database_url.startswith("postgresql"):
        raise ValueError("CloudBase startup requires an explicit PostgreSQL URL and fitcrew schema")
    verify_cloudbase_schema(make_engine(), schema=settings.database_schema)


if __name__ == "__main__":
    main()
