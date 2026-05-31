import hashlib
import uuid
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_vault_write_and_retrieve(vault_client, patient_id, actor_id, consent_snapshot_id):
    """Full round-trip: write an event to vault, then retrieve it by ID."""
    raw_payload = b"Hello, this is a manual text entry for testing."
    content_hash = hashlib.sha256(raw_payload).hexdigest()
    captured_at = datetime.now(timezone.utc).isoformat()
    correlation_id = uuid.uuid4().hex
    trace_id = uuid.uuid4().hex
    idempotency_key = f"{patient_id}:{content_hash}"

    write_body = {
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "normalized_payload": raw_payload.decode("latin-1"),
        "adapter_provenance": {
            "source_type": "manual_text",
            "captured_at": captured_at,
            "adapter_name": "wellbe-manual-text",
            "adapter_version": "0.1.0",
            "mime_type": "text/plain",
            "encoding": "utf-8",
            "language": "en",
        },
        "idempotency_key": idempotency_key,
        "consent_snapshot_id": str(consent_snapshot_id),
        "correlation_id": correlation_id,
        "trace_id": trace_id,
        "mime_type": "text/plain",
        "encoding": "utf-8",
        "language": "en",
    }

    resp = await vault_client.post("/vault/events", json=write_body)
    assert resp.status_code == 201, f"Write failed: {resp.text}"
    data = resp.json()
    event_id = data["event_id"]
    assert data["content_hash"] == content_hash
    assert data["duplicate_of_event_id"] is None

    resp = await vault_client.get(f"/vault/events/{event_id}")
    assert resp.status_code == 200
    event = resp.json()
    assert event["id"] == event_id
    assert event["patient_id"] == str(patient_id)
    assert event["source_type"] == "manual_text"
    assert event["content_hash"] == content_hash
    assert event["adapter_name"] == "wellbe-manual-text"
    assert event["consent_snapshot_id"] == str(consent_snapshot_id)


@pytest.mark.asyncio
async def test_vault_deduplication(vault_client, patient_id, actor_id, consent_snapshot_id):
    """Writing the same payload twice returns the same event_id (dedup by content_hash)."""
    raw_payload = b"Duplicate test payload - should only store once."
    content_hash = hashlib.sha256(raw_payload).hexdigest()
    captured_at = datetime.now(timezone.utc).isoformat()
    idempotency_key = f"{patient_id}:{content_hash}"

    body = {
        "patient_id": str(patient_id),
        "actor_id": str(actor_id),
        "normalized_payload": raw_payload.decode("latin-1"),
        "adapter_provenance": {
            "source_type": "manual_text",
            "captured_at": captured_at,
            "adapter_name": "wellbe-manual-text",
            "adapter_version": "0.1.0",
            "mime_type": "text/plain",
            "encoding": "utf-8",
        },
        "idempotency_key": idempotency_key,
        "consent_snapshot_id": str(consent_snapshot_id),
        "correlation_id": uuid.uuid4().hex,
        "trace_id": uuid.uuid4().hex,
        "mime_type": "text/plain",
        "encoding": "utf-8",
    }

    resp1 = await vault_client.post("/vault/events", json=body)
    assert resp1.status_code == 201
    event_id_1 = resp1.json()["event_id"]

    body["correlation_id"] = uuid.uuid4().hex
    body["trace_id"] = uuid.uuid4().hex
    resp2 = await vault_client.post("/vault/events", json=body)
    assert resp2.status_code == 201
    event_id_2 = resp2.json()["event_id"]

    assert event_id_1 == event_id_2
