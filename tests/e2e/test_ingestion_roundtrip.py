import base64
import uuid
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_manual_text_ingestion_roundtrip(
    ingestion_client, vault_client, patient_id, actor_id, consent_snapshot_id
):
    """
    E2E: Submit text via ingestion-worker (C3), which validates via ManualTextAdapter,
    then calls vault-writer (C2) to persist. Verify the event is retrievable from vault.
    """
    text = "Patient reports mild headache for the past three days."
    raw_data_b64 = base64.b64encode(text.encode()).decode()
    captured_at = datetime.now(timezone.utc).isoformat()

    ingest_body = {
        "source_type": "manual_text",
        "raw_data": raw_data_b64,
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "consent_snapshot_id": str(consent_snapshot_id),
        "captured_at": captured_at,
    }

    resp = await ingestion_client.post("/ingest", json=ingest_body)
    assert resp.status_code == 200, f"Ingestion failed: {resp.text}"
    data = resp.json()
    event_id = data["event_id"]
    assert data["content_hash"]
    assert data["ingested_at"]

    resp = await vault_client.get(f"/vault/events/{event_id}")
    assert resp.status_code == 200
    event = resp.json()
    assert event["id"] == event_id
    assert event["patient_id"] == str(patient_id)
    assert event["actor_id"] == str(actor_id)
    assert event["source_type"] == "manual_text"
    assert event["mime_type"] == "text/plain"
    assert event["adapter_name"] == "wellbe-manual-text"


@pytest.mark.asyncio
async def test_document_ingestion_roundtrip(
    ingestion_client, vault_client, patient_id, actor_id, consent_snapshot_id
):
    """
    E2E: Submit a PDF-like binary via ingestion-worker (C3), verify it lands in the vault (C2).
    """
    fake_pdf = b"%PDF-1.4 fake pdf content for testing" + b"\x00" * 100
    raw_data_b64 = base64.b64encode(fake_pdf).decode()
    captured_at = datetime.now(timezone.utc).isoformat()

    ingest_body = {
        "source_type": "pdf",
        "raw_data": raw_data_b64,
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "consent_snapshot_id": str(consent_snapshot_id),
        "captured_at": captured_at,
        "metadata": {"mime_type": "application/pdf"},
    }

    resp = await ingestion_client.post("/ingest", json=ingest_body)
    assert resp.status_code == 200, f"Ingestion failed: {resp.text}"
    data = resp.json()
    event_id = data["event_id"]

    resp = await vault_client.get(f"/vault/events/{event_id}")
    assert resp.status_code == 200
    event = resp.json()
    assert event["source_type"] == "pdf"
    assert event["mime_type"] == "application/pdf"
    assert event["adapter_name"] == "wellbe-document"


@pytest.mark.asyncio
async def test_ingestion_validation_failure(ingestion_client, patient_id, actor_id, consent_snapshot_id):
    """
    E2E: Submit an empty payload — adapter validation should reject it with 422.
    """
    raw_data_b64 = base64.b64encode(b"").decode()
    captured_at = datetime.now(timezone.utc).isoformat()

    ingest_body = {
        "source_type": "manual_text",
        "raw_data": raw_data_b64,
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "consent_snapshot_id": str(consent_snapshot_id),
        "captured_at": captured_at,
    }

    resp = await ingestion_client.post("/ingest", json=ingest_body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingestion_unknown_source_type(ingestion_client, patient_id, actor_id, consent_snapshot_id):
    """
    E2E: Submit with an unregistered source type — should get 400.
    """
    raw_data_b64 = base64.b64encode(b"some data").decode()
    captured_at = datetime.now(timezone.utc).isoformat()

    ingest_body = {
        "source_type": "unknown_type_xyz",
        "raw_data": raw_data_b64,
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "consent_snapshot_id": str(consent_snapshot_id),
        "captured_at": captured_at,
    }

    resp = await ingestion_client.post("/ingest", json=ingest_body)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_async_ingestion_enqueue(ingestion_client, patient_id, actor_id, consent_snapshot_id):
    """
    E2E: Submit via async endpoint — should return a task_id (Dramatiq enqueue).
    Note: actual processing depends on Dramatiq worker being up. We only verify the enqueue succeeds.
    """
    text = "Async ingestion test."
    raw_data_b64 = base64.b64encode(text.encode()).decode()
    captured_at = datetime.now(timezone.utc).isoformat()

    ingest_body = {
        "source_type": "manual_text",
        "raw_data": raw_data_b64,
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "consent_snapshot_id": str(consent_snapshot_id),
        "captured_at": captured_at,
    }

    resp = await ingestion_client.post("/ingest/async", json=ingest_body)
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert len(data["task_id"]) > 0
