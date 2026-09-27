"""C13 /v2 thread timeline: one chronological, read-only view of a Health Thread.

Stitches together rows that already exist for the thread — its C7 status
transitions, the C2 captures behind its memories, and its C9 open loops — and
resolves the thread memories' source refs into plain labels for the evidence
drawer. Nothing is inferred: an event appears only when a stored row backs it,
and no clinical value is copied (labels only, like the memory read model).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c2_vault.models import RawContextEventRow
from wellbe_c4_processing.models import ExtractedFactRow
from wellbe_c6_graph.models import KgNodeRow
from wellbe_c7_thread.models import HealthThreadRow, ThreadStateTransitionRow
from wellbe_c8_memories.models import MemoryEntryRow, MemorySourceRefRow
from wellbe_c9_continuity.models import PendingItemRow
from wellbe_contracts.c13_api import ProblemCode

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError
from wellbe_api.records.engine import source_for

router = APIRouter(prefix="/v2", tags=["v2-thread-timeline"])

TimelineEventKind = Literal["thread_started", "status_changed", "capture", "open_loop"]
SourceComponent = Literal["c2", "c5", "c16"]

_FACT_CONFIDENCE_BASIS = "How clearly WellBe picked this out of what you added"

_CAPTURE_TITLE = {
    "symptom": "You described how you feel",
    "lab": "You added a result",
    "note": "You added a note",
    "document": "You added a document",
}


def _capture_title(event: Any, fallback: str) -> str:
    capture_type = str((event.source_metadata or {}).get("capture_type") or "")
    return _CAPTURE_TITLE.get(capture_type, fallback)


class TimelineSourceV2(BaseModel):
    """One backing source, labelled for display (SourceRefV2-shaped, never an id label)."""

    source_ref_id: str
    source_ref_type: str
    component: SourceComponent
    kind: str
    display_label: str
    date: datetime | None = None
    confidence: float | None = None
    confidence_basis: str | None = None
    review_marker: str | None = None
    capture_id: str | None = None


class TimelineEventV2(BaseModel):
    event_id: str
    kind: TimelineEventKind
    occurred_at: datetime
    title: str
    detail: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    actor: Literal["you", "wellbe"] | None = None
    item_type: str | None = None
    item_status: str | None = None
    due_at: datetime | None = None
    source_ref_ids: list[str] = Field(default_factory=list)


class ThreadTimelineV2(BaseModel):
    schema_version: Literal["c13.thread_timeline.v2"] = "c13.thread_timeline.v2"
    thread_id: str
    status: str
    # Statuses the thread has actually entered, oldest first, ending at ``status``.
    status_history: list[str]
    # Oldest first.
    events: list[TimelineEventV2]
    # Every source any event or thread memory points at, resolved to a display label.
    sources: list[TimelineSourceV2]


@dataclass
class TimelineInputs:
    thread: Any
    transitions: Sequence[Any] = ()
    captures: Mapping[uuid.UUID, Any] = field(default_factory=dict)
    facts: Mapping[uuid.UUID, Any] = field(default_factory=dict)
    nodes: Mapping[uuid.UUID, Any] = field(default_factory=dict)
    pending: Sequence[Any] = ()
    # (source_ref_type, source_ref_id) pairs held by the thread's memories.
    memory_refs: Sequence[tuple[str, uuid.UUID]] = ()


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def status_history(thread: Any, transitions: Iterable[Any]) -> list[str]:
    """The statuses entered, oldest first; only real transitions contribute."""
    ordered = sorted(transitions, key=lambda t: t.transition_seq)
    if not ordered:
        return [str(thread.status)]
    history = [str(ordered[0].from_status)]
    history += [str(t.to_status) for t in ordered]
    if history[-1] != thread.status:
        history.append(str(thread.status))
    return history


def _capture_source(event: Any) -> TimelineSourceV2:
    src = source_for(event)
    return TimelineSourceV2(
        source_ref_id=str(event.id),
        source_ref_type="c2_capture",
        component="c2",
        kind=src.kind,
        display_label=src.display_label,
        date=_utc(event.captured_at),
        review_marker=src.review_marker,
        capture_id=str(event.id),
    )


def _fact_source(fact: Any, captures: Mapping[uuid.UUID, Any]) -> TimelineSourceV2:
    event = captures.get(fact.raw_context_event_id)
    review = source_for(event).review_marker if event is not None else None
    return TimelineSourceV2(
        source_ref_id=str(fact.id),
        source_ref_type="c4_extracted_fact",
        component="c5",
        kind="lab" if fact.fact_type in ("lab_result", "vital_sign") else "extracted_fact",
        display_label=str(fact.entity_label).strip() or "Something you added",
        date=_utc(fact.captured_at),
        confidence=float(fact.extraction_confidence),
        confidence_basis=_FACT_CONFIDENCE_BASIS,
        review_marker=review,
        capture_id=str(fact.raw_context_event_id) if event is not None else None,
    )


def _node_source(node: Any) -> TimelineSourceV2:
    return TimelineSourceV2(
        source_ref_id=str(node.id),
        source_ref_type="c6_kg_node",
        component="c5",
        kind="linked_concept",
        display_label=str(node.display_label).strip() or "Linked concept",
        date=_utc(node.first_seen_at),
        review_marker="AI-summarized",
    )


def build_timeline(inputs: TimelineInputs) -> ThreadTimelineV2:
    """Pure transform from stored rows to the timeline read model."""
    thread = inputs.thread
    sources: dict[str, TimelineSourceV2] = {}

    for event in inputs.captures.values():
        sources[str(event.id)] = _capture_source(event)
    for ref_type, ref_id in inputs.memory_refs:
        key = str(ref_id)
        if key in sources:
            continue
        if ref_type == "c4_extracted_fact" and ref_id in inputs.facts:
            sources[key] = _fact_source(inputs.facts[ref_id], inputs.captures)
        elif ref_type == "c6_kg_node" and ref_id in inputs.nodes:
            sources[key] = _node_source(inputs.nodes[ref_id])

    events: list[TimelineEventV2] = [
        TimelineEventV2(
            event_id=f"thread:{thread.id}",
            kind="thread_started",
            occurred_at=_utc(thread.created_at),
            title=(
                "You started this thread"
                if getattr(thread, "created_by", "user") == "user"
                else "WellBe started this thread from what you added"
            ),
            actor="you" if getattr(thread, "created_by", "user") == "user" else "wellbe",
        )
    ]

    for t in sorted(inputs.transitions, key=lambda t: t.transition_seq):
        events.append(
            TimelineEventV2(
                event_id=f"transition:{t.id}",
                kind="status_changed",
                occurred_at=_utc(t.created_at),
                title="Status changed",
                from_status=str(t.from_status),
                to_status=str(t.to_status),
                actor="you" if t.actor_type == "user" else "wellbe",
            )
        )

    picked: dict[uuid.UUID, list[str]] = {}
    for fact in inputs.facts.values():
        label = str(fact.entity_label).strip()
        names = picked.setdefault(fact.raw_context_event_id, [])
        if label and label.casefold() not in {n.casefold() for n in names}:
            names.append(label)
    for event in inputs.captures.values():
        names = picked.get(event.id, [])
        events.append(
            TimelineEventV2(
                event_id=f"capture:{event.id}",
                kind="capture",
                occurred_at=_utc(event.captured_at),
                title=_capture_title(event, sources[str(event.id)].display_label),
                detail=f"Picked out: {', '.join(names)}" if names else None,
                actor="you",
                source_ref_ids=[str(event.id)],
            )
        )

    for p in inputs.pending:
        events.append(
            TimelineEventV2(
                event_id=f"pending:{p.pending_item_id}",
                kind="open_loop",
                occurred_at=_utc(p.created_at),
                title=str(p.title),
                item_type=str(p.item_type),
                item_status=str(p.status),
                due_at=_utc(p.due_at) if p.due_at else None,
            )
        )

    events.sort(key=lambda e: e.occurred_at)
    return ThreadTimelineV2(
        thread_id=str(thread.id),
        status=str(thread.status),
        status_history=status_history(thread, inputs.transitions),
        events=events,
        sources=list(sources.values()),
    )


async def load_timeline_inputs(
    session: AsyncSession, *, patient_id: uuid.UUID, thread: Any
) -> TimelineInputs:
    """Load every stored row the timeline is built from, scoped to the patient."""
    thread_id: uuid.UUID = thread.id

    transitions = (
        await session.execute(
            select(ThreadStateTransitionRow).where(ThreadStateTransitionRow.thread_id == thread_id)
        )
    ).scalars().all()

    ref_rows = (
        await session.execute(
            select(MemorySourceRefRow.source_ref_type, MemorySourceRefRow.source_ref_id)
            .join(
                MemoryEntryRow,
                MemoryEntryRow.memory_entry_id == MemorySourceRefRow.memory_entry_id,
            )
            .where(
                MemoryEntryRow.patient_id == patient_id,
                MemoryEntryRow.thread_id == thread_id,
            )
        )
    ).all()
    memory_refs = [(str(t), rid) for t, rid in ref_rows]
    fact_ids = {rid for t, rid in memory_refs if t == "c4_extracted_fact"}
    node_ids = {rid for t, rid in memory_refs if t == "c6_kg_node"}

    facts: dict[uuid.UUID, Any] = {}
    if fact_ids:
        rows = (
            await session.execute(
                select(ExtractedFactRow).where(
                    ExtractedFactRow.patient_id == patient_id,
                    ExtractedFactRow.id.in_(fact_ids),
                )
            )
        ).scalars().all()
        facts = {f.id: f for f in rows}

    nodes: dict[uuid.UUID, Any] = {}
    if node_ids:
        node_rows = (
            await session.execute(
                select(KgNodeRow).where(
                    KgNodeRow.patient_id == patient_id, KgNodeRow.id.in_(node_ids)
                )
            )
        ).scalars().all()
        nodes = {n.id: n for n in node_rows}

    capture_ids = {f.raw_context_event_id for f in facts.values()}
    capture_filter = RawContextEventRow.source_metadata["thread_id"].astext == str(thread_id)
    if capture_ids:
        capture_filter = or_(capture_filter, RawContextEventRow.id.in_(capture_ids))
    capture_rows = (
        await session.execute(
            select(RawContextEventRow).where(
                RawContextEventRow.patient_id == patient_id, capture_filter
            )
        )
    ).scalars().all()

    pending = (
        await session.execute(
            select(PendingItemRow).where(
                PendingItemRow.patient_id == patient_id,
                PendingItemRow.primary_thread_id == thread_id,
            )
        )
    ).scalars().all()

    return TimelineInputs(
        thread=thread,
        transitions=list(transitions),
        captures={e.id: e for e in capture_rows},
        facts=facts,
        nodes=nodes,
        pending=list(pending),
        memory_refs=memory_refs,
    )


async def _load_thread(session: AsyncSession, thread_id: uuid.UUID) -> Any:
    return await session.get(HealthThreadRow, thread_id)


@router.get("/threads/{thread_id}/timeline", response_model=ThreadTimelineV2)
async def thread_timeline(
    thread_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ThreadTimelineV2:
    await require_access(
        principal, session, action="read", resource_type="health_thread", resource_id=thread_id
    )
    thread = await _load_thread(session, thread_id)
    if thread is None or thread.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Thread not found",
            detail="No health thread with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    inputs = await load_timeline_inputs(session, patient_id=principal.patient_id, thread=thread)
    timeline = build_timeline(inputs)
    await audit_ref(
        session,
        event_type="c13.thread_timeline.read",
        principal=principal,
        summary="Health thread timeline read",
        extra={"thread_id": str(thread_id), "event_count": len(timeline.events)},
    )
    await session.commit()
    return timeline
