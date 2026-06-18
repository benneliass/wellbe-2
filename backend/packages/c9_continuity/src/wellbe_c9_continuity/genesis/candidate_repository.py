from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c9_continuity.genesis.models import GenesisCandidateRow


def _union(existing: list[uuid.UUID] | None, new: list[uuid.UUID]) -> list[uuid.UUID]:
    """Order-preserving union of two id lists (no duplicate provenance entries)."""
    seen: dict[uuid.UUID, None] = dict.fromkeys(existing or [])
    for item in new:
        seen.setdefault(item, None)
    return list(seen)


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
        candidate_key: str,
        concern_key: dict[str, object],
        episode_bucket: str,
        display_title: str,
        candidate_type: str,
        source_capture_ids: list[uuid.UUID],
        source_fact_ids: list[uuid.UUID],
        source_graph_entity_ids: list[uuid.UUID],
        evidence_link_ids: list[uuid.UUID],
        confidence: float | None,
        reason_code: str | None,
    ) -> tuple[GenesisCandidateRow, bool]:
        """Idempotently create-or-update a candidate keyed on ``candidate_key``.

        Returns ``(row, created)``. On a repeat mention of the same concern the
        existing candidate is updated: provenance arrays are unioned, ``seen_count``
        increments, ``last_seen_at`` advances, and ``confidence`` keeps the max. The
        status is never changed here — a dismissed/promoted candidate is not
        silently resurrected (richer re-surfacing is post-MVP).
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        insert_stmt = (
            pg_insert(GenesisCandidateRow)
            .values(
                candidate_id=candidate_id,
                user_id=user_id,
                candidate_key=candidate_key,
                concern_key=concern_key,
                episode_bucket=episode_bucket,
                display_title=display_title,
                candidate_type=candidate_type,
                source_capture_ids=source_capture_ids,
                source_fact_ids=source_fact_ids,
                source_graph_entity_ids=source_graph_entity_ids,
                evidence_link_ids=evidence_link_ids,
                status="pending",
                confidence=confidence,
                reason_code=reason_code,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_genesis_candidate_key")
            .returning(GenesisCandidateRow.candidate_id)
        )
        result = await self._session.execute(insert_stmt)
        inserted_id = result.scalar_one_or_none()
        await self._session.flush()

        if inserted_id is not None:
            row = await self.get(inserted_id)
            assert row is not None
            return row, True

        existing = await self._get_by_key_for_update(candidate_key)
        assert existing is not None  # conflict guarantees a row
        existing.source_capture_ids = _union(existing.source_capture_ids, source_capture_ids)
        existing.source_fact_ids = _union(existing.source_fact_ids, source_fact_ids)
        existing.source_graph_entity_ids = _union(
            existing.source_graph_entity_ids, source_graph_entity_ids
        )
        existing.evidence_link_ids = _union(existing.evidence_link_ids, evidence_link_ids)
        existing.seen_count = existing.seen_count + 1
        existing.last_seen_at = now
        existing.updated_at = now
        if confidence is not None:
            existing.confidence = max(existing.confidence or 0.0, confidence)
        await self._session.flush()
        return existing, False

    async def get(self, candidate_id: uuid.UUID) -> GenesisCandidateRow | None:
        stmt = select(GenesisCandidateRow).where(
            GenesisCandidateRow.candidate_id == candidate_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_key_for_update(
        self, candidate_key: str
    ) -> GenesisCandidateRow | None:
        stmt = (
            select(GenesisCandidateRow)
            .where(GenesisCandidateRow.candidate_key == candidate_key)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pending(
        self, user_id: uuid.UUID, *, limit: int = 100
    ) -> list[GenesisCandidateRow]:
        stmt = (
            select(GenesisCandidateRow)
            .where(
                GenesisCandidateRow.user_id == user_id,
                GenesisCandidateRow.status == "pending",
            )
            .order_by(GenesisCandidateRow.last_seen_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_status(
        self,
        *,
        candidate_id: uuid.UUID,
        status: str,
        promoted_thread_id: uuid.UUID | None = None,
    ) -> GenesisCandidateRow | None:
        row = await self.get(candidate_id)
        if row is None:
            return None
        row.status = status
        if promoted_thread_id is not None:
            row.promoted_thread_id = promoted_thread_id
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self._session.flush()
        return row
