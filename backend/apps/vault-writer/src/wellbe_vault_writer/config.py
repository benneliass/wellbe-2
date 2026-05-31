from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class VaultWriterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WELLBE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: SecretStr
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_raw: str = "wellbe-raw"
    redis_url: str = "redis://localhost:6379/0"
