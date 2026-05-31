from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c5_evidence.models import EvidenceLinkRow


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_link(
        self,
        *,
        id: uuid.UUID,
        source_type: str,
        source_id: uuid.UUID,
        raw_context_event_id: uuid.UUID,
        patient_id: uuid.UUID,
        link_type: str,
        confidence: float,
        confidence_basis: str,
        linked_by: str = "pipeline",
        relevance_span_start: int | None = None,
        relevance_span_end: int | None = None,
        correction_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        """Idempotently insert an evidence link.

        Uniqueness is enforced on (source_type, source_id, raw_context_event_id,
        link_type) by the ``uq_evidence_link_dedup`` constraint. On a re-delivery
        of the same logical link the insert is a no-op and ``None`` is returned, so
        callers can avoid re-emitting an ``evidence.linked`` event for a duplicate.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            pg_insert(EvidenceLinkRow)
            .values(
                id=id,
                source_type=source_type,
                source_id=source_id,
                raw_context_event_id=raw_context_event_id,
                patient_id=patient_id,
                link_type=link_type,
                confidence=confidence,
                confidence_basis=confidence_basis,
                relevance_span_start=relevance_span_start,
                relevance_span_end=relevance_span_end,
                linked_at=now,
                linked_by=linked_by,
                correction_id=correction_id,
                schema_version=1,
                created_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_evidence_link_dedup")
            .returning(EvidenceLinkRow.id)
        )
        result = await self._session.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        await self._session.flush()
        return inserted_id

    async def links_for_source(
        self, source_type: str, source_id: uuid.UUID
    ) -> list[EvidenceLinkRow]:
        stmt = select(EvidenceLinkRow).where(
            EvidenceLinkRow.source_type == source_type,
            EvidenceLinkRow.source_id == source_id,
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
