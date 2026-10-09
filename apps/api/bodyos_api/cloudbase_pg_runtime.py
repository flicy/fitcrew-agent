"""Fail-closed, read-only startup verification for a separately initialized PG schema."""

from sqlalchemy import UniqueConstraint, inspect, text

from bodyos_api.cloudbase_pg_manifest import SCHEMA, build_manifest
from bodyos_api.config import get_settings
from bodyos_api.db import make_engine
from bodyos_api.models import Base


def verify_cloudbase_schema(database_engine, *, schema: str) -> None:
    if schema != SCHEMA or database_engine.dialect.name != "postgresql":
        raise ValueError("CloudBase startup requires the private fitcrew PostgreSQL schema")

    inspector = inspect(database_engine)
    expected_tables = set(Base.metadata.tables) | {"alembic_version"}
    existing_tables = set(inspector.get_table_names(schema=schema))
    if missing := expected_tables - existing_tables:
        raise RuntimeError(f"CloudBase schema is missing tables: {', '.join(sorted(missing))}")

    for table in Base.metadata.sorted_tables:
        actual_columns = {
            column["name"] for column in inspector.get_columns(table.name, schema=schema)
        }
        if missing := set(table.columns.keys()) - actual_columns:
            raise RuntimeError(
                f"CloudBase schema is missing columns in {table.name}: {', '.join(sorted(missing))}"
            )

        actual_indexes = {
            index["name"]: index for index in inspector.get_indexes(table.name, schema=schema)
        }
        for index in table.indexes:
            actual = actual_indexes.get(index.name)
            if (
                actual is None
                or tuple(actual["column_names"]) != tuple(index.columns.keys())
                or bool(actual["unique"]) != bool(index.unique)
            ):
                raise RuntimeError(f"CloudBase schema index mismatch: {index.name}")

        actual_uniques = {
            frozenset(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table.name, schema=schema)
        }
        for constraint in table.constraints:
            if (
                isinstance(constraint, UniqueConstraint)
                and frozenset(constraint.columns.keys()) not in actual_uniques
            ):
                raise RuntimeError(f"CloudBase schema unique constraint mismatch: {table.name}")

        actual_foreign_keys = {
            (
                tuple(key["constrained_columns"]),
                key["referred_schema"],
                key["referred_table"],
                tuple(key["referred_columns"]),
            )
            for key in inspector.get_foreign_keys(
                table.name, schema=schema, postgresql_ignore_search_path=True
            )
        }
        for constraint in table.foreign_key_constraints:
            expected_key = (
                tuple(element.parent.name for element in constraint.elements),
                schema,
                constraint.elements[0].column.table.name,
                tuple(element.column.name for element in constraint.elements),
            )
            if expected_key not in actual_foreign_keys:
                raise RuntimeError(f"CloudBase schema foreign key mismatch: {table.name}")

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
