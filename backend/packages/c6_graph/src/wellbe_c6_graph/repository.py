from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c5_evidence import EvidenceLinkType

from wellbe_c6_graph.constants import SYMMETRIC_EDGE_CODES, validate_personal_edge_type
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow
from wellbe_c6_graph.scoring import PotentialScoreComputer, ScoreInput

# Distinct observations at which an observed relationship reaches full support.
SUPPORT_SATURATION = 3


class GraphRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_node(
        self,
        *,
        patient_id: uuid.UUID,
        node_type: str,
        normalized_key: str,
        display_label: str,
        thread_ids: list[uuid.UUID] | None = None,
        node_metadata: dict[str, Any] | None = None,
    ) -> KgNodeRow:
        """Insert or update a knowledge graph node (upsert on patient_id + normalized_key)."""
        now = datetime.now(UTC).replace(tzinfo=None)

        stmt = select(KgNodeRow).where(
            KgNodeRow.patient_id == patient_id,
            KgNodeRow.normalized_key == normalized_key,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.last_seen_at = now
            existing.updated_at = now
            if thread_ids:
                existing_set = set(existing.thread_ids or [])
                existing.thread_ids = list(existing_set | set(thread_ids))
            if node_metadata:
                merged = dict(existing.node_metadata or {})
                merged.update(node_metadata)
                existing.node_metadata = merged
            await self._session.flush()
            return existing

        node = KgNodeRow(
            id=uuid.uuid4(),
            patient_id=patient_id,
            node_type=node_type,
            normalized_key=normalized_key,
            display_label=display_label,
            status="active",
            thread_ids=thread_ids or [],
            node_metadata=node_metadata,
            first_seen_at=now,
            last_seen_at=now,
            schema_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(node)
        await self._session.flush()
        return node

    async def get_node_by_key(
        self, *, patient_id: uuid.UUID, normalized_key: str
    ) -> KgNodeRow | None:
        """Look up a node by its natural key (patient_id + normalized_key).

        Genesis uses this to attach a ``graph_node_id`` to each fact and to gauge
        graph resolution status without mutating the graph.
        """
        stmt = select(KgNodeRow).where(
            KgNodeRow.patient_id == patient_id,
            KgNodeRow.normalized_key == normalized_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def insert_edge(
        self,
        *,
        from_node_id: uuid.UUID,
        to_node_id: uuid.UUID,
        edge_type: str,
        potential_score: float,
        patient_id: uuid.UUID,
        score_inputs: dict[str, Any] | None = None,
        thread_ids: list[uuid.UUID] | None = None,
    ) -> KgEdgeRow:
        # Defense in depth: reject diagnostic verbs and external-only edge types
        # before they can reach the personal graph (mirrors the DB CHECK constraints).
        validate_personal_edge_type(edge_type)
        now = datetime.now(UTC).replace(tzinfo=None)
        edge = KgEdgeRow(
            id=uuid.uuid4(),
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,
            potential_score=potential_score,
            score_version=1,
            score_inputs=score_inputs,
            needs_rescore=False,
            thread_ids=thread_ids or [],
            patient_id=patient_id,
            schema_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(edge)
        await self._session.flush()
        return edge

    async def mark_needs_rescore(self, node_id: uuid.UUID) -> int:
        """Mark all edges connected to a node as needing rescore."""
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            update(KgEdgeRow)
            .where(
                (KgEdgeRow.from_node_id == node_id) | (KgEdgeRow.to_node_id == node_id)
            )
            .values(needs_rescore=True, updated_at=now)
        )
        result = await self._session.execute(stmt)
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount

    async def edges_for_node(
        self, node_id: uuid.UUID, direction: str = "outgoing"
    ) -> list[KgEdgeRow]:
        if direction == "outgoing":
            stmt = select(KgEdgeRow).where(KgEdgeRow.from_node_id == node_id)
        elif direction == "incoming":
            stmt = select(KgEdgeRow).where(KgEdgeRow.to_node_id == node_id)
        else:
            stmt = select(KgEdgeRow).where(
                (KgEdgeRow.from_node_id == node_id) | (KgEdgeRow.to_node_id == node_id)
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_edges_needing_rescore(self, limit: int = 100) -> list[KgEdgeRow]:
        stmt = (
            select(KgEdgeRow)
            .where(KgEdgeRow.needs_rescore == True)  # noqa: E712
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def nodes_for_thread(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        node_types: list[str] | None = None,
        limit: int = 200,
    ) -> list[KgNodeRow]:
        """Thread-scoped nodes for a patient (WEL-156).

        Anchored to BOTH the authenticated patient and the requested thread:
        ``thread_id = ANY(kg_nodes.thread_ids)``. Out-of-thread nodes are never
        selected, so their existence cannot be disclosed.
        """
        stmt = select(KgNodeRow).where(
            KgNodeRow.patient_id == patient_id,
            KgNodeRow.thread_ids.any(thread_id),  # type: ignore[arg-type]
        )
        if node_types:
            stmt = stmt.where(KgNodeRow.node_type.in_(node_types))
        stmt = stmt.order_by(KgNodeRow.last_seen_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def edges_for_patient(
        self,
        *,
        patient_id: uuid.UUID,
        edge_types: list[str] | None = None,
        limit: int = 200,
    ) -> list[KgEdgeRow]:
        """All of a patient's edges (optionally filtered by type), strongest first.

        Used by the non-diagnostic pattern engine (WEL-79), which surfaces
        cross-thread co-occurrence/temporal candidates. Anchored to the
        authenticated patient.
        """
        stmt = select(KgEdgeRow).where(KgEdgeRow.patient_id == patient_id)
        if edge_types:
            stmt = stmt.where(KgEdgeRow.edge_type.in_(edge_types))
        stmt = stmt.order_by(KgEdgeRow.potential_score.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def nodes_by_ids(
        self, *, patient_id: uuid.UUID, node_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, KgNodeRow]:
        """Fetch patient-owned nodes by id, returned as an id->row map."""
        if not node_ids:
            return {}
        stmt = select(KgNodeRow).where(
            KgNodeRow.patient_id == patient_id,
            KgNodeRow.id.in_(node_ids),
        )
        result = await self._session.execute(stmt)
        return {row.id: row for row in result.scalars().all()}

    async def nodes_for_patient(
        self,
        *,
        patient_id: uuid.UUID,
        node_types: list[str] | None = None,
        limit: int = 500,
    ) -> list[KgNodeRow]:
        """All of a patient's nodes (optionally by type), most-recent first.

        Used by the coverage-aware signals summary (WEL-91), which reports what
        signal-bearing data the patient actually has and how fresh it is.
        Anchored to the authenticated patient; never crosses owners.
        """
        stmt = select(KgNodeRow).where(KgNodeRow.patient_id == patient_id)
        if node_types:
            stmt = stmt.where(KgNodeRow.node_type.in_(node_types))
        stmt = stmt.order_by(KgNodeRow.last_seen_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def edges_among_nodes(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        node_ids: list[uuid.UUID],
        edge_types: list[str] | None = None,
        limit: int = 400,
    ) -> list[KgEdgeRow]:
        """Edges of a thread whose BOTH endpoints are in the in-thread node set.

        Requiring both endpoints in ``node_ids`` structurally omits any edge that
        would reach an out-of-thread node, so no adjacent out-of-scope node id or
        existence is ever leaked (per docs/decisions/graph-query-api-contract.md).
        """
        if not node_ids:
            return []
        stmt = select(KgEdgeRow).where(
            KgEdgeRow.patient_id == patient_id,
            KgEdgeRow.thread_ids.any(thread_id),  # type: ignore[arg-type]
            KgEdgeRow.from_node_id.in_(node_ids),
            KgEdgeRow.to_node_id.in_(node_ids),
        )
        if edge_types:
            stmt = stmt.where(KgEdgeRow.edge_type.in_(edge_types))
        stmt = stmt.order_by(KgEdgeRow.potential_score.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def edges_touching_nodes(
        self,
        *,
        patient_id: uuid.UUID,
        node_ids: list[uuid.UUID],
        edge_types: list[str] | None = None,
        limit: int = 200,
    ) -> list[KgEdgeRow]:
        """The patient's edges with at least one endpoint in ``node_ids``, strongest first.

        Used for a bounded 1-hop expansion around a thread's nodes. Anchored to the
        authenticated patient only (not the thread), so callers must decide whether
        the principal may see out-of-thread neighbours before using the result.
        """
        if not node_ids:
            return []
        stmt = select(KgEdgeRow).where(
            KgEdgeRow.patient_id == patient_id,
            KgEdgeRow.from_node_id.in_(node_ids) | KgEdgeRow.to_node_id.in_(node_ids),
        )
        if edge_types:
            stmt = stmt.where(KgEdgeRow.edge_type.in_(edge_types))
        stmt = stmt.order_by(KgEdgeRow.potential_score.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def tag_nodes_with_thread(
        self, *, patient_id: uuid.UUID, node_ids: list[uuid.UUID], thread_id: uuid.UUID
    ) -> int:
        """Add ``thread_id`` to each node's ``thread_ids`` (idempotent, patient-anchored)."""
        if not node_ids:
            return 0
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            update(KgNodeRow)
            .where(
                KgNodeRow.patient_id == patient_id,
                KgNodeRow.id.in_(node_ids),
                ~KgNodeRow.thread_ids.any(thread_id),  # type: ignore[arg-type]
            )
            .values(
                thread_ids=func.array_append(KgNodeRow.thread_ids, thread_id),
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def tag_edges_within_thread(
        self, *, patient_id: uuid.UUID, thread_id: uuid.UUID
    ) -> int:
        """Add ``thread_id`` to every edge whose BOTH endpoints are in the thread.

        Keeps edge thread scope derived from node scope, so an edge never becomes
        visible in a thread view that does not contain both of its endpoints.
        """
        member_ids = select(KgNodeRow.id).where(
            KgNodeRow.patient_id == patient_id,
            KgNodeRow.thread_ids.any(thread_id),  # type: ignore[arg-type]
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            update(KgEdgeRow)
            .where(
                KgEdgeRow.patient_id == patient_id,
                KgEdgeRow.from_node_id.in_(member_ids),
                KgEdgeRow.to_node_id.in_(member_ids),
                ~KgEdgeRow.thread_ids.any(thread_id),  # type: ignore[arg-type]
            )
            .values(
                thread_ids=func.array_append(KgEdgeRow.thread_ids, thread_id),
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def upsert_observed_edge(
        self,
        *,
        patient_id: uuid.UUID,
        from_node_id: uuid.UUID,
        to_node_id: uuid.UUID,
        edge_type: str,
        confidence: float,
        observation_key: str,
        link_type: EvidenceLinkType = EvidenceLinkType.PRIMARY,
    ) -> tuple[KgEdgeRow, bool]:
        """Record one observation of a relationship; create or strengthen the edge.

        Symmetric relations are stored once per unordered pair (lower id first).
        ``observation_key`` (e.g. the raw event id) makes re-delivery a no-op: the
        same observation never strengthens an edge twice. Support grows with
        distinct observations (``min(1, n / SUPPORT_SATURATION)``), so a single
        co-mention stays in the sparse / missing-data band.
        Returns ``(edge, changed)``.
        """
        validate_personal_edge_type(edge_type)
        if from_node_id == to_node_id:
            raise ValueError("self-loop edges are not allowed")
        if edge_type in SYMMETRIC_EDGE_CODES and str(from_node_id) > str(to_node_id):
            from_node_id, to_node_id = to_node_id, from_node_id

        stmt = select(KgEdgeRow).where(
            KgEdgeRow.patient_id == patient_id,
            KgEdgeRow.from_node_id == from_node_id,
            KgEdgeRow.to_node_id == to_node_id,
            KgEdgeRow.edge_type == edge_type,
        )
        existing = (await self._session.execute(stmt)).scalars().first()
        inputs = dict(existing.score_inputs or {}) if existing is not None else {}
        observations: dict[str, float] = dict(inputs.get("observations") or {})
        if observation_key in observations:
            assert existing is not None
            return existing, False
        observations[observation_key] = round(float(confidence), 4)

        scored = PotentialScoreComputer().compute(
            [
                ScoreInput(link_type=link_type, confidence=c, edge_category=edge_type)
                for c in observations.values()
            ]
        )
        support = min(1.0, len(observations) / SUPPORT_SATURATION)
        score = round(scored.potential_score * support, 4)
        score_inputs = {
            **scored.score_inputs,
            "observations": observations,
            "support": round(support, 4),
            "score_semantics": "observed_relationship_support",
        }
        now = datetime.now(UTC).replace(tzinfo=None)
        if existing is not None:
            existing.potential_score = score
            existing.score_version = scored.score_version
            existing.score_inputs = score_inputs
            existing.needs_rescore = False
            existing.updated_at = now
            await self._session.flush()
            return existing, True

        edge = await self.insert_edge(
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,
            potential_score=score,
            patient_id=patient_id,
            score_inputs=score_inputs,
        )
        return edge, True
