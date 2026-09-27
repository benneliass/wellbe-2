from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, func, not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c6_graph.constants import validate_personal_edge_type
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow

from wellbe_c15_theory.models import (
    TheoryEvaluationRow,
    TheoryExternalContextRow,
    TheoryRow,
)

USER_EVIDENCE_SOURCE = "user_evaluation"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _naive_utcnow() -> datetime:
    # graph.* tables use naive-UTC timestamps (matches wellbe_c6_graph).
    return datetime.now(UTC).replace(tzinfo=None)


class TheoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_theory(
        self,
        *,
        theory_id: uuid.UUID,
        patient_id: uuid.UUID,
        theory_text: str,
        normalized_question: str | None,
        theory_type: str,
        status: str,
        safety_level: str,
        linked_investigation_id: uuid.UUID | None,
        created_by_actor_id: uuid.UUID | None,
    ) -> TheoryRow:
        now = _utcnow()
        row = TheoryRow(
            id=theory_id,
            patient_id=patient_id,
            theory_text=theory_text,
            normalized_question=normalized_question,
            theory_type=theory_type,
            status=status,
            safety_level=safety_level,
            linked_investigation_id=linked_investigation_id,
            created_by_actor_id=created_by_actor_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, theory_id: uuid.UUID) -> TheoryRow | None:
        stmt = select(TheoryRow).where(TheoryRow.id == theory_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_investigation(
        self, investigation_id: uuid.UUID, *, limit: int = 100
    ) -> list[TheoryRow]:
        stmt = (
            select(TheoryRow)
            .where(TheoryRow.linked_investigation_id == investigation_id)
            .order_by(TheoryRow.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def create_projection_node(
        self, *, patient_id: uuid.UUID, theory_id: uuid.UUID, display_label: str
    ) -> uuid.UUID:
        now = _naive_utcnow()
        node_id = uuid.uuid4()
        node = KgNodeRow(
            id=node_id,
            patient_id=patient_id,
            node_type="Theory",
            normalized_key=f"theory:{theory_id}",
            display_label=display_label,
            status="active",
            thread_ids=[],
            node_metadata={"theory_id": str(theory_id)},
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(node)
        await self._session.flush()
        return node_id

    async def set_projection_node(self, theory_id: uuid.UUID, node_id: uuid.UUID) -> None:
        await self._session.execute(
            update(TheoryRow).where(TheoryRow.id == theory_id).values(projection_node_id=node_id)
        )

    async def create_evidence_edge(
        self,
        *,
        patient_id: uuid.UUID,
        from_node_id: uuid.UUID,
        theory_node_id: uuid.UUID,
        edge_type: str,
        potential_score: float,
    ) -> uuid.UUID:
        """Create a personal evidence edge: personal fact node -> Theory node.

        edge_type is 'evidence_for' or 'evidence_against'. Both endpoints share
        the same patient_id (caller guarantees personal, C5-backed source).
        """
        now = _naive_utcnow()
        edge_id = uuid.uuid4()
        edge = KgEdgeRow(
            id=edge_id,
            from_node_id=from_node_id,
            to_node_id=theory_node_id,
            edge_type=edge_type,
            potential_score=potential_score,
            score_inputs={"score_semantics": "personal_evidence_quality"},
            thread_ids=[],
            patient_id=patient_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(edge)
        await self._session.flush()
        return edge_id

    async def next_evaluation_version(self, theory_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(TheoryEvaluationRow.evaluation_version), 0)).where(
            TheoryEvaluationRow.theory_id == theory_id
        )
        return int((await self._session.execute(stmt)).scalar_one()) + 1

    async def insert_evaluation(
        self,
        *,
        evaluation_id: uuid.UUID,
        theory_id: uuid.UUID,
        patient_id: uuid.UUID,
        evaluation_version: int,
        evidence_for_node_ids: list[uuid.UUID],
        evidence_against_node_ids: list[uuid.UUID],
        missing_data: list[dict[str, object]],
        external_context_link_ids: list[uuid.UUID],
        proposed_status: str,
        proposed_safety_level: str,
        c10_gate_result: dict[str, object],
        evaluator_actor_id: uuid.UUID | None,
    ) -> None:
        row = TheoryEvaluationRow(
            id=evaluation_id,
            theory_id=theory_id,
            patient_id=patient_id,
            evaluation_version=evaluation_version,
            evidence_for_node_ids=evidence_for_node_ids,
            evidence_against_node_ids=evidence_against_node_ids,
            missing_data=missing_data,
            external_context_link_ids=external_context_link_ids,
            proposed_status=proposed_status,
            proposed_safety_level=proposed_safety_level,
            c10_gate_result=c10_gate_result,
            evaluator_actor_id=evaluator_actor_id,
            created_at=_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()

    async def insert_external_context(
        self,
        *,
        theory_id: uuid.UUID,
        patient_id: uuid.UUID,
        external_source_id: uuid.UUID,
        external_claim_id: uuid.UUID | None,
        relevance_link_id: uuid.UUID,
        context_direction: str,
    ) -> None:
        row = TheoryExternalContextRow(
            id=uuid.uuid4(),
            theory_id=theory_id,
            patient_id=patient_id,
            external_source_id=external_source_id,
            external_claim_id=external_claim_id,
            relevance_link_id=relevance_link_id,
            context_direction=context_direction,
            context_only=True,
            created_at=_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()

    async def apply_evaluation(
        self,
        *,
        theory_id: uuid.UUID,
        status: str,
        safety_level: str,
        latest_evaluation_id: uuid.UUID,
    ) -> None:
        await self._session.execute(
            update(TheoryRow)
            .where(TheoryRow.id == theory_id)
            .values(
                status=status,
                safety_level=safety_level,
                latest_evaluation_id=latest_evaluation_id,
                version=TheoryRow.version + 1,
                updated_at=_utcnow(),
            )
        )

    # ------------------------------------------------------------------
    # User evaluations
    # ------------------------------------------------------------------

    async def find_evaluation_by_idempotency(
        self, idempotency_key: str
    ) -> TheoryEvaluationRow | None:
        stmt = select(TheoryEvaluationRow).where(
            TheoryEvaluationRow.idempotency_key == idempotency_key
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def insert_user_evaluation(
        self,
        *,
        evaluation_id: uuid.UUID,
        theory_id: uuid.UUID,
        patient_id: uuid.UUID,
        evaluation_version: int,
        actor_id: uuid.UUID,
        assessment: str,
        from_status: str,
        to_status: str,
        safety_level: str,
        rationale: str,
        evidence_refs: list[dict[str, object]],
        evidence_for_node_ids: list[uuid.UUID],
        evidence_against_node_ids: list[uuid.UUID],
        idempotency_key: str,
    ) -> TheoryEvaluationRow:
        row = TheoryEvaluationRow(
            id=evaluation_id,
            theory_id=theory_id,
            patient_id=patient_id,
            evaluation_version=evaluation_version,
            evaluation_kind="user",
            assessment=assessment,
            from_status=from_status,
            proposed_status=to_status,
            proposed_safety_level=safety_level,
            rationale=rationale,
            evidence_refs=evidence_refs,
            evidence_for_node_ids=evidence_for_node_ids,
            evidence_against_node_ids=evidence_against_node_ids,
            missing_data=[],
            external_context_link_ids=[],
            c10_gate_result={},
            evaluator_actor_id=actor_id,
            idempotency_key=idempotency_key,
            created_at=_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def apply_user_evaluation(
        self,
        *,
        theory_id: uuid.UUID,
        expected_version: int,
        status: str,
        latest_evaluation_id: uuid.UUID,
    ) -> int | None:
        """Compare-and-set the theory status; returns the new version or None on conflict."""
        stmt = (
            update(TheoryRow)
            .where(TheoryRow.id == theory_id, TheoryRow.version == expected_version)
            .values(
                status=status,
                latest_evaluation_id=latest_evaluation_id,
                version=TheoryRow.version + 1,
                updated_at=_utcnow(),
            )
            .returning(TheoryRow.version)
            .execution_options(synchronize_session=False)
        )
        new_version = (await self._session.execute(stmt)).scalar_one_or_none()
        return int(new_version) if new_version is not None else None

    async def list_user_evaluations(
        self, theory_id: uuid.UUID, *, limit: int = 100
    ) -> list[TheoryEvaluationRow]:
        stmt = (
            select(TheoryEvaluationRow)
            .where(
                TheoryEvaluationRow.theory_id == theory_id,
                TheoryEvaluationRow.evaluation_kind == "user",
            )
            .order_by(TheoryEvaluationRow.evaluation_version.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def latest_user_evaluations(
        self, theory_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, TheoryEvaluationRow]:
        if not theory_ids:
            return {}
        stmt = (
            select(TheoryEvaluationRow)
            .where(
                TheoryEvaluationRow.theory_id.in_(theory_ids),
                TheoryEvaluationRow.evaluation_kind == "user",
            )
            .order_by(
                TheoryEvaluationRow.theory_id,
                TheoryEvaluationRow.evaluation_version.desc(),
            )
            .distinct(TheoryEvaluationRow.theory_id)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return {r.theory_id: r for r in rows}

    async def update_theory_node(
        self, *, patient_id: uuid.UUID, node_id: uuid.UUID, metadata: dict[str, Any]
    ) -> None:
        node = (
            await self._session.execute(
                select(KgNodeRow).where(
                    KgNodeRow.id == node_id, KgNodeRow.patient_id == patient_id
                )
            )
        ).scalar_one_or_none()
        if node is None:
            return
        merged = dict(node.node_metadata or {})
        merged.update(metadata)
        node.node_metadata = merged
        node.last_seen_at = _naive_utcnow()
        node.updated_at = node.last_seen_at
        await self._session.flush()

    async def sync_user_evidence_edges(
        self,
        *,
        patient_id: uuid.UUID,
        theory_node_id: uuid.UUID,
        edge_type: str | None,
        score_inputs_by_node: dict[uuid.UUID, dict[str, Any]],
        potential_score: float,
    ) -> list[uuid.UUID]:
        """Make the theory node's user-cited evidence edges match the latest evaluation.

        Edges from earlier user evaluations that the latest one no longer cites (or
        cites in the other direction) are removed, so the graph shows the user's
        current view; the immutable evaluation log keeps the history. Edges written
        by the system evaluator are never touched.
        """
        user_sourced = KgEdgeRow.score_inputs["source"].astext == USER_EVIDENCE_SOURCE
        keep = (
            and_(
                KgEdgeRow.edge_type == edge_type,
                KgEdgeRow.from_node_id.in_(list(score_inputs_by_node)),
            )
            if edge_type is not None and score_inputs_by_node
            else None
        )
        stale = delete(KgEdgeRow).where(
            KgEdgeRow.patient_id == patient_id,
            KgEdgeRow.to_node_id == theory_node_id,
            user_sourced,
        )
        if keep is not None:
            stale = stale.where(not_(keep))
        await self._session.execute(stale.execution_options(synchronize_session=False))

        if edge_type is None:
            await self._session.flush()
            return []
        validate_personal_edge_type(edge_type)

        now = _naive_utcnow()
        existing = {
            e.from_node_id: e
            for e in (
                await self._session.execute(
                    select(KgEdgeRow).where(
                        KgEdgeRow.patient_id == patient_id,
                        KgEdgeRow.to_node_id == theory_node_id,
                        KgEdgeRow.edge_type == edge_type,
                        user_sourced,
                    )
                )
            ).scalars()
        }
        edge_ids: list[uuid.UUID] = []
        for from_node_id, inputs in score_inputs_by_node.items():
            if from_node_id == theory_node_id:
                continue
            payload = {**inputs, "source": USER_EVIDENCE_SOURCE}
            edge = existing.get(from_node_id)
            if edge is not None:
                edge.score_inputs = payload
                edge.potential_score = potential_score
                edge.updated_at = now
            else:
                edge = KgEdgeRow(
                    id=uuid.uuid4(),
                    from_node_id=from_node_id,
                    to_node_id=theory_node_id,
                    edge_type=edge_type,
                    potential_score=potential_score,
                    score_inputs=payload,
                    thread_ids=[],
                    patient_id=patient_id,
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(edge)
            edge_ids.append(edge.id)
        await self._session.flush()
        return edge_ids
