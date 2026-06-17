"""E2E: the C13 Visit Packet flow (WEL-30 / WEL-68).

Exercises the approved decision end-to-end against the live cluster:
generate (two-layer, source-linked) -> C10 pre-share gate -> named-recipient,
time-boxed, passcode-protected, revocable share link -> public recipient read
-> revoke -> 404 (future access only). Also asserts the passcode gate returns
404 until the right passcode is given.

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
async def test_visit_packet_generate_share_read_revoke(api_client, actor_id):
    thread_id = await _make_thread(api_client, actor_id, "Persistent cough")

    gen = await api_client.post(
        "/v2/visit-packets",
        json={
            "title": "Visit packet",
            "thread_ids": [thread_id],
            "include_summary": True,
            "prep": {"questions": ["What could be causing this cough?"], "goals": []},
        },
        headers=_auth(actor_id),
    )
    assert gen.status_code == 201, gen.text
    packet = gen.json()
    packet_id = packet["packet_id"]
    statements = packet["statements"]
    assert any(s["layer"] == "patient_prep" for s in statements)
    assert any(s["layer"] == "summary" for s in statements)
    # No orphan claims: every non-absent statement carries a source ref.
    for s in statements:
        if not s["absent"]:
            assert s["source_refs"], s

    # Share -> C10 gate passes -> revocable link.
    share = await api_client.post(
        f"/v2/visit-packets/{packet_id}/share",
        json={"recipient_name": "Dr. Jane Smith", "expires_in_hours": 168},
        headers=_auth(actor_id),
    )
    assert share.status_code == 201, share.text
    token = share.json()["share_token"]
    link_id = share.json()["share_link_id"]

    # Public recipient read (no auth) works while active.
    pub = await api_client.get(f"/v2/share/{token}")
    assert pub.status_code == 200, pub.text
    assert pub.json()["statements"]

    # Revoke -> future access only -> 404.
    rev = await api_client.post(
        f"/v2/visit-packets/{packet_id}/share/{link_id}/revoke", headers=_auth(actor_id)
    )
    assert rev.status_code == 204, rev.text
    gone = await api_client.get(f"/v2/share/{token}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_visit_packet_passcode_gate(api_client, actor_id):
    thread_id = await _make_thread(api_client, actor_id, "Sleep changes")
    gen = await api_client.post(
        "/v2/visit-packets",
        json={"thread_ids": [thread_id], "include_summary": True},
        headers=_auth(actor_id),
    )
    assert gen.status_code == 201, gen.text
    packet_id = gen.json()["packet_id"]

    share = await api_client.post(
        f"/v2/visit-packets/{packet_id}/share",
        json={"recipient_name": "Dr. Smith", "expires_in_hours": 24, "passcode": "open-sesame"},
        headers=_auth(actor_id),
    )
    assert share.status_code == 201, share.text
    assert share.json()["passcode_required"] is True
    token = share.json()["share_token"]

    # No passcode -> 404 (no information leak).
    assert (await api_client.get(f"/v2/share/{token}")).status_code == 404
    # Wrong passcode -> 404.
    bad = await api_client.get(f"/v2/share/{token}", headers={"X-Share-Passcode": "wrong"})
    assert bad.status_code == 404
    # Right passcode -> 200.
    ok = await api_client.get(f"/v2/share/{token}", headers={"X-Share-Passcode": "open-sesame"})
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
async def test_visit_packet_requires_auth(api_client):
    resp = await api_client.post("/v2/visit-packets", json={"thread_ids": []})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unknown_share_token_is_404(api_client):
    resp = await api_client.get(f"/v2/share/{uuid.uuid4().hex}")
    assert resp.status_code == 404
