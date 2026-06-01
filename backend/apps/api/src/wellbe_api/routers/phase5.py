"""C13 /v2 routes for Continuity (C9), Six Memories (C8), and Corrections (C11).

These complete the MVP read surface the UI needs: open loops (pending items),
thread memory (pointers + C11-resolved overlays), and the correction ledger.
Memory never exposes displayed clinical values from C8's own payload — only
pointers and resolved overlay state.
"""

from __future__ import annotations

import uuid

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
    PendingItemV2,
)

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access

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
    proposed_payload: dict | None = None
    rationale: str | None = None


@router.get("/pending-items", response_model=list[PendingItemV2])
async def list_pending_items(
    principal: PrincipalDep, session: SessionDep
) -> list[PendingItemV2]:
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
    entries = await svc.read_thread_memory(
        patient_id=principal.patient_id, thread_id=thread_id
    )
    return [
        MemoryEntryV2(
            memory_entry_id=str(e.memory_entry_id),
            memory_type=str(e.memory_type),
            lifecycle_state=str(e.lifecycle_state),
            title=e.title,
            thread_id=str(thread_id),
            source_refs=[ref.model_dump(mode="json") for ref in e.source_refs],
            resolved_overlays=list(e.resolved_overlays),
            projection_stale=e.projection_stale,
        )
        for e in entries
    ]


@router.get("/corrections", response_model=list[CorrectionV2])
async def list_corrections(
    principal: PrincipalDep, session: SessionDep
) -> list[CorrectionV2]:
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


def _correction_to_v2(row: object, targets: list[object]) -> CorrectionV2:
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
