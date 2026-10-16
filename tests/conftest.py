import pytest

from app.core.config import DatabaseSettings, RedisSettings, Settings


@pytest.fixture
def settings() -> Settings:
    """Settings that do not depend on the environment or any .env file."""
    return Settings(
        _env_file=None,
        DATABASE=DatabaseSettings(URL="postgresql+asyncpg://user:password@localhost:5432/unused"),
        REDIS=RedisSettings(URL="redis://localhost:6379/0"),
    )
