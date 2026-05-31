from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c6_graph.constants import validate_personal_edge_type
from wellbe_c6_graph.models import KgNodeRow, KgEdgeRow


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
        node_metadata: dict | None = None,
    ) -> KgNodeRow:
        """Insert or update a knowledge graph node (upsert on patient_id + normalized_key)."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)

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

    async def insert_edge(
        self,
        *,
        from_node_id: uuid.UUID,
        to_node_id: uuid.UUID,
        edge_type: str,
        potential_score: float,
        patient_id: uuid.UUID,
        score_inputs: dict | None = None,
        thread_ids: list[uuid.UUID] | None = None,
    ) -> KgEdgeRow:
        # Defense in depth: reject diagnostic verbs and external-only edge types
        # before they can reach the personal graph (mirrors the DB CHECK constraints).
        validate_personal_edge_type(edge_type)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
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
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        stmt = (
            update(KgEdgeRow)
            .where(
                (KgEdgeRow.from_node_id == node_id) | (KgEdgeRow.to_node_id == node_id)
            )
            .values(needs_rescore=True, updated_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

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
