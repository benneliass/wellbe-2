"""E2E: the C13 /v1/capture write path (WEL-155).

CaptureModal's contract: POST /v1/capture -> C3 adapter -> C2 Vault, returning
201 with the durable raw record id and processing:"pending". Verifies the
type-specific envelope, the deterministic-id idempotency replay (same
Idempotency-Key returns the same capture_id), that the raw record is retrievable
from the Vault, and the required-header / validation guards.

Requires the cluster up with the API on API_URL and vault-writer on
VAULT_WRITER_URL (port-forwards).
"""

from __future__ import annotations

import uuid

import pytest


def _auth(actor_id: uuid.UUID) -> dict[str, str]:
    return {"X-Wellbe-Actor-Id": str(actor_id), "X-Wellbe-Actor-Type": "controller"}


@pytest.mark.asyncio
async def test_capture_symptom_roundtrip(api_client, vault_client, actor_id):
    idem = f"e2e-{uuid.uuid4()}"
    body = {
        "capture_type": "symptom",
        "payload": {"description": "Dull lower-back ache after sitting", "severity": "Moderate"},
    }
    headers = {**_auth(actor_id), "Idempotency-Key": idem}

    resp = await api_client.post("/v1/capture", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "captured"
    assert data["processing"] == "pending"
    capture_id = data["capture_id"]

    # Raw record is durable immediately and retrievable from the Vault.
    vresp = await vault_client.get(f"/vault/events/{capture_id}")
    assert vresp.status_code == 200, vresp.text
    event = vresp.json()
    assert event["actor_id"] == str(actor_id)
    assert event["source_type"] == "manual_text"
    assert event["source_metadata"]["capture_type"] == "symptom"


@pytest.mark.asyncio
async def test_capture_idempotent_replay(api_client, actor_id):
    """Same Idempotency-Key => same durable capture id (no duplicate raw record)."""
    idem = f"e2e-{uuid.uuid4()}"
    body = {"capture_type": "note", "payload": {"text": "Ask the doctor about my sleep"}}
    headers = {**_auth(actor_id), "Idempotency-Key": idem}

    first = await api_client.post("/v1/capture", json=body, headers=headers)
    assert first.status_code == 201, first.text
    second = await api_client.post("/v1/capture", json=body, headers=headers)
    assert second.status_code == 201, second.text
    assert first.json()["capture_id"] == second.json()["capture_id"]


@pytest.mark.asyncio
async def test_capture_requires_idempotency_key(api_client, actor_id):
    body = {"capture_type": "note", "payload": {"text": "no key"}}
    resp = await api_client.post("/v1/capture", json=body, headers=_auth(actor_id))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_capture_requires_auth(api_client):
    body = {"capture_type": "note", "payload": {"text": "anon"}}
    resp = await api_client.post(
        "/v1/capture", json=body, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert resp.status_code == 401
