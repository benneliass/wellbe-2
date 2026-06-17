"""E2E: non-diagnostic pattern read API (WEL-79).

Exercises the HTTP contract against the live cluster: an authenticated self-read
returns a well-formed patterns envelope (200) with the non-diagnostic framing
note; the bound on `limit` is enforced (422). Seeded-data scoping and patient
isolation are covered by the C6 live integration test.

Requires the cluster up with the API on API_URL (port-forward).
"""

from __future__ import annotations

import uuid

import pytest


def _auth(actor_id: uuid.UUID) -> dict[str, str]:
    return {"X-Wellbe-Actor-Id": str(actor_id), "X-Wellbe-Actor-Type": "controller"}


@pytest.mark.asyncio
async def test_patterns_self_read_returns_envelope(api_client, actor_id):
    resp = await api_client.get("/v2/patterns", headers=_auth(actor_id))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "c13.patterns.v2"
    assert isinstance(body["patterns"], list)
    assert body["not_diagnosis"] is True
    # Every surfaced candidate must be source-linked and carry a caveat.
    for p in body["patterns"]:
        assert p["caveat"]
        assert len(p["sources"]) >= 1
        assert "diagnos" not in p["relation_phrase"].lower()
        assert "cause" not in p["relation_phrase"].lower()


@pytest.mark.asyncio
async def test_patterns_limit_bound_enforced(api_client, actor_id):
    resp = await api_client.get("/v2/patterns?limit=999", headers=_auth(actor_id))
    assert resp.status_code == 422, resp.text
