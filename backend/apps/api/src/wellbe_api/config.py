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
    # C10 render-token HMAC secret. Matches the safety-gate default so render
    # tokens minted at visit-packet share time validate consistently.
    c10_token_secret: SecretStr = SecretStr("local-dev-c10-render-token-secret")
    log_level: str = "INFO"
    environment: str = "dev"
    # Browser origins allowed to call this boundary cross-origin. The web app is
    # served from a different host (app.localhost) than the API (api.localhost),
    # and every data request carries custom X-Wellbe-* headers, which forces a
    # CORS preflight. Without an allow-list the browser blocks all data fetches.
    # Override via WELLBE_CORS_ALLOW_ORIGINS (JSON list) per environment.
    cors_allow_origins: list[str] = [
        "http://app.localhost",
        "https://app.localhost",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
