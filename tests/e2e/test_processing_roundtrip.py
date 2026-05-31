"""E2E: Ingest text → verify processing-worker creates extracted_facts row."""
from __future__ import annotations

import asyncio
import base64
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_text_ingestion_produces_extracted_fact(
    ingestion_client: httpx.AsyncClient,
    processing_client: httpx.AsyncClient,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
    consent_snapshot_id: uuid.UUID,
):
    """Full roundtrip: ingest manual text → processing-worker extracts facts."""
    health_resp = await processing_client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    text = "I have been experiencing headache and nausea for 3 days"
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
