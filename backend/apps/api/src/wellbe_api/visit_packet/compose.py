"""Deterministic two-layer Visit Packet composer (WEL-30 / WEL-68).

Per docs/decisions/visit-packet-composition-gating.md the packet has:

- a **patient-prep** layer — the user's own questions/goals/observations,
  classified ``patient_reported`` and sourced to the user's own entry; and
- an optional **summary** layer — assembled *deterministically* from the user's
  existing structured data (C7 threads + C9 pending items). Because the MVP does
  not free-text generate, every summary statement is a ``direct_source_fact``
  linked to the object it summarizes, so there are no orphan claims and no new
  AI-generated diagnosis.

Absence is explicit: when a selected scope yields no data, the composer emits a
visible "known absence" statement rather than silently omitting it.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_contracts.visit_packet import (
    AbsenceReason,
    PacketLayer,
    PacketSection,
    StatementClassification,
)

from wellbe_api.visit_packet.models import StatementRow

_CLOSED_STATUSES = {"closed", "archived"}


def _ref(ref_type: str, source_id: str, label: str) -> dict[str, Any]:
    return {"ref_type": ref_type, "source_id": source_id, "label": label}


async def compose_statements(
    *,
    session: AsyncSession,
    packet_id: uuid.UUID,
    patient_id: uuid.UUID,
    thread_ids: list[uuid.UUID],
    include_summary: bool,
    prep_questions: list[str],
    prep_goals: list[str],
    prep_observations: list[str],
) -> list[StatementRow]:
    """Build the ordered statement rows for a packet. Pure assembly, no I/O writes."""
    rows: list[StatementRow] = []
    ordinal = 0

    def add(
        *,
        layer: PacketLayer,
        section: PacketSection,
        text: str,
        classification: StatementClassification,
        source_refs: list[dict[str, Any]],
        absent: bool = False,
        absence_reason: AbsenceReason | None = None,
    ) -> None:
        nonlocal ordinal
        rows.append(
            StatementRow(
                packet_id=packet_id,
                patient_id=patient_id,
                layer=layer.value,
                section=section.value,
                ordinal=ordinal,
                text=text,
                classification=classification.value,
                source_refs=source_refs,
                absent=absent,
                absence_reason=absence_reason.value if absence_reason else None,
                included=True,
            )
        )
        ordinal += 1

    # ---- Patient-prep layer (the user's own words) --------------------------
    for q in (s.strip() for s in prep_questions):
        if q:
            add(
                layer=PacketLayer.PATIENT_PREP,
                section=PacketSection.QUESTION,
                text=q,
                classification=StatementClassification.PATIENT_REPORTED,
                source_refs=[_ref("patient_entered", str(packet_id), "Your question")],
            )
    for g in (s.strip() for s in prep_goals):
        if g:
            add(
                layer=PacketLayer.PATIENT_PREP,
                section=PacketSection.GOAL,
                text=g,
                classification=StatementClassification.PATIENT_REPORTED,
                source_refs=[_ref("patient_entered", str(packet_id), "Your goal")],
            )
    for o in (s.strip() for s in prep_observations):
        if o:
            add(
                layer=PacketLayer.PATIENT_PREP,
                section=PacketSection.OBSERVATION,
                text=o,
                classification=StatementClassification.PATIENT_REPORTED,
                source_refs=[_ref("patient_entered", str(packet_id), "Your observation")],
            )

    if not include_summary:
        return rows

    # ---- Summary layer (deterministic, source-linked) -----------------------
    thread_repo = ThreadRepository(session)
    continuity_repo = ContinuityRepository(session)

    threads = []
    if thread_ids:
        for tid in thread_ids:
            row = await thread_repo.get(tid)
            if row is not None and row.patient_id == patient_id:
                threads.append(row)
    else:
        threads = [t for t in await thread_repo.list_for_patient(patient_id)]

    open_threads = [t for t in threads if t.status not in _CLOSED_STATUSES]

    if not open_threads:
        add(
            layer=PacketLayer.SUMMARY,
            section=PacketSection.CONCERN,
            text="No active health concerns are on record for the selected scope.",
            classification=StatementClassification.DIRECT_SOURCE_FACT,
            source_refs=[_ref("record_scan", str(patient_id), "Your records")],
            absent=True,
            absence_reason=AbsenceReason.KNOWN_ABSENT,
        )

    any_pending = False
    for t in open_threads:
        add(
            layer=PacketLayer.SUMMARY,
            section=PacketSection.CONCERN,
            text=f"{t.title} (current status: {str(t.status).replace('_', ' ')}).",
            classification=StatementClassification.DIRECT_SOURCE_FACT,
            source_refs=[_ref("health_thread", str(t.id), t.title)],
        )
        pendings = await continuity_repo.items_for_thread(patient_id=patient_id, thread_id=t.id)
        for p in pendings:
            if p.status in {"resolved", "cancelled", "superseded"}:
                continue
            any_pending = True
            add(
                layer=PacketLayer.SUMMARY,
                section=PacketSection.PENDING,
                text=f"Open item: {p.title} (status: {str(p.status).replace('_', ' ')}).",
                classification=StatementClassification.DIRECT_SOURCE_FACT,
                source_refs=[_ref("pending_item", str(p.pending_item_id), p.title)],
            )

    if open_threads and not any_pending:
        add(
            layer=PacketLayer.SUMMARY,
            section=PacketSection.PENDING,
            text="No open follow-up items are tracked for these concerns.",
            classification=StatementClassification.DIRECT_SOURCE_FACT,
            source_refs=[_ref("record_scan", str(patient_id), "Your records")],
            absent=True,
            absence_reason=AbsenceReason.KNOWN_ABSENT,
        )

    return rows
