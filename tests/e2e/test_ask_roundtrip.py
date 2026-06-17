"""E2E: the Ask WellBe answer engine (WEL-166).

Exercises the approved decision end-to-end against the live cluster:
- a benign question matching the user's own thread returns an ``answered`` mode
  with source-linked citations (no orphan claims);
- an urgent input returns ``urgent`` escalation without touching records;
- a diagnosis/treatment request returns ``out_of_scope_redirect``;
- an unrelated question returns ``no_sources`` (closed corpus, no outside
  knowledge).

Requires the cluster up with the API on API_URL (port-forward).
"""

from __future__ import annotations

import uuid

import pytest


def _auth(actor_id: uuid.UUID) -> dict[str, str]:
    return {"X-Wellbe-Actor-Id": str(actor_id), "X-Wellbe-Actor-Type": "controller"}


async def _ask(api_client, actor_id: uuid.UUID, question: str) -> dict:
    resp = await api_client.post(
        "/v2/ask",
        json={"schema_version": "c13.ask.request.v1", "question": question},
        headers=_auth(actor_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_ask_answers_from_own_records(api_client, actor_id):
    # Seed a thread so the closed corpus has something to ground on.
    resp = await api_client.post(
        "/v1/threads", json={"title": "Persistent headaches"}, headers=_auth(actor_id)
    )
    assert resp.status_code == 201, resp.text

    answer = await _ask(api_client, actor_id, "what's going on with my headaches?")
    assert answer["mode"] == "answered", answer
    assert answer["not_diagnosis"] is True
    # Source-linked: at least one citation back to the user's own thread.
    assert any(c["ref_type"] == "health_thread" for c in answer["citations"]), answer
    assert "headache" in answer["answer_text"].lower()


@pytest.mark.asyncio
async def test_ask_urgent_input_escalates(api_client, actor_id):
    answer = await _ask(api_client, actor_id, "I have crushing chest pain and can't breathe")
    assert answer["mode"] == "urgent", answer
    assert not answer["citations"]
    assert "emergency" in answer["answer_text"].lower()


@pytest.mark.asyncio
async def test_ask_diagnosis_request_redirects(api_client, actor_id):
    answer = await _ask(api_client, actor_id, "do I have diabetes?")
    assert answer["mode"] == "out_of_scope_redirect", answer
    assert not answer["citations"]


@pytest.mark.asyncio
async def test_ask_unrelated_question_has_no_sources(api_client, actor_id):
    answer = await _ask(
        api_client, actor_id, "tell me about my zorblax readings from mars"
    )
    assert answer["mode"] == "no_sources", answer
    assert not answer["citations"]
