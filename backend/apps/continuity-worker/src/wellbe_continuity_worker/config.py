from __future__ import annotations

from typing import Literal

from wellbe_platform import BaseServiceSettings


class ContinuityWorkerSettings(BaseServiceSettings):
    service_name: str = "continuity-worker"
    database_url: str = "postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe"
    temporal_host: str = "temporal:7233"
    temporal_namespace: str = "default"
    # Exactly one mechanism advances C9 timers. "sweeper" polls the ledger (the
    # homeserver default); "temporal" hosts the per-item durable-timer workflow.
    # Never run both against the same ledger.
    c9_timer_mechanism: Literal["sweeper", "temporal"] = "sweeper"
    c9_sweep_interval_seconds: float = 60.0
