from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from bodyos_api.config import get_settings


def make_engine(database_url: str | None = None, *, schema: str | None = None):
    settings = get_settings()
    url = database_url or settings.database_url
    target_schema = settings.database_schema if schema is None else schema
    if target_schema:
        if target_schema != "fitcrew":
            raise ValueError("unsupported private database schema")
        if not url.startswith("postgresql://") and not url.startswith("postgresql+"):
            raise ValueError("private database schema requires PostgreSQL")
    options = {"check_same_thread": False} if url.startswith("sqlite") else {}
    database_engine = create_engine(url, connect_args=options, pool_pre_ping=True)
    if target_schema:
        return database_engine.execution_options(schema_translate_map={None: target_schema})
    return database_engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
