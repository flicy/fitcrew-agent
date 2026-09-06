from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_product_migration_runs_on_fresh_and_legacy_database(tmp_path, monkeypatch):
    root = Path(__file__).parents[3]
    for legacy in (False, True):
        url = f"sqlite:///{tmp_path / ('legacy.db' if legacy else 'fresh.db')}"
        monkeypatch.setenv("BODYOS_DATABASE_URL", url)
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "apps/api/migrations"))
        engine = create_engine(url)
        if legacy:
            command.upgrade(config, "0003_group_coach_outbox")
            with engine.begin() as connection:
                connection.execute(text("DROP TABLE product_records"))
                connection.execute(text("DROP TABLE login_challenges"))
                connection.execute(text("ALTER TABLE device_bindings DROP COLUMN expires_at"))
        command.upgrade(config, "head")
        tables = inspect(engine).get_table_names()
        assert "product_records" in tables and "login_challenges" in tables
        assert "expires_at" in {c["name"] for c in inspect(engine).get_columns("device_bindings")}
        command.upgrade(config, "head")
