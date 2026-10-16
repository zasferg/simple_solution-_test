from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    URL: str


class RedisSettings(BaseModel):
    URL: str


class DeribitSettings(BaseModel):
    BASE_URL: str = "https://www.deribit.com/api/v2"
    TIMEOUT_SECONDS: float = 10.0


class CollectorSettings(BaseModel):
    INTERVAL_SECONDS: int = 60


class Settings(BaseSettings):
    """Created at an entrypoint and passed down; never cached globally."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore",
    )

    DATABASE: DatabaseSettings
    REDIS: RedisSettings
    DERIBIT: DeribitSettings = DeribitSettings()
    COLLECTOR: CollectorSettings = CollectorSettings()
