"""E2E: Home coverage-aware signals summary API (WEL-91).

Exercises the HTTP contract against the live cluster: a self-read returns a
well-formed, never-alarm summary envelope (200). A fresh actor with no data is
honestly suppressed (no "all clear"), and every area is an explicit unknown
rather than green.

Requires the cluster up with the API on API_URL (port-forward).
"""

from __future__ import annotations

import uuid

import pytest

_BANNED = ("all clear", "in range", "all good", "you're healthy", "no concern")


def _auth(actor_id: uuid.UUID) -> dict[str, str]:
    return {"X-Wellbe-Actor-Id": str(actor_id), "X-Wellbe-Actor-Type": "controller"}


@pytest.mark.asyncio
async def test_signals_self_read_envelope(api_client, actor_id):
    resp = await api_client.get("/v2/signals", headers=_auth(actor_id))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "c13.signals.v2"
    assert body["not_diagnosis"] is True
    assert body["areas_total"] == 6
    assert 0 <= body["areas_with_data"] <= 6
    blob = " ".join(
        [body["headline"], body["coverage_label"], body["note"]]
        + [a["status_label"] for a in body["areas"]]
    ).lower()
    assert not any(b in blob for b in _BANNED)


@pytest.mark.asyncio
async def test_fresh_actor_is_suppressed_never_reassured(api_client, actor_id):
    # A brand-new actor has no signal-bearing data -> honest, suppressed state.
    resp = await api_client.get("/v2/signals", headers=_auth(actor_id))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["suppressed"] is True
    assert body["areas_with_data"] == 0
    # No area is implied "green"/in-range.
    for a in body["areas"]:
        assert a["status"] == "no_data"
