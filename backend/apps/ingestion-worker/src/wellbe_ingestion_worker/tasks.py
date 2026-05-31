from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timezone
from uuid import UUID

import dramatiq

from wellbe_contracts.c3_ingestion import AdapterInput

from wellbe_c3_ingestion import AdapterRegistry, IngestionService, ManualTextAdapter, DocumentAdapter


def _build_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(ManualTextAdapter())
    registry.register(DocumentAdapter())
    return registry


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def ingest_task(payload_json: str) -> None:
    from wellbe_ingestion_worker.config import IngestionWorkerSettings

    data = json.loads(payload_json)
    settings = IngestionWorkerSettings()
    registry = _build_registry()
    service = IngestionService(registry, settings.vault_writer_url)

    adapter_input = AdapterInput(
        source_type=data["source_type"],
        raw_data=base64.b64decode(data["raw_data"]),
        captured_at=datetime.fromisoformat(data["captured_at"]),
        actor_id=UUID(data["actor_id"]),
        patient_id=UUID(data["patient_id"]),
        metadata=data.get("metadata"),
    )

    async def _run() -> None:
        try:
            await service.ingest(
                adapter_input=adapter_input,
                consent_snapshot_id=UUID(data["consent_snapshot_id"]),
                correlation_id=data["correlation_id"],
                trace_id=data["trace_id"],
                share_grant_id=UUID(data["share_grant_id"]) if data.get("share_grant_id") else None,
            )
        finally:
            await service.close()

    asyncio.run(_run())
