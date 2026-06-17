"""Unit tests for the what-changed delta engine (WEL-56).

Covers the calm, source-linked change-event semantics: open loops rank first,
copy says "changed"/"new" (never "worse"), every event carries a ranking reason
and a source cue, and ranking is category-then-recency (never abnormality-first).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from wellbe_api.delta import engine
from wellbe_contracts.delta import DeltaCategory

_NOW = datetime.now(UTC)
_SINCE = _NOW - timedelta(days=14)


@dataclass
class _Item:
    status: str
    title: str
    created_at: datetime
    updated_at: datetime
    pending_item_id: uuid.UUID = field(default_factory=uuid.uuid4)
    resolved_at: datetime | None = None
    cancelled_at: datetime | None = None


@dataclass
class _Transition:
    to_status: str
    thread_id: uuid.UUID = field(default_factory=uuid.uuid4)
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: _NOW)


@dataclass
class _Thread:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: _NOW)


def test_new_open_item_is_open_loop_with_calm_reason():
    item = _Item(status="open", title="Chest x-ray follow-up", created_at=_NOW, updated_at=_NOW)
    ev = engine._pending_event(item, _SINCE)
    assert ev.category is DeltaCategory.OPEN_LOOP
    assert ev.ranking_reason == "New open item"
    assert ev.source.ref_type == "pending_item"
    assert "worse" not in (ev.detail or "").lower()


def test_resolved_item_reads_as_resolved_not_worse():
    item = _Item(
        status="resolved", title="Iron recheck",
        created_at=_NOW - timedelta(days=30), updated_at=_NOW, resolved_at=_NOW,
    )
    ev = engine._pending_event(item, _SINCE)
    assert ev.ranking_reason == "Item resolved"
    assert "worse" not in (ev.detail or "").lower()


def test_updated_item_reads_as_changed():
    item = _Item(
        status="waiting_on_result", title="Referral",
        created_at=_NOW - timedelta(days=30), updated_at=_NOW,
    )
    ev = engine._pending_event(item, _SINCE)
    assert ev.ranking_reason == "Open item changed"
    assert ev.detail == "Now: Waiting on result."


def test_transition_event_is_lifecycle_and_source_linked():
    t = _Transition(to_status="waiting_for_result")
    ev = engine._transition_event(t, "Persistent cough")
    assert ev.category is DeltaCategory.LIFECYCLE
    assert ev.ranking_reason == "Status changed"
    assert ev.detail == "Now: Waiting for result."
    assert ev.source.ref_type == "health_thread"


def test_ranking_open_loop_before_lifecycle_before_new_fact():
    new_item = _Item(status="open", title="A", created_at=_NOW, updated_at=_NOW)
    open_ev = engine._pending_event(new_item, _SINCE)
    life_ev = engine._transition_event(_Transition(to_status="referred"), "B")
    fact_ev = engine._new_thread_event(_Thread(title="C"))
    ordered = sorted([fact_ev, life_ev, open_ev], key=engine._sort_key, reverse=True)
    assert [e.category for e in ordered] == [
        DeltaCategory.OPEN_LOOP,
        DeltaCategory.LIFECYCLE,
        DeltaCategory.NEW_FACT,
    ]
