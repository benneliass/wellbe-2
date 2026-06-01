from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c5_evidence.repository import EvidenceRepository
from wellbe_contracts.c11_correction import (
    C11_CORRECTION_ACCEPTED,
    C11_CORRECTION_APPLIED,
    C11_CORRECTION_PROPOSED,
    C11_CORRECTION_REQUESTED,
    CORRECTION_APPLIED_COMPAT,
    ActorAuthority,
    CorrectionResult,
    CorrectionStatus,
    CorrectionTargetKind,
    CorrectionTargetRef,
    CorrectionType,
    ResolvedOverlay,
)
from wellbe_events import emit_event

from wellbe_c11_correction.errors import (
    CorrectionNotFoundError,
    CorrectionNotPendingError,
)
from wellbe_c11_correction.repository import CorrectionRepository
from wellbe_c11_correction.resolver import resolve_overlays

# Target kinds whose corrections get a formal C5 evidence link. Limited to the
# C5 evidence_links source_type CHECK domain; other kinds still carry C2
# provenance via raw_correction_event_id but have no evidence_links row.
_C5_SOURCE_TYPE: dict[CorrectionTargetKind, str] = {
    CorrectionTargetKind.C4_EXTRACTED_FACT: "extracted_fact",
    CorrectionTargetKind.C8_MEMORY_ENTRY: "memory_entry",
}

_CONTRADICTING_TYPES = {
    CorrectionType.MARK_INCORRECT,
    CorrectionType.REPLACE_VALUE,
    CorrectionType.WITHDRAW_FROM_CURRENT_VIEW,
    CorrectionType.CHANGE_EVIDENCE_WEIGHT,
}


def _link_type_for(correction_type: CorrectionType) -> str:
    if correction_type in _CONTRADICTING_TYPES:
        return "contradicting"
    if correction_type == CorrectionType.ADD_MISSING_CONTEXT:
        return "contextual"
    return "corroborating"


class CorrectionService:
    """C11: append-only, source-linked correction overlays written through C5.

    Never mutates correction targets. Controller-authored corrections are applied
    immediately; role/system proposals stay pending until the controller accepts.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CorrectionRepository(session)
        self._evidence = EvidenceRepository(session)

    async def request_correction(
        self,
        *,
        patient_id: uuid.UUID,
        correction_type: CorrectionType,
        target: CorrectionTargetRef,
        raw_correction_event_id: uuid.UUID,
        actor_ref: dict,
        actor_authority: ActorAuthority = ActorAuthority.CONTROLLER,
        proposed_payload: dict | None = None,
        rationale: str | None = None,
        effective_at=None,
        supersedes_correction_id: uuid.UUID | None = None,
        idempotency_key: str | None = None,
        correlation_id: str = "c11",
        trace_id: str = "c11",
    ) -> CorrectionResult:
        """Create a correction overlay.

        Controller authorities are applied immediately and participate in resolved
        reads. ``role_proposed``/``system_suggested`` stay pending until accepted.
        """
        correction_id = uuid.uuid4()
        idem = idempotency_key or f"c11:{correction_id}"
        is_proposal = actor_authority in (
            ActorAuthority.ROLE_PROPOSED,
            ActorAuthority.SYSTEM_SUGGESTED,
        )
        status = (
            CorrectionStatus.PENDING_CONTROLLER_ACCEPTANCE
            if is_proposal
            else CorrectionStatus.APPLIED
        )
        from wellbe_c11_correction.repository import _naive_utcnow

        applied_at = None if is_proposal else _naive_utcnow()

        await self._repo.insert_correction(
            correction_id=correction_id,
            patient_id=patient_id,
            status=status,
            correction_type=correction_type,
            actor_authority=actor_authority,
            actor_ref=actor_ref,
            raw_correction_event_id=raw_correction_event_id,
            proposed_payload=proposed_payload or {},
            idempotency_key=idem,
            rationale=rationale,
            effective_at=effective_at,
            applied_at=applied_at,
            supersedes_correction_id=supersedes_correction_id,
        )
        await self._repo.insert_target(
            correction_id=correction_id,
            patient_id=patient_id,
            target_kind=target.target_kind,
            target_id=target.target_id,
            field_path=target.field_path,
            semantic_rank=target.semantic_rank,
            target_version=target.target_version,
            base_value_hash=target.base_value_hash,
            proposed_value_hash=target.proposed_value_hash,
        )

        # Attach correction provenance via a C5 evidence link (write THROUGH C5).
        evidence_link_ids: list[uuid.UUID] = []
        source_type = _C5_SOURCE_TYPE.get(target.target_kind)
        if source_type is not None:
            link_id = await self._evidence.insert_link(
                id=uuid.uuid4(),
                source_type=source_type,
                source_id=target.target_id,
                raw_context_event_id=raw_correction_event_id,
                patient_id=patient_id,
                link_type=_link_type_for(correction_type),
                confidence=1.0,
                confidence_basis="correction_service",
                linked_by="correction_service",
                correction_id=correction_id,
            )
            if link_id is not None:
                evidence_link_ids.append(link_id)

        # Events
        requested_payload = {
            "correction_id": str(correction_id),
            "patient_id": str(patient_id),
            "correction_type": correction_type.value,
            "actor_authority": actor_authority.value,
            "target_kind": target.target_kind.value,
            "target_id": str(target.target_id),
            "field_path": target.field_path,
        }
        await emit_event(
            session=self._session,
            event_type=C11_CORRECTION_REQUESTED,
            payload=requested_payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        if is_proposal:
            await emit_event(
                session=self._session,
                event_type=C11_CORRECTION_PROPOSED,
                payload=requested_payload,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
        else:
            await self._emit_applied(
                correction_id=correction_id,
                patient_id=patient_id,
                target=target,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )

        return CorrectionResult(
            correction_id=correction_id,
            status=status,
            actor_authority=actor_authority,
            evidence_link_ids=evidence_link_ids,
            superseded_correction_id=supersedes_correction_id,
        )

    async def accept_proposal(
        self,
        *,
        correction_id: uuid.UUID,
        controller_actor: dict,
        correlation_id: str = "c11",
        trace_id: str = "c11",
    ) -> CorrectionResult:
        """Controller accepts a pending proposal: it becomes applied and resolves."""
        row = await self._repo.get(correction_id)
        if row is None:
            raise CorrectionNotFoundError(correction_id)
        if row.status != CorrectionStatus.PENDING_CONTROLLER_ACCEPTANCE.value:
            raise CorrectionNotPendingError(correction_id, row.status)

        await self._repo.mark_applied(
            row=row,
            actor_authority=ActorAuthority.CONTROLLER_ACCEPTED_PROPOSAL,
            accepted_by_controller_actor=controller_actor,
        )
        targets = await self._repo.targets_for(correction_id)
        await emit_event(
            session=self._session,
            event_type=C11_CORRECTION_ACCEPTED,
            payload={
                "correction_id": str(correction_id),
                "patient_id": str(row.patient_id),
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        for t in targets:
            await self._emit_applied(
                correction_id=correction_id,
                patient_id=row.patient_id,
                target=CorrectionTargetRef(
                    target_kind=CorrectionTargetKind(t.target_kind),
                    target_id=t.target_id,
                    field_path=t.field_path,
                    semantic_rank=t.semantic_rank,
                ),
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
        return CorrectionResult(
            correction_id=correction_id,
            status=CorrectionStatus.APPLIED,
            actor_authority=ActorAuthority.CONTROLLER_ACCEPTED_PROPOSAL,
        )

    async def resolve_target(
        self,
        *,
        patient_id: uuid.UUID,
        target_kind: CorrectionTargetKind,
        target_id: uuid.UUID,
        field_path: str | None = None,
    ) -> ResolvedOverlay:
        """The shared resolver entrypoint used by C6, C8, and C13."""
        candidates = await self._repo.load_candidates(
            patient_id=patient_id, target_kind=target_kind, target_id=target_id
        )
        return resolve_overlays(
            target_kind=target_kind,
            target_id=target_id,
            field_path=field_path,
            candidates=candidates,
        )

    async def _emit_applied(
        self,
        *,
        correction_id: uuid.UUID,
        patient_id: uuid.UUID,
        target: CorrectionTargetRef,
        correlation_id: str,
        trace_id: str,
    ) -> None:
        payload = {
            "correction_id": str(correction_id),
            "patient_id": str(patient_id),
            "target_kind": target.target_kind.value,
            "target_id": str(target.target_id),
            "field_path": target.field_path,
        }
        await emit_event(
            session=self._session,
            event_type=C11_CORRECTION_APPLIED,
            payload=payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        # Compatibility alias for existing C6 rescore workers.
        await emit_event(
            session=self._session,
            event_type=CORRECTION_APPLIED_COMPAT,
            payload=payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        await self._repo.insert_resolution_event(
            correction_id=correction_id,
            patient_id=patient_id,
            target_kind=target.target_kind.value,
            target_id=target.target_id,
            field_path=target.field_path,
            resolution_action="became_active",
            idempotency_key=(
                f"c11:resolve:{correction_id}:{target.target_id}:{target.field_path or ''}"
            ),
            new_active_correction_id=correction_id,
        )
