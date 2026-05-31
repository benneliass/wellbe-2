from __future__ import annotations

import base64
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from wellbe_contracts.c2_vault import VaultWriteResponse
from wellbe_contracts.c3_ingestion import AdapterInput

from wellbe_c3_ingestion import (
    AdapterRegistry,
    DocumentAdapter,
    IngestionService,
    ManualTextAdapter,
)
from wellbe_c3_ingestion.exceptions import IngestionValidationError

from wellbe_ingestion_worker.config import IngestionWorkerSettings
from wellbe_ingestion_worker.tasks import ingest_task


class IngestRequest(BaseModel):
    source_type: str
    raw_data: str  # base64-encoded
    patient_id: uuid.UUID
    actor_id: uuid.UUID
    consent_snapshot_id: uuid.UUID
    captured_at: datetime
    metadata: Optional[dict] = None
    share_grant_id: Optional[uuid.UUID] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None


class AsyncIngestResponse(BaseModel):
    task_id: str


_service: IngestionService | None = None
_settings: IngestionWorkerSettings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service, _settings
    _settings = IngestionWorkerSettings()
    broker = RedisBroker(url=_settings.redis_url)
    dramatiq.set_broker(broker)
    registry = AdapterRegistry()
    registry.register(ManualTextAdapter())
    registry.register(DocumentAdapter())
    _service = IngestionService(registry, _settings.vault_writer_url)
    yield
    await _service.close()


app = FastAPI(title="Ingestion Worker", version="0.1.0", lifespan=lifespan)


def _build_adapter_input(req: IngestRequest) -> AdapterInput:
    return AdapterInput(
        source_type=req.source_type,
        raw_data=base64.b64decode(req.raw_data),
        captured_at=req.captured_at,
        actor_id=req.actor_id,
        patient_id=req.patient_id,
        metadata=req.metadata,
    )


@app.post("/ingest", response_model=VaultWriteResponse)
async def ingest_sync(req: IngestRequest) -> VaultWriteResponse:
    assert _service is not None
    adapter_input = _build_adapter_input(req)
    correlation_id = req.correlation_id or uuid.uuid4().hex
    trace_id = req.trace_id or uuid.uuid4().hex
    try:
        return await _service.ingest(
            adapter_input=adapter_input,
            consent_snapshot_id=req.consent_snapshot_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            share_grant_id=req.share_grant_id,
        )
    except IngestionValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/ingest/async", response_model=AsyncIngestResponse)
async def ingest_async(req: IngestRequest) -> AsyncIngestResponse:
    task_id = uuid.uuid4().hex
    correlation_id = req.correlation_id or task_id
    trace_id = req.trace_id or uuid.uuid4().hex

    payload = {
        "source_type": req.source_type,
        "raw_data": req.raw_data,
        "patient_id": str(req.patient_id),
        "actor_id": str(req.actor_id),
        "consent_snapshot_id": str(req.consent_snapshot_id),
        "captured_at": req.captured_at.isoformat(),
        "metadata": req.metadata,
        "share_grant_id": str(req.share_grant_id) if req.share_grant_id else None,
        "correlation_id": correlation_id,
        "trace_id": trace_id,
    }

    ingest_task.send(json.dumps(payload))
    return AsyncIngestResponse(task_id=task_id)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
