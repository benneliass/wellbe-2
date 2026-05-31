from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_contracts.c5_evidence import (
    EVIDENCE_LINKED,
    PROVENANCE_ORPHAN_REJECTED,
    ConfidenceBasis,
    EvidenceLinkedPayload,
    EvidenceLinkType,
    EvidenceRef,
    EvidenceSourceType,
    ProvenanceOrphanRejectedPayload,
)
from wellbe_events import emit_event

from wellbe_c5_evidence.repository import EvidenceRepository


class NoEvidenceRefsError(Exception):
    """Raised when a derived object write is attempted with no evidence refs."""
    pass


class MissingRawEventError(Exception):
    """Raised when evidence refs reference raw_context_event_ids not in vault."""

    def __init__(self, missing_ids: list[uuid.UUID]) -> None:
        self.missing_ids = missing_ids
        super().__init__(f"Missing raw_context_event_ids: {missing_ids}")


class EvidenceService:
    """C5 write gate: ensures every derived fact has provenance before persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EvidenceRepository(session)

    async def link_fact(
        self,
        *,
        fact_id: uuid.UUID,
        patient_id: uuid.UUID,
        evidence_refs: list[EvidenceRef],
        correlation_id: str,
        trace_id: str,
    ) -> list[uuid.UUID]:
        """Create evidence links for an extracted fact.

        Validates that:
        1. At least one evidence ref is provided (no orphan claims at application level)
        2. All raw_context_event_ids actually exist in vault

        The Postgres deferred constraint trigger provides a second enforcement layer.
        """
        if not evidence_refs:
            await self._emit_orphan_rejected(
                source_type=EvidenceSourceType.EXTRACTED_FACT,
                source_id=fact_id,
                patient_id=patient_id,
                missing_ids=[],
                reason="No evidence refs provided",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            raise NoEvidenceRefsError(
                f"Fact {fact_id} cannot be written without evidence refs"
            )

        missing = await self._check_raw_events_exist(
            [ref.raw_context_event_id for ref in evidence_refs]
        )
        if missing:
            await self._emit_orphan_rejected(
                source_type=EvidenceSourceType.EXTRACTED_FACT,
                source_id=fact_id,
                patient_id=patient_id,
                missing_ids=missing,
                reason="Referenced raw_context_event_ids do not exist in vault",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            raise MissingRawEventError(missing)

        link_ids: list[uuid.UUID] = []
        for ref in evidence_refs:
            link_id = uuid.uuid4()
            await self._repo.insert_link(
                id=link_id,
                source_type=EvidenceSourceType.EXTRACTED_FACT.value,
                source_id=fact_id,
                raw_context_event_id=ref.raw_context_event_id,
                patient_id=patient_id,
                link_type=ref.link_type.value,
                confidence=ref.confidence,
                confidence_basis=ref.confidence_basis.value,
                linked_by="pipeline",
                relevance_span_start=ref.relevance_span_start,
                relevance_span_end=ref.relevance_span_end,
            )
            link_ids.append(link_id)

            payload = EvidenceLinkedPayload(
                evidence_link_id=link_id,
                source_type=EvidenceSourceType.EXTRACTED_FACT,
                source_id=fact_id,
                raw_context_event_id=ref.raw_context_event_id,
                patient_id=patient_id,
                link_type=ref.link_type,
                confidence=ref.confidence,
                confidence_basis=ref.confidence_basis,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            await emit_event(
                session=self._session,
                event_type=EVIDENCE_LINKED,
                payload=payload.model_dump(mode="json"),
                correlation_id=correlation_id,
                trace_id=trace_id,
            )

        return link_ids

    async def link_signal(
        self,
        *,
        signal_id: uuid.UUID,
        patient_id: uuid.UUID,
        evidence_refs: list[EvidenceRef],
        correlation_id: str,
        trace_id: str,
    ) -> list[uuid.UUID]:
        """Create evidence links for a health signal (one per raw event)."""
        if not evidence_refs:
            await self._emit_orphan_rejected(
                source_type=EvidenceSourceType.HEALTH_SIGNAL,
                source_id=signal_id,
                patient_id=patient_id,
                missing_ids=[],
                reason="No evidence refs provided",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            raise NoEvidenceRefsError(
                f"Signal {signal_id} cannot be written without evidence refs"
            )

        missing = await self._check_raw_events_exist(
            [ref.raw_context_event_id for ref in evidence_refs]
        )
        if missing:
            await self._emit_orphan_rejected(
                source_type=EvidenceSourceType.HEALTH_SIGNAL,
                source_id=signal_id,
                patient_id=patient_id,
                missing_ids=missing,
                reason="Referenced raw_context_event_ids do not exist in vault",
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            raise MissingRawEventError(missing)

        link_ids: list[uuid.UUID] = []
        for ref in evidence_refs:
            link_id = uuid.uuid4()
            await self._repo.insert_link(
                id=link_id,
                source_type=EvidenceSourceType.HEALTH_SIGNAL.value,
                source_id=signal_id,
                raw_context_event_id=ref.raw_context_event_id,
                patient_id=patient_id,
                link_type=ref.link_type.value,
                confidence=ref.confidence,
                confidence_basis=ref.confidence_basis.value,
                linked_by="pipeline",
                relevance_span_start=ref.relevance_span_start,
                relevance_span_end=ref.relevance_span_end,
            )
            link_ids.append(link_id)

            payload = EvidenceLinkedPayload(
                evidence_link_id=link_id,
                source_type=EvidenceSourceType.HEALTH_SIGNAL,
                source_id=signal_id,
                raw_context_event_id=ref.raw_context_event_id,
                patient_id=patient_id,
                link_type=ref.link_type,
                confidence=ref.confidence,
                confidence_basis=ref.confidence_basis,
                correlation_id=correlation_id,
                trace_id=trace_id,
            )
            await emit_event(
                session=self._session,
                event_type=EVIDENCE_LINKED,
                payload=payload.model_dump(mode="json"),
                correlation_id=correlation_id,
                trace_id=trace_id,
            )

        return link_ids

    async def _check_raw_events_exist(
        self, event_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        """Check which event IDs don't exist in vault. Returns missing ones."""
        from wellbe_c2_vault.models import RawContextEventRow

        stmt = select(RawContextEventRow.id).where(
            RawContextEventRow.id.in_(event_ids)
        )
        result = await self._session.execute(stmt)
        existing = {row[0] for row in result}
        return [eid for eid in event_ids if eid not in existing]

    async def _emit_orphan_rejected(
        self,
        *,
        source_type: EvidenceSourceType,
        source_id: uuid.UUID,
        patient_id: uuid.UUID,
        missing_ids: list[uuid.UUID],
        reason: str,
        correlation_id: str,
        trace_id: str,
    ) -> None:
        payload = ProvenanceOrphanRejectedPayload(
            source_type=source_type,
            source_id=source_id,
            patient_id=patient_id,
            missing_raw_context_event_ids=missing_ids,
            rejection_reason=reason,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        await emit_event(
            session=self._session,
            event_type=PROVENANCE_ORPHAN_REJECTED,
            payload=payload.model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
