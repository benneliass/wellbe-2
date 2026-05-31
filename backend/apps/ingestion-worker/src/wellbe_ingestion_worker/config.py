from __future__ import annotations

from wellbe_platform import BaseServiceSettings


class IngestionWorkerSettings(BaseServiceSettings):
    service_name: str = "ingestion-worker"
    vault_writer_url: str = "http://localhost:8001"
    redis_url: str = "redis://localhost:6379/0"
