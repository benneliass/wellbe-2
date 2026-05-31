from __future__ import annotations

from wellbe_platform import BaseServiceSettings


class ProcessingWorkerSettings(BaseServiceSettings):
    service_name: str = "processing-worker"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe"
    temporal_host: str = "localhost:7233"
    extraction_model: str = "wellbe-text-extractor"
