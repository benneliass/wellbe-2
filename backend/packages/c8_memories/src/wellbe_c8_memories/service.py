from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c5_evidence.repository import EvidenceRepository
from wellbe_c11_correction.service import CorrectionService
from wellbe_contracts.c8_memory import (
    C8_MEMORY_CONFIRMED,
    C8_MEMORY_CREATED,
    C8_MEMORY_VISIBLE,
    DEFAULT_AUTHORSHIP,
    DERIVED_MEMORY_TYPES,
    AuthorshipMode,
    MemoryLifecycleState,
    MemorySourceRef,
    MemoryType,
    ResolvedMemoryEntry,
    SourceRefType,
)
from wellbe_contracts.c11_correction import CorrectionTargetKind
from wellbe_events import emit_event

from wellbe_c8_memories.errors import MemoryNotFoundError, VisibleWithoutEvidenceError
from wellbe_c8_memories.repository import MemoryRepository

# Source-ref kinds that participate in correction resolution at read time, mapped
# to the C11 target kind. (Pointers C8 holds that the C11 resolver understands.)
_CORRECTABLE: dict[SourceRefType, CorrectionTargetKind] = {
    SourceRefType.C4_EXTRACTED_FACT: CorrectionTargetKind.C4_EXTRACTED_FACT,
    SourceRefType.C6_KG_NODE: CorrectionTargetKind.C6_KG_NODE,
    SourceRefType.C6_KG_EDGE: CorrectionTargetKind.C6_KG_EDGE,
    SourceRefType.C9_PENDING_ITEM: CorrectionTargetKind.C9_PENDING_ITEM,
    SourceRefType.C15_THEORY: CorrectionTargetKind.C15_THEORY,
}


class MemoryService:
    """C8 Six Memories hybrid store.

    Stores user-authored entries and rebuildable derived POINTER projections. A
    visible derived entry must carry C5 provenance (written through C5). Displayed
    values are resolved at read time through the shared C11 resolver — C8 never
    implements its own correction precedence and never copies clinical facts.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MemoryRepository(session)
        self._evidence = EvidenceRepository(session)
        self._corrections = CorrectionService(session)

    async def create_entry(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        memory_type: MemoryType,
        source_refs: list[MemorySourceRef],
        created_by_actor: dict,
        title: str | None = None,
        payload: dict | None = None,
        authorship_mode: AuthorshipMode | None = None,
        make_visible: bool = False,
        evidence_raw_event_ids: list[uuid.UUID] | None = None,
        c10_gate_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        correlation_id: str = "c8",
        trace_id: str = "c8",
    ):
        """Create a memory entry.

        For derived memory types (clinical/pattern), ``make_visible`` requires
        ``evidence_raw_event_ids`` so a C5 evidence link can be created (no orphan
        derived claims). Authored types (story/equity) may be visible from their own
        words / controller confirmation.
        """
        memory_entry_id = uuid.uuid4()
        idem = idempotency_key or f"c8:{memory_entry_id}"
        authorship = authorship_mode or DEFAULT_AUTHORSHIP[memory_type]

        # Always create as draft first; promote to visible only after the gate.
        row = await self._repo.insert_entry(
            memory_entry_id=memory_entry_id,
            patient_id=patient_id,
            thread_id=thread_id,
            memory_type=memory_type,
            authorship_mode=authorship,
            lifecycle_state=MemoryLifecycleState.DRAFT,
            idempotency_key=idem,
            title=title,
            payload=payload or {},
            created_by_actor=created_by_actor,
            c10_gate_id=c10_gate_id,
        )
        for ref in source_refs:
            await self._repo.insert_source_ref(
                memory_entry_id=memory_entry_id, patient_id=patient_id, ref=ref
            )

        await emit_event(
            session=self._session,
            event_type=C8_MEMORY_CREATED,
            payload={
                "memory_entry_id": str(memory_entry_id),
                "patient_id": str(patient_id),
                "thread_id": str(thread_id),
                "memory_type": memory_type.value,
                "authorship_mode": authorship.value,
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        if make_visible:
            await self._make_visible(
                row=row,
                memory_type=memory_type,
                patient_id=patient_id,
                evidence_raw_event_ids=evidence_raw_event_ids or [],
                correlation_id=correlation_id,
                trace_id=trace_id,
            )

        return row

    async def _make_visible(
        self,
        *,
        row,
        memory_type: MemoryType,
        patient_id: uuid.UUID,
        evidence_raw_event_ids: list[uuid.UUID],
        correlation_id: str,
        trace_id: str,
    ) -> None:
        # Derived entries (clinical/pattern) need C5 provenance before visible.
        if memory_type in DERIVED_MEMORY_TYPES:
            if not evidence_raw_event_ids:
                raise VisibleWithoutEvidenceError(row.memory_entry_id)
            for raw_event_id in evidence_raw_event_ids:
                await self._evidence.insert_link(
                    id=uuid.uuid4(),
                    source_type="memory_entry",
                    source_id=row.memory_entry_id,
                    raw_context_event_id=raw_event_id,
                    patient_id=patient_id,
                    link_type="primary",
                    confidence=1.0,
                    confidence_basis="system_computed",
                    linked_by="pipeline",
                )

        await self._repo.set_lifecycle(row=row, state=MemoryLifecycleState.VISIBLE)
        await emit_event(
            session=self._session,
            event_type=C8_MEMORY_VISIBLE,
            payload={
                "memory_entry_id": str(row.memory_entry_id),
                "patient_id": str(patient_id),
                "memory_type": memory_type.value,
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    async def confirm_entry(
        self,
        *,
        memory_entry_id: uuid.UUID,
        controller_actor: dict,
        correlation_id: str = "c8",
        trace_id: str = "c8",
    ):
        """Controller confirms a pending (e.g. derived Equity) entry -> visible."""
        row = await self._repo.get(memory_entry_id)
        if row is None:
            raise MemoryNotFoundError(memory_entry_id)
        row.authorship_mode = AuthorshipMode.CONTROLLER_CONFIRMED.value
        row.accepted_by_controller_actor = controller_actor
        await self._repo.set_lifecycle(row=row, state=MemoryLifecycleState.VISIBLE)
        await emit_event(
            session=self._session,
            event_type=C8_MEMORY_CONFIRMED,
            payload={
                "memory_entry_id": str(memory_entry_id),
                "patient_id": str(row.patient_id),
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return row

    async def read_thread_memory(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        memory_type: MemoryType | None = None,
    ) -> list[ResolvedMemoryEntry]:
        """Read memory entries, resolving correctable pointers through C11.

        C8 returns pointers + the C11-resolved overlay state for each correctable
        source ref. It never reads displayed clinical values from its own payload.
        """
        entries = await self._repo.entries_for_thread(
            patient_id=patient_id, thread_id=thread_id, memory_type=memory_type
        )
        resolved: list[ResolvedMemoryEntry] = []
        for entry in entries:
            ref_rows = await self._repo.source_refs_for(entry.memory_entry_id)
            refs = [await self._repo.to_source_ref(r) for r in ref_rows]
            overlays: list[dict] = []
            stale = False
            for ref in refs:
                target_kind = _CORRECTABLE.get(ref.source_ref_type)
                if target_kind is None:
                    continue
                overlay = await self._corrections.resolve_target(
                    patient_id=patient_id,
                    target_kind=target_kind,
                    target_id=ref.source_ref_id,
                    field_path=ref.field_path,
                )
                if overlay.resolved_state != "base":
                    stale = True
                    overlays.append(overlay.model_dump(mode="json"))
            resolved.append(
                ResolvedMemoryEntry(
                    memory_entry_id=entry.memory_entry_id,
                    memory_type=MemoryType(entry.memory_type),
                    lifecycle_state=MemoryLifecycleState(entry.lifecycle_state),
                    title=entry.title,
                    source_refs=refs,
                    resolved_overlays=overlays,
                    projection_stale=stale,
                )
            )
        return resolved
