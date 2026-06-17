"""C13 API settings."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WELLBE_", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://wellbe:wellbe_dev@wellbe-postgres:5432/wellbe"
    )
    redis_url: str = "redis://wellbe-redis:6379/0"
    # C3 ingestion worker (the capture write path forwards here; it owns the
    # adapter registry and the C2 Vault append).
    ingestion_worker_url: str = "http://ingestion-worker:8003"
    log_level: str = "INFO"
    environment: str = "dev"
