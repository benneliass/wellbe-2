"""What-changed delta digest engine (WEL-56).

Per docs/decisions/delta-semantics-window.md, this composes a calm, typed,
source-linked change-event stream from the user's own persisted state:

- **Open-loop continuity changes (C9)** rank first — pending items the user is
  waiting on that were created, updated, resolved, or cancelled in the window.
- **Lifecycle/status changes (C7)** rank second — thread state transitions.
- **New facts** rank last — newly started threads.

Ranking is never abnormality-first; copy says "changed"/"new", never "worse".
Each event carries a plain-language ranking reason and a source cue.

Deferred (tracked): C4 value-delta comparators (range-crossing, change-from-
prior, personal baseline, RCV), patient-reported change, critical-result routing
to C9 next-steps, and per-user "since you last looked" read-state persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c7_thread.models import HealthThreadRow, ThreadStateTransitionRow
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c9_continuity.models import PendingItemRow
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_contracts.delta import DeltaCategory, DeltaEventV2, DeltaSourceRef

_DEFAULT_WINDOW_DAYS = 14
_CLOSED_PENDING = {"resolved", "cancelled", "superseded"}

_CATEGORY_RANK = {
    DeltaCategory.OPEN_LOOP: 2,
    DeltaCategory.LIFECYCLE: 1,
    DeltaCategory.NEW_FACT: 0,
}


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass
class DeltaResult:
    events: list[DeltaEventV2] = field(default_factory=list)
    window_since: datetime | None = None
    window_label: str = ""
    note: str = ""


def _pending_event(item: PendingItemRow, since: datetime) -> DeltaEventV2:
    created = _as_utc(item.created_at)
    updated = _as_utc(item.updated_at)
    status = str(item.status)
    label = item.title

    if created >= since:
        reason = "New open item"
        detail = "A new item to follow up on."
        occurred = created
    elif status in _CLOSED_PENDING:
        reason = "Item closed" if status != "resolved" else "Item resolved"
        detail = f"Now: {_humanize(status)}."
        occurred = _as_utc(item.resolved_at or item.cancelled_at or item.updated_at)
    else:
        reason = "Open item changed"
        detail = f"Now: {_humanize(status)}."
        occurred = updated

    return DeltaEventV2(
        id=f"pending:{item.pending_item_id}",
        category=DeltaCategory.OPEN_LOOP,
        title=label,
        ranking_reason=reason,
        detail=detail,
        occurred_at=occurred,
        source=DeltaSourceRef(
            ref_type="pending_item",
            source_id=str(item.pending_item_id),
            label=label,
        ),
    )


def _transition_event(
    transition: ThreadStateTransitionRow, thread_title: str
) -> DeltaEventV2:
    return DeltaEventV2(
        id=f"transition:{transition.id}",
        category=DeltaCategory.LIFECYCLE,
        title=thread_title,
        ranking_reason="Status changed",
        detail=f"Now: {_humanize(transition.to_status)}.",
        occurred_at=_as_utc(transition.created_at),
        source=DeltaSourceRef(
            ref_type="health_thread",
            source_id=str(transition.thread_id),
            label=thread_title,
        ),
    )


def _new_thread_event(thread: HealthThreadRow) -> DeltaEventV2:
    return DeltaEventV2(
        id=f"thread:{thread.id}",
        category=DeltaCategory.NEW_FACT,
        title=thread.title,
        ranking_reason="New thread",
        detail="A new health thread you started.",
        occurred_at=_as_utc(thread.created_at),
        source=DeltaSourceRef(
            ref_type="health_thread", source_id=str(thread.id), label=thread.title
        ),
    )


def _sort_key(e: DeltaEventV2) -> tuple[Any, ...]:
    return (_CATEGORY_RANK[e.category], _as_utc(e.occurred_at).timestamp())


async def build_digest(
    *,
    session: AsyncSession,
    patient_id: uuid.UUID,
    since: datetime | None,
    limit: int = 50,
) -> DeltaResult:
    now = datetime.now(UTC)
    if since is None:
        since = now - timedelta(days=_DEFAULT_WINDOW_DAYS)
        window_label = f"the last {_DEFAULT_WINDOW_DAYS} days"
    else:
        since = _as_utc(since)
        window_label = f"since {since.date().isoformat()}"

    continuity = ContinuityRepository(session)
    threads = ThreadRepository(session)

    events: list[DeltaEventV2] = []

    for item in await continuity.changed_since_for_patient(
        patient_id, since=since, limit=limit
    ):
        events.append(_pending_event(item, since))

    for transition, title in await threads.transitions_since_for_patient(
        patient_id, since=since, limit=limit
    ):
        events.append(_transition_event(transition, title))

    for thread in await threads.list_for_patient(patient_id, limit=limit):
        if _as_utc(thread.created_at) >= since:
            events.append(_new_thread_event(thread))

    events.sort(key=_sort_key, reverse=True)
    events = events[:limit]

    if not events:
        note = (
            f"Nothing changed in {window_label}. When new results, notes, or "
            "updates arrive on your threads, they'll show up here — calmly, "
            "source-linked, and never as a diagnosis."
        )
    else:
        note = (
            f"What changed in {window_label}, calmest-to-act-on first. "
            "Each item links back to its source and is never a diagnosis."
        )

    return DeltaResult(
        events=events, window_since=since, window_label=window_label, note=note
    )
