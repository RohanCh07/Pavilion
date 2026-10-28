"""Engine and session factory."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from fantasy_bot.storage.models import Base


def create_engine(url: str) -> AsyncEngine:
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"
    if is_sqlite and parsed.database and parsed.database != ":memory:":
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(url, pool_pre_ping=not is_sqlite)
    if is_sqlite:

        @event.listens_for(engine.sync_engine, "connect")
        def _sqlite_pragmas(conn, _record):  # pragma: no cover - trivial
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


# Columns added after their table first shipped: (table, column, SQL type).
ADDED_COLUMNS = (("fantasy_teams", "pool_id", "INTEGER"),)


def _add_missing_columns(conn) -> None:
    inspector = inspect(conn)
    for table, column, sql_type in ADDED_COLUMNS:
        if table in inspector.get_table_names():
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


async def init_db(engine: AsyncEngine) -> None:
    """Create tables if missing and add newer columns to old databases.

    Swap for Alembic migrations once the schema settles.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)


def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
