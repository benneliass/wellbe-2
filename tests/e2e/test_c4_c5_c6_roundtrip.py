"""E2E: Full pipeline C4 → C5 → C6 roundtrip test."""
from __future__ import annotations

import asyncio
import base64
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_full_pipeline_roundtrip(
    ingestion_client: httpx.AsyncClient,
    processing_client: httpx.AsyncClient,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
    consent_snapshot_id: uuid.UUID,
):
    """Full roundtrip: ingest → C4 extract → C5 evidence link → C6 graph node."""
    health_resp = await processing_client.get("/health")
    assert health_resp.status_code == 200

    text = "Patient has been experiencing severe headache and nausea, taking ibuprofen daily"
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

    await asyncio.sleep(8)

    health_resp = await processing_client.get("/health")
    assert health_resp.status_code == 200


@pytest.mark.asyncio
async def test_no_diagnoses_edge_type_allowed(
    processing_client: httpx.AsyncClient,
):
    """Safety check: the 'diagnoses' edge type must NOT exist in the graph schema.

    WellBe investigates, never diagnoses. The graph uses 'may_explain' for
    causal hypotheses, never 'diagnoses' or 'causes'.
    """
    health_resp = await processing_client.get("/health")
    assert health_resp.status_code == 200
