"""C13 /v2 routes for Continuity (C9), Six Memories (C8), and Corrections (C11).

These complete the MVP read surface the UI needs: open loops (pending items),
thread memory (pointers + C11-resolved overlays), and the correction ledger.
Memory never exposes displayed clinical values from C8's own payload — only
pointers, the original vault wording those pointers came from, and resolved
overlay state.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from wellbe_c8_memories import MemoryService
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_c11_correction import CorrectionService
from wellbe_c11_correction.repository import CorrectionRepository
from wellbe_contracts.c11_correction import (
    ActorAuthority,
    CorrectionTargetKind,
    CorrectionTargetRef,
    CorrectionType,
)
from wellbe_contracts.c13_api import (
    CorrectionTargetV2,
    CorrectionV2,
    MemoryEntryV2,
    MemorySourceTextV2,
    PendingItemV2,
)

from wellbe_api.config import ApiSettings
from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.records.memory_sources import source_texts_for_facts

logger = logging.getLogger("wellbe.api.phase5")

router = APIRouter(prefix="/v2", tags=["v2-continuity-memory-correction"])


class CorrectionTargetRequest(BaseModel):
    target_kind: CorrectionTargetKind
    target_id: uuid.UUID
    field_path: str | None = None
    semantic_rank: int = 50
    target_version: str | None = None
    base_value_hash: str | None = None
    proposed_value_hash: str | None = None


class RequestCorrectionRequest(BaseModel):
    correction_type: CorrectionType
    target: CorrectionTargetRequest
    raw_correction_event_id: uuid.UUID
    proposed_payload: dict[str, Any] | None = None
    rationale: str | None = None


@router.get("/pending-items", response_model=list[PendingItemV2])
async def list_pending_items(principal: PrincipalDep, session: SessionDep) -> list[PendingItemV2]:
    await require_access(principal, session, action="read", resource_type="pending_item")
    repo = ContinuityRepository(session)
    rows = await repo.list_for_patient(principal.patient_id)
    return [
        PendingItemV2(
            pending_item_id=str(r.pending_item_id),
            primary_thread_id=str(r.primary_thread_id),
            item_type=r.item_type,
            status=r.status,
            title=r.title,
            next_action_code=r.next_action_code,
            due_at=r.due_at,
            due_precision=r.due_precision,
            investigation_ids=[str(i) for i in (r.investigation_ids or [])],
            blocks_closure=r.blocks_c9_closure_request,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/threads/{thread_id}/memories", response_model=list[MemoryEntryV2])
async def thread_memories(
    thread_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[MemoryEntryV2]:
    await require_access(
        principal, session, action="read", resource_type="memory", resource_id=thread_id
    )
    svc = MemoryService(session)
    entries = await svc.read_thread_memory(patient_id=principal.patient_id, thread_id=thread_id)
    built = [
        MemoryEntryV2(
            memory_entry_id=str(e.memory_entry_id),
            memory_type=str(e.memory_type),
            lifecycle_state=str(e.lifecycle_state),
            title=e.title or "",
            thread_id=str(thread_id),
            source_refs=[ref.model_dump(mode="json") for ref in e.source_refs],
            resolved_overlays=list(e.resolved_overlays),
            projection_stale=e.projection_stale,
            created_at=e.created_at,
            authorship_mode=str(e.authorship_mode) if e.authorship_mode else None,
        )
        for e in entries
    ]
    await _attach_source_texts(session, principal.patient_id, built)
    return dedupe_memories(built)


def _fact_ids(entries: list[MemoryEntryV2]) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for entry in entries:
        for ref in entry.source_refs:
            if ref.get("source_ref_type") != "c4_extracted_fact":
                continue
            raw = ref.get("source_ref_id")
            try:
                ids.append(uuid.UUID(str(raw)))
            except (TypeError, ValueError):
                continue
    return ids


async def _attach_source_texts(
    session: Any, patient_id: uuid.UUID, entries: list[MemoryEntryV2]
) -> None:
    """Fill ``source_texts`` from the vault. Sessions without ``execute`` skip this.

    A vault or SQL failure is logged and the memories are still returned.
    """
    if not hasattr(session, "execute"):
        return
    fact_ids = _fact_ids(entries)
    if not fact_ids:
        return
    settings = ApiSettings()
    base = settings.vault_writer_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:

            async def fetch_text(event_id: uuid.UUID) -> bytes | None:
                try:
                    resp = await client.get(f"{base}/vault/events/{event_id}/content")
                    resp.raise_for_status()
                    return resp.content
                except Exception:
                    logger.warning("vault content unavailable for %s", event_id, exc_info=True)
                    return None

            texts = await source_texts_for_facts(
                session,
                patient_id=patient_id,
                fact_ids=fact_ids,
                fetch_text=fetch_text,
            )
    except Exception:
        logger.warning("memory source text lookup failed", exc_info=True)
        return
    by_id = {item.source_ref_id: item for item in texts}
    for entry in entries:
        attached: list[MemorySourceTextV2] = []
        for ref in entry.source_refs:
            if ref.get("source_ref_type") != "c4_extracted_fact":
                continue
            item = by_id.get(str(ref.get("source_ref_id")))
            if item is not None:
                attached.append(item)
        entry.source_texts = attached


def _ref_key(ref: dict[str, Any]) -> tuple[Any, ...]:
    return (ref.get("source_ref_type"), ref.get("source_ref_id"), ref.get("field_path"))


def dedupe_memories(entries: list[MemoryEntryV2]) -> list[MemoryEntryV2]:
    """Collapse same-type, same-title memories into one row, newest first.

    Thread linkage keeps one pointer memory per extracted fact, so the same
    concept mentioned in several captures ("pain", "pain") reads as duplicates.
    The newest entry is kept and the others' source refs and overlays are merged
    into it, so no provenance is lost. Untitled entries are never merged, and
    entries with different authorship never merge: the user's own words must not
    fold into a WellBe summary (story-memory-display-lanes.md).
    """
    oldest = datetime.min.replace(tzinfo=UTC)

    def when(m: MemoryEntryV2) -> datetime:
        ts = m.created_at
        if ts is None:
            return oldest
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)

    kept: dict[tuple[str, str | None, str], MemoryEntryV2] = {}
    out: list[MemoryEntryV2] = []
    for m in sorted(entries, key=when, reverse=True):
        title = m.title.strip().casefold()
        if not title:
            out.append(m)
            continue
        group = (m.memory_type, m.authorship_mode, title)
        head = kept.get(group)
        if head is None:
            head = m.model_copy(deep=True)
            kept[group] = head
            out.append(head)
            continue
        refs = {_ref_key(r) for r in head.source_refs}
        head.source_refs += [r for r in m.source_refs if _ref_key(r) not in refs]
        seen_text = {t.source_ref_id for t in head.source_texts}
        head.source_texts += [t for t in m.source_texts if t.source_ref_id not in seen_text]
        overlays = head.resolved_overlays
        head.resolved_overlays += [o for o in m.resolved_overlays if o not in overlays]
        head.projection_stale = head.projection_stale or m.projection_stale
    return out


@router.get("/corrections", response_model=list[CorrectionV2])
async def list_corrections(principal: PrincipalDep, session: SessionDep) -> list[CorrectionV2]:
    await require_access(principal, session, action="read", resource_type="correction")
    repo = CorrectionRepository(session)
    rows = await repo.list_for_patient(principal.patient_id)
    out: list[CorrectionV2] = []
    for r in rows:
        targets = await repo.targets_for(r.correction_id)
        out.append(_correction_to_v2(r, targets))
    return out


@router.post("/corrections", response_model=CorrectionV2, status_code=201)
async def request_correction(
    body: RequestCorrectionRequest, principal: PrincipalDep, session: SessionDep
) -> CorrectionV2:
    await require_access(principal, session, action="write", resource_type="correction")
    svc = CorrectionService(session)
    result = await svc.request_correction(
        patient_id=principal.patient_id,
        correction_type=body.correction_type,
        target=CorrectionTargetRef(
            target_kind=body.target.target_kind,
            target_id=body.target.target_id,
            field_path=body.target.field_path,
            semantic_rank=body.target.semantic_rank,
            target_version=body.target.target_version,
            base_value_hash=body.target.base_value_hash,
            proposed_value_hash=body.target.proposed_value_hash,
        ),
        raw_correction_event_id=body.raw_correction_event_id,
        actor_ref={"actor_id": str(principal.actor_id)},
        actor_authority=ActorAuthority.CONTROLLER,
        proposed_payload=body.proposed_payload,
        rationale=body.rationale,
        correlation_id=principal.correlation_id,
        trace_id=principal.trace_id,
    )
    await audit_ref(
        session,
        event_type="c13.correction.requested",
        principal=principal,
        summary="Correction requested",
        extra={"correction_id": str(result.correction_id)},
    )
    await session.commit()
    repo = CorrectionRepository(session)
    row = await repo.get(result.correction_id)
    assert row is not None
    targets = await repo.targets_for(result.correction_id)
    return _correction_to_v2(row, targets)


def _correction_to_v2(row: object, targets: Sequence[object]) -> CorrectionV2:
    return CorrectionV2(
        correction_id=str(row.correction_id),  # type: ignore[attr-defined]
        status=row.status,  # type: ignore[attr-defined]
        correction_type=row.correction_type,  # type: ignore[attr-defined]
        actor_authority=row.actor_authority,  # type: ignore[attr-defined]
        rationale=row.rationale,  # type: ignore[attr-defined]
        targets=[
            CorrectionTargetV2(
                target_kind=t.target_kind,  # type: ignore[attr-defined]
                target_id=str(t.target_id),  # type: ignore[attr-defined]
                field_path=t.field_path,  # type: ignore[attr-defined]
                semantic_rank=t.semantic_rank,  # type: ignore[attr-defined]
            )
            for t in targets
        ],
        applied_at=row.applied_at,  # type: ignore[attr-defined]
        effective_at=row.effective_at,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
    )
