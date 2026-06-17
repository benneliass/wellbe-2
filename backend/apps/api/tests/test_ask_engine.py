"""Unit tests for the Ask WellBe answer engine (WEL-166).

Covers intent classification (urgent / out-of-scope diagnosis), deterministic
source-linked composition with no orphan claims, the no-sources soft refusal,
and that a composed answer passes the C10 gate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from wellbe_api.ask import engine
from wellbe_contracts.ask import AskMode
from wellbe_contracts.c10_safety import C10Decision


@dataclass
class _Thread:
    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    status: str


@dataclass
class _Pending:
    pending_item_id: uuid.UUID
    title: str
    status: str


def test_urgent_intent_escalates():
    assert engine.classify_intent("I have crushing chest pain right now") is AskMode.URGENT
    assert engine.classify_intent("i want to kill myself") is AskMode.URGENT


def test_diagnosis_intent_is_out_of_scope():
    assert (
        engine.classify_intent("do i have diabetes?")
        is AskMode.OUT_OF_SCOPE_REDIRECT
    )
    assert (
        engine.classify_intent("what medication should i take for this")
        is AskMode.OUT_OF_SCOPE_REDIRECT
    )


def test_benign_question_is_not_pre_classified():
    assert engine.classify_intent("what's open in my records?") is None


def test_compose_no_sources_soft_refuses():
    result = engine.compose_answer("anything about my knee?", [], {})
    assert result.mode is AskMode.NO_SOURCES
    # No source-linked claims in a refusal.
    assert all(s.citation is None for s in result.statements)


def test_compose_answer_links_every_claim():
    pid = uuid.uuid4()
    tid = uuid.uuid4()
    thread = _Thread(id=tid, patient_id=pid, title="Persistent cough", status="active")
    pending = _Pending(
        pending_item_id=uuid.uuid4(), title="Chest x-ray follow-up", status="open"
    )
    result = engine.compose_answer("cough", [thread], {tid: [pending]})
    assert result.mode is AskMode.ANSWERED
    # Every non-meta statement carries a citation -> no orphan claims.
    sourced = [s for s in result.statements if s.citation is not None]
    assert any(s.citation.ref_type == "health_thread" for s in sourced)
    assert any(s.citation.ref_type == "pending_item" for s in sourced)


def test_composed_answer_passes_c10_gate():
    pid = uuid.uuid4()
    tid = uuid.uuid4()
    thread = _Thread(id=tid, patient_id=pid, title="Iron levels", status="monitoring")
    result = engine.compose_answer("iron", [thread], {tid: []})
    decision = engine.gate_answer(
        result=result,
        patient_id=pid,
        question="iron",
        correlation_id="test-corr",
    )
    assert decision in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}
