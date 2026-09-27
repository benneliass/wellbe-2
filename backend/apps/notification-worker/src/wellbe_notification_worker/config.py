from __future__ import annotations

from wellbe_platform import BaseServiceSettings


class NotificationWorkerSettings(BaseServiceSettings):
    service_name: str = "notification-worker"
    database_url: str = "postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe"
    notification_poll_interval_seconds: float = 5.0
    notification_batch_size: int = 50
