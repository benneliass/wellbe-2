from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WELLBE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.DEV
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    service_name: str = "wellbe"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WELLBE_",
        extra="ignore",
    )

    database_url: SecretStr = Field(
        ..., description="PostgreSQL connection string"
    )


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WELLBE_",
        extra="ignore",
    )

    redis_url: str = "redis://localhost:6379/0"
