from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c6_graph.models import KgNodeRow

from wellbe_c14_investigation.models import (
    InvestigationRow,
    InvestigationStateTransitionRow,
    InvestigationThreadRow,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class InvestigationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        investigation_id: uuid.UUID,
        patient_id: uuid.UUID,
        primary_question: str,
        owner_type: str,
        owner_grant_id: uuid.UUID | None,
        created_by_actor_id: uuid.UUID | None,
    ) -> InvestigationRow:
        now = _utcnow()
        row = InvestigationRow(
            id=investigation_id,
            patient_id=patient_id,
            primary_question=primary_question,
            status="open",
            status_version=1,
            owner_type=owner_type,
            owner_grant_id=owner_grant_id,
            created_by_actor_id=created_by_actor_id,
            status_changed_at=now,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, investigation_id: uuid.UUID) -> InvestigationRow | None:
        stmt = select(InvestigationRow).where(InvestigationRow.id == investigation_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_for_update(self, investigation_id: uuid.UUID) -> InvestigationRow | None:
        stmt = (
            select(InvestigationRow)
            .where(InvestigationRow.id == investigation_id)
            .with_for_update()
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_projection_node(
        self,
        *,
        patient_id: uuid.UUID,
        investigation_id: uuid.UUID,
        display_label: str,
        status: str,
    ) -> uuid.UUID:
        """Write the C6 ``Investigation`` projection node (graph is a projection)."""
        # graph.kg_nodes uses naive-UTC timestamps (matches wellbe_c6_graph).
        now = datetime.now(UTC).replace(tzinfo=None)
        node_id = uuid.uuid4()
        node = KgNodeRow(
            id=node_id,
            patient_id=patient_id,
            node_type="Investigation",
            normalized_key=f"investigation:{investigation_id}",
            display_label=display_label,
            status="active" if status != "closed" else "resolved",
            thread_ids=[],
            node_metadata={"investigation_status": status},
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(node)
        await self._session.flush()
        return node_id

    async def set_projection_node(
        self, investigation_id: uuid.UUID, node_id: uuid.UUID
    ) -> None:
        await self._session.execute(
            update(InvestigationRow)
            .where(InvestigationRow.id == investigation_id)
            .values(projection_node_id=node_id)
        )

    async def link_thread(
        self,
        *,
        investigation_id: uuid.UUID,
        thread_id: uuid.UUID,
        patient_id: uuid.UUID,
        relationship: str,
    ) -> None:
        row = InvestigationThreadRow(
            investigation_id=investigation_id,
            thread_id=thread_id,
            patient_id=patient_id,
            relationship=relationship,
            linked_at=_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()

    async def get_linked_threads(
        self, investigation_id: uuid.UUID, relationships: tuple[str, ...] | None = None
    ) -> list[tuple[uuid.UUID, str]]:
        stmt = select(
            InvestigationThreadRow.thread_id, InvestigationThreadRow.relationship
        ).where(InvestigationThreadRow.investigation_id == investigation_id)
        if relationships:
            stmt = stmt.where(InvestigationThreadRow.relationship.in_(relationships))
        result = await self._session.execute(stmt)
        return [(r.thread_id, r.relationship) for r in result.all()]

    async def find_transition_by_idempotency(
        self, investigation_id: uuid.UUID, idempotency_key: str
    ) -> InvestigationStateTransitionRow | None:
        stmt = select(InvestigationStateTransitionRow).where(
            InvestigationStateTransitionRow.investigation_id == investigation_id,
            InvestigationStateTransitionRow.idempotency_key == idempotency_key,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def next_transition_seq(self, investigation_id: uuid.UUID) -> int:
        stmt = select(
            func.coalesce(func.max(InvestigationStateTransitionRow.transition_seq), 0)
        ).where(InvestigationStateTransitionRow.investigation_id == investigation_id)
        return int((await self._session.execute(stmt)).scalar_one()) + 1

    async def update_status(
        self,
        *,
        investigation_id: uuid.UUID,
        new_status: str,
        new_version: int,
        expected_version: int,
        status_reason: str | None,
    ) -> int:
        stmt = (
            update(InvestigationRow)
            .where(
                InvestigationRow.id == investigation_id,
                InvestigationRow.status_version == expected_version,
            )
            .values(
                status=new_status,
                status_version=new_version,
                status_reason=status_reason,
                status_changed_at=_utcnow(),
            )
        )
        result = await self._session.execute(stmt)
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount

    async def insert_transition(
        self,
        *,
        investigation_id: uuid.UUID,
        patient_id: uuid.UUID,
        from_status: str,
        to_status: str,
        transition_seq: int,
        reason_code: str,
        actor_id: uuid.UUID | None,
        idempotency_key: str,
        correlation_id: str,
        event_id: uuid.UUID | None,
    ) -> None:
        row = InvestigationStateTransitionRow(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            patient_id=patient_id,
            from_status=from_status,
            to_status=to_status,
            transition_seq=transition_seq,
            reason_code=reason_code,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            event_id=event_id,
            created_at=_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()

    async def append_safety_flag(
        self, *, investigation_id: uuid.UUID, flag: dict[str, object]
    ) -> None:
        """Append a safety flag to the investigation's flags JSONB array."""
        row = await self.get_for_update(investigation_id)
        if row is None:
            return
        flags = list(row.safety_flags or [])
        flags.append(flag)
        await self._session.execute(
            update(InvestigationRow)
            .where(InvestigationRow.id == investigation_id)
            .values(safety_flags=flags)
        )
