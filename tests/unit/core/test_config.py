import pytest

from app.core.config import Settings


def test_nested_settings_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE__URL", "postgresql+asyncpg://u:p@db:5432/tracker")
    monkeypatch.setenv("REDIS__URL", "redis://redis:6379/0")
    monkeypatch.setenv("COLLECTOR__INTERVAL_SECONDS", "30")

    settings = Settings(_env_file=None)

    assert settings.DATABASE.URL == "postgresql+asyncpg://u:p@db:5432/tracker"
    assert settings.REDIS.URL == "redis://redis:6379/0"
    assert settings.COLLECTOR.INTERVAL_SECONDS == 30
    assert settings.DERIBIT.BASE_URL == "https://www.deribit.com/api/v2"
