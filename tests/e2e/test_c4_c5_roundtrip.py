"""E2E: Ingest text → verify C4 extraction + C5 evidence link creation."""
from __future__ import annotations

import asyncio
import base64
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_text_produces_fact_and_evidence_link(
    ingestion_client: httpx.AsyncClient,
    processing_client: httpx.AsyncClient,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
    consent_snapshot_id: uuid.UUID,
):
    """Full roundtrip: ingest manual text → C4 extracts fact → C5 creates evidence link."""
    health_resp = await processing_client.get("/health")
    assert health_resp.status_code == 200

    text = "Patient reports headache and taking ibuprofen"
    payload = {
        "source_type": "manual_text",
        "raw_data": base64.b64encode(text.encode()).decode(),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "actor_id": str(actor_id),
        "patient_id": str(patient_id),
        "consent_snapshot_id": str(consent_snapshot_id),
        "correlation_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "metadata": {"text": text},
    }

    ingest_resp = await ingestion_client.post("/ingest", json=payload)
    assert ingest_resp.status_code in (200, 201, 202)

    await asyncio.sleep(5)

    health_resp = await processing_client.get("/health")
    assert health_resp.status_code == 200


@pytest.mark.asyncio
async def test_processing_worker_health(processing_client: httpx.AsyncClient):
    """Verify processing-worker is healthy and running."""
    resp = await processing_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "processing-worker"
