from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c9_continuity.genesis.models import GenesisDecisionRow


class GenesisDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_decision(
        self,
        *,
        decision_id: uuid.UUID,
        user_id: uuid.UUID,
        source_event_id: uuid.UUID,
        capture_id: uuid.UUID,
        fact_ids: list[uuid.UUID],
        graph_node_id: uuid.UUID | None,
        graph_cluster_id: uuid.UUID | None,
        concern_key: dict[str, object],
        episode_bucket: str,
        decision: str,
        reason_code: str,
        confidence: float | None,
        policy_version: int,
        decision_inputs_hash: str,
        target_thread_id: uuid.UUID | None = None,
        candidate_id: uuid.UUID | None = None,
        created_thread_id: uuid.UUID | None = None,
        evidence_link_ids: list[uuid.UUID] | None = None,
        supersedes_decision_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        """Idempotently append a genesis decision.

        Uniqueness is enforced on ``decision_inputs_hash``. On redelivery of the
        same genesis event for the same concern the insert is a no-op and ``None``
        is returned, so the consumer can detect a replay and avoid re-applying
        downstream side effects.
        """
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            pg_insert(GenesisDecisionRow)
            .values(
                decision_id=decision_id,
                user_id=user_id,
                source_event_id=source_event_id,
                capture_id=capture_id,
                fact_ids=fact_ids,
                graph_node_id=graph_node_id,
                graph_cluster_id=graph_cluster_id,
                concern_key=concern_key,
                episode_bucket=episode_bucket,
                decision=decision,
                reason_code=reason_code,
                confidence=confidence,
                policy_version=policy_version,
                target_thread_id=target_thread_id,
                candidate_id=candidate_id,
                created_thread_id=created_thread_id,
                evidence_link_ids=evidence_link_ids or [],
                decision_inputs_hash=decision_inputs_hash,
                created_at=now,
                supersedes_decision_id=supersedes_decision_id,
            )
            .on_conflict_do_nothing(constraint="uq_genesis_decision_inputs_hash")
            .returning(GenesisDecisionRow.decision_id)
        )
        result = await self._session.execute(stmt)
        inserted_id = result.scalar_one_or_none()
        await self._session.flush()
        return inserted_id

    async def update_decision_outcome(
        self,
        *,
        decision_id: uuid.UUID,
        target_thread_id: uuid.UUID | None = None,
        candidate_id: uuid.UUID | None = None,
        created_thread_id: uuid.UUID | None = None,
        evidence_link_ids: list[uuid.UUID] | None = None,
    ) -> None:
        """Complete the outcome columns of a freshly-claimed decision.

        Called once, in the same transaction that just inserted the decision, after
        the side effect (thread create/attach or candidate upsert) produced its ids.
        This is NOT a re-evaluation: the decision/reason/concern_key/hash are never
        altered — only the outcome references the row was created to hold are filled.
        A re-evaluation under a new policy version still writes a NEW row
        (``supersedes_decision_id``), never mutates this one.
        """
        stmt = (
            update(GenesisDecisionRow)
            .where(GenesisDecisionRow.decision_id == decision_id)
            .values(
                target_thread_id=target_thread_id,
                candidate_id=candidate_id,
                created_thread_id=created_thread_id,
                evidence_link_ids=evidence_link_ids or [],
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_by_hash(self, decision_inputs_hash: str) -> GenesisDecisionRow | None:
        stmt = select(GenesisDecisionRow).where(
            GenesisDecisionRow.decision_inputs_hash == decision_inputs_hash
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_capture(self, capture_id: uuid.UUID) -> list[GenesisDecisionRow]:
        stmt = (
            select(GenesisDecisionRow)
            .where(GenesisDecisionRow.capture_id == capture_id)
            .order_by(GenesisDecisionRow.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
