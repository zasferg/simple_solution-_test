import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import Settings
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.tables import IndexPriceRecord

PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def recreate_database(url: str) -> None:
    """Drop and create the test database through the server's `postgres` maintenance database."""
    database = make_url(url).database
    engine = create_async_engine(make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
            await connection.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """A fresh test database migrated by alembic, so the migrations are tested too."""
    url = Settings(_env_file=PROJECT_ROOT / ".env.test").DATABASE.URL
    try:
        asyncio.run(recreate_database(url))
    except OSError as exc:
        pytest.skip(f"PostgreSQL from .env.test is unavailable ({exc}); start it with `docker compose up -d db`")

    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_config, "head")
    yield url
    command.downgrade(alembic_config, "base")


@pytest.fixture
async def db_session(database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(database_url)
    try:
        async with create_session_factory(engine)() as session:
            yield session
            await session.rollback()
            await session.execute(delete(IndexPriceRecord))
            await session.commit()
    finally:
        await engine.dispose()
