"""E2E: thread-scoped graph read API (WEL-156).

Exercises the HTTP contract against the live cluster: an owned thread returns a
well-formed subgraph envelope; an unowned/absent thread returns a non-leaking
404; an invalid edge-type filter returns a 422 problem. (Seeded-data scoping and
patient isolation are covered by the C6 live integration test.)

Requires the cluster up with the API on API_URL (port-forward).
"""

from __future__ import annotations

import uuid

import pytest


def _auth(actor_id: uuid.UUID) -> dict[str, str]:
    return {"X-Wellbe-Actor-Id": str(actor_id), "X-Wellbe-Actor-Type": "controller"}


async def _make_thread(api_client, actor_id: uuid.UUID, title: str) -> str:
    resp = await api_client.post("/v1/threads", json={"title": title}, headers=_auth(actor_id))
    assert resp.status_code == 201, resp.text
    return resp.json()["thread_id"]


@pytest.mark.asyncio
async def test_owned_thread_returns_subgraph_envelope(api_client, actor_id):
    thread_id = await _make_thread(api_client, actor_id, "Graph thread")
    resp = await api_client.get(
        f"/v2/graph/threads/{thread_id}", headers=_auth(actor_id)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "c13.graph.subgraph.v2"
    assert body["thread_id"] == thread_id
    assert isinstance(body["nodes"], list)
    assert isinstance(body["edges"], list)
    assert "page_info" in body


@pytest.mark.asyncio
async def test_unowned_thread_is_not_found(api_client, actor_id):
    # A different actor cannot read this actor's thread (non-leaking 404).
    thread_id = await _make_thread(api_client, actor_id, "Private graph thread")
    other = uuid.uuid4()
    resp = await api_client.get(
        f"/v2/graph/threads/{thread_id}", headers=_auth(other)
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_absent_thread_is_not_found(api_client, actor_id):
    resp = await api_client.get(
        f"/v2/graph/threads/{uuid.uuid4()}", headers=_auth(actor_id)
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_invalid_edge_filter_is_rejected(api_client, actor_id):
    thread_id = await _make_thread(api_client, actor_id, "Filter thread")
    # `causes` is a prohibited diagnostic verb, never in the personal vocabulary.
    resp = await api_client.get(
        f"/v2/graph/threads/{thread_id}?edge_types=causes", headers=_auth(actor_id)
    )
    assert resp.status_code == 422, resp.text
