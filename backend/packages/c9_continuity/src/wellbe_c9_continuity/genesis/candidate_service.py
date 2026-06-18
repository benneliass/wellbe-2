"""Pending thread-candidate store (Story C0).

The minimal durable "Things noticed" object: a non-alarming, lossless destination
for weak/ambiguous concern signals that are not yet active threads. Create/update
is idempotent on the candidate key (concern key + episode bucket), so repeated
mentions of one concern update a single candidate rather than fragmenting.

The caller owns the commit (matching C5/C7/genesis-decision), so a candidate and
any sibling side effects in the same genesis turn land in one transaction.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.genesis import (
    CandidateStatus,
    ConcernKey,
    ConcernType,
    GenesisFactInput,
    ThreadCandidate,
)

from wellbe_c9_continuity.genesis.candidate_repository import CandidateRepository
from wellbe_c9_continuity.genesis.concern_key import calm_display_title, candidate_key
from wellbe_c9_continuity.genesis.errors import (
    CandidateNotFoundError,
    OrphanCandidateError,
)
from wellbe_c9_continuity.genesis.models import GenesisCandidateRow

# A pending candidate seen this many times is due for promotion to an active
# thread (repeat-signal rule). MVP default; the promotion itself is Story B1.
DEFAULT_REPEAT_SIGNAL_THRESHOLD = 3


class GenesisCandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CandidateRepository(session)

    async def create_or_update(
        self,
        *,
        concern_key: ConcernKey,
        facts: list[GenesisFactInput],
        source_capture_ids: list[uuid.UUID] | None = None,
        source_fact_ids: list[uuid.UUID] | None = None,
        source_graph_entity_ids: list[uuid.UUID] | None = None,
        evidence_link_ids: list[uuid.UUID] | None = None,
        confidence: float | None = None,
        reason_code: str | None = None,
        display_title: str | None = None,
    ) -> ThreadCandidate:
        """Idempotently record a pending candidate for a concern.

        Raises :class:`OrphanCandidateError` if there is no originating capture or
        fact — a candidate must always trace back to what was noticed.
        """
        captures = source_capture_ids or []
        derived_facts = source_fact_ids or [f.fact_id for f in facts]
        if not captures and not derived_facts:
            raise OrphanCandidateError(concern_key.user_id)

        title = display_title or calm_display_title(facts)
        row, _created = await self._repo.upsert(
            candidate_id=uuid.uuid4(),
            user_id=concern_key.user_id,
            candidate_key=candidate_key(concern_key),
            concern_key=concern_key.model_dump(mode="json"),
            episode_bucket=concern_key.episode_bucket,
            display_title=title,
            candidate_type=concern_key.concern_type.value,
            source_capture_ids=captures,
            source_fact_ids=derived_facts,
            source_graph_entity_ids=source_graph_entity_ids or [],
            evidence_link_ids=evidence_link_ids or [],
            confidence=confidence,
            reason_code=reason_code,
        )
        return self._to_candidate(row)

    async def list_things_noticed(
        self, user_id: uuid.UUID, *, limit: int = 100
    ) -> list[ThreadCandidate]:
        """Pending candidates for the user, most-recently-seen first."""
        rows = await self._repo.list_pending(user_id, limit=limit)
        return [self._to_candidate(r) for r in rows]

    async def dismiss(self, candidate_id: uuid.UUID) -> ThreadCandidate:
        """User stops tracking a candidate. Evidence + history are preserved."""
        return await self._set_status(candidate_id, CandidateStatus.DISMISSED)

    async def promote(
        self, candidate_id: uuid.UUID, *, thread_id: uuid.UUID
    ) -> ThreadCandidate:
        """Mark a candidate promoted into a C7 thread (thread create is Story B1)."""
        return await self._set_status(
            candidate_id, CandidateStatus.PROMOTED, promoted_thread_id=thread_id
        )

    async def merge(
        self, candidate_id: uuid.UUID, *, into_thread_id: uuid.UUID
    ) -> ThreadCandidate:
        """Fold a candidate into an existing thread."""
        return await self._set_status(
            candidate_id, CandidateStatus.MERGED, promoted_thread_id=into_thread_id
        )

    @staticmethod
    def is_promotion_due(
        candidate: ThreadCandidate,
        *,
        threshold: int = DEFAULT_REPEAT_SIGNAL_THRESHOLD,
    ) -> bool:
        """Whether a pending candidate has been seen enough times to promote."""
        return (
            candidate.status is CandidateStatus.PENDING
            and candidate.seen_count >= threshold
        )

    async def _set_status(
        self,
        candidate_id: uuid.UUID,
        status: CandidateStatus,
        *,
        promoted_thread_id: uuid.UUID | None = None,
    ) -> ThreadCandidate:
        row = await self._repo.set_status(
            candidate_id=candidate_id,
            status=status.value,
            promoted_thread_id=promoted_thread_id,
        )
        if row is None:
            raise CandidateNotFoundError(candidate_id)
        return self._to_candidate(row)

    @staticmethod
    def _to_candidate(row: GenesisCandidateRow) -> ThreadCandidate:
        def _aware(value: datetime) -> datetime:
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value

        return ThreadCandidate(
            candidate_id=row.candidate_id,
            user_id=row.user_id,
            concern_key=dict(row.concern_key or {}),
            episode_bucket=row.episode_bucket,
            display_title=row.display_title,
            candidate_type=ConcernType(row.candidate_type),
            source_capture_ids=list(row.source_capture_ids or []),
            source_fact_ids=list(row.source_fact_ids or []),
            source_graph_entity_ids=list(row.source_graph_entity_ids or []),
            evidence_link_ids=list(row.evidence_link_ids or []),
            status=CandidateStatus(row.status),
            confidence=row.confidence,
            reason_code=row.reason_code,
            first_seen_at=_aware(row.first_seen_at),
            last_seen_at=_aware(row.last_seen_at),
            seen_count=row.seen_count,
            promoted_thread_id=row.promoted_thread_id,
            created_at=_aware(row.created_at),
            updated_at=_aware(row.updated_at),
        )
