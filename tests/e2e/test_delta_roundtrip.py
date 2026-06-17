"""E2E: what-changed delta digest API (WEL-56).

Exercises the HTTP contract against the live cluster: a self-read returns a
well-formed digest envelope (200) with calm, non-diagnostic framing; a thread
transition shows up as a lifecycle delta; the `limit` bound is enforced (422).

Requires the cluster up with the API on API_URL (port-forward).
"""

from __future__ import annotations

import uuid

import pytest


def _auth(actor_id: uuid.UUID) -> dict[str, str]:
    return {"X-Wellbe-Actor-Id": str(actor_id), "X-Wellbe-Actor-Type": "controller"}


@pytest.mark.asyncio
async def test_delta_self_read_returns_envelope(api_client, actor_id):
    resp = await api_client.get("/v2/delta", headers=_auth(actor_id))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "c13.delta.v2"
    assert isinstance(body["events"], list)
    assert body["not_diagnosis"] is True
    assert body["window_label"]
    for e in body["events"]:
        assert e["ranking_reason"]
        assert e["source"]["source_id"]
        # Calm, non-diagnostic wording.
        assert "worse" not in (e.get("detail") or "").lower()


@pytest.mark.asyncio
async def test_delta_reflects_a_new_thread(api_client, actor_id):
    # Create a thread for this actor, then expect a "new fact" delta for it.
    resp = await api_client.post(
        "/v1/threads", json={"title": "Delta e2e thread"}, headers=_auth(actor_id)
    )
    assert resp.status_code == 201, resp.text
    thread_id = resp.json()["thread_id"]

    resp = await api_client.get("/v2/delta", headers=_auth(actor_id))
    assert resp.status_code == 200, resp.text
    sources = {e["source"]["source_id"] for e in resp.json()["events"]}
    assert thread_id in sources


@pytest.mark.asyncio
async def test_delta_limit_bound_enforced(api_client, actor_id):
    resp = await api_client.get("/v2/delta?limit=999", headers=_auth(actor_id))
    assert resp.status_code == 422, resp.text
