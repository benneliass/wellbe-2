from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c7_thread.models import HealthThreadRow, ThreadStateTransitionRow


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ThreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_thread(
        self,
        *,
        thread_id: uuid.UUID,
        patient_id: uuid.UUID,
        title: str,
    ) -> HealthThreadRow:
        now = _utcnow()
        row = HealthThreadRow(
            id=thread_id,
            patient_id=patient_id,
            title=title,
            status="draft",
            status_version=1,
            status_changed_at=now,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_for_update(self, thread_id: uuid.UUID) -> HealthThreadRow | None:
        """Load a thread row with a row-level write lock (SELECT ... FOR UPDATE).

        This serialises concurrent transitions on the same thread: a second
        in-flight transition blocks until the first commits, then observes the
        incremented status_version.
        """
        stmt = (
            select(HealthThreadRow)
            .where(HealthThreadRow.id == thread_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, thread_id: uuid.UUID) -> HealthThreadRow | None:
        stmt = select(HealthThreadRow).where(HealthThreadRow.id == thread_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, limit: int = 100
    ) -> list[HealthThreadRow]:
        stmt = (
            select(HealthThreadRow)
            .where(HealthThreadRow.patient_id == patient_id)
            .order_by(HealthThreadRow.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_transition_by_idempotency(
        self, thread_id: uuid.UUID, idempotency_key: str
    ) -> ThreadStateTransitionRow | None:
        stmt = select(ThreadStateTransitionRow).where(
            ThreadStateTransitionRow.thread_id == thread_id,
            ThreadStateTransitionRow.idempotency_key == idempotency_key,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def next_transition_seq(self, thread_id: uuid.UUID) -> int:
        stmt = select(func.coalesce(func.max(ThreadStateTransitionRow.transition_seq), 0)).where(
            ThreadStateTransitionRow.thread_id == thread_id
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one()) + 1

    async def update_status(
        self,
        *,
        thread_id: uuid.UUID,
        new_status: str,
        new_version: int,
        expected_version: int,
        status_changed_at: datetime,
    ) -> int:
        """Conditionally update status; returns affected row count.

        The WHERE clause pins status_version = expected_version so a lost-update
        race produces 0 affected rows rather than silently overwriting.
        """
        stmt = (
            update(HealthThreadRow)
            .where(
                HealthThreadRow.id == thread_id,
                HealthThreadRow.status_version == expected_version,
            )
            .values(
                status=new_status,
                status_version=new_version,
                status_changed_at=status_changed_at,
            )
        )
        result = await self._session.execute(stmt)
        rowcount: int = result.rowcount  # type: ignore[attr-defined]
        return rowcount

    async def insert_transition(
        self,
        *,
        transition_id: uuid.UUID,
        thread_id: uuid.UUID,
        from_status: str,
        to_status: str,
        transition_seq: int,
        actor_type: str,
        actor_id: uuid.UUID | None,
        reason_code: str,
        evidence_refs: list[dict[str, object]],
        safety_flags: list[str],
        idempotency_key: str,
        correlation_id: str,
        event_id: uuid.UUID | None,
    ) -> ThreadStateTransitionRow:
        row = ThreadStateTransitionRow(
            id=transition_id,
            thread_id=thread_id,
            from_status=from_status,
            to_status=to_status,
            transition_seq=transition_seq,
            actor_type=actor_type,
            actor_id=actor_id,
            reason_code=reason_code,
            evidence_refs=evidence_refs,
            safety_flags=safety_flags,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            event_id=event_id,
            created_at=_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row
