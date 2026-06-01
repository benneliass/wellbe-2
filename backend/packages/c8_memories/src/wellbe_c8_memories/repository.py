from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c8_memory import (
    AuthorshipMode,
    LinkRole,
    MemoryLifecycleState,
    MemorySourceRef,
    MemoryType,
)

from wellbe_c8_memories.models import (
    MemoryEntryRow,
    MemorySourceRefRow,
)


def _naive_utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_entry(
        self,
        *,
        memory_entry_id: uuid.UUID,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        memory_type: MemoryType,
        authorship_mode: AuthorshipMode,
        lifecycle_state: MemoryLifecycleState,
        idempotency_key: str,
        title: str | None,
        payload: dict,
        created_by_actor: dict,
        c10_gate_id: uuid.UUID | None = None,
    ) -> MemoryEntryRow:
        row = MemoryEntryRow(
            memory_entry_id=memory_entry_id,
            patient_id=patient_id,
            thread_id=thread_id,
            memory_type=memory_type.value,
            authorship_mode=authorship_mode.value,
            lifecycle_state=lifecycle_state.value,
            title=title,
            payload=payload,
            created_by_actor=created_by_actor,
            c10_gate_id=c10_gate_id,
            created_at=_naive_utcnow(),
            visible_at=_naive_utcnow()
            if lifecycle_state == MemoryLifecycleState.VISIBLE
            else None,
            idempotency_key=idempotency_key,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def insert_source_ref(
        self,
        *,
        memory_entry_id: uuid.UUID,
        patient_id: uuid.UUID,
        ref: MemorySourceRef,
    ) -> None:
        row = MemorySourceRefRow(
            memory_entry_id=memory_entry_id,
            patient_id=patient_id,
            source_ref_id=ref.source_ref_id,
            source_ref_type=ref.source_ref_type.value,
            source_ref_version=ref.source_ref_version,
            field_path=ref.field_path,
            link_role=ref.link_role.value,
            created_at=_naive_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()

    async def set_lifecycle(
        self, *, row: MemoryEntryRow, state: MemoryLifecycleState
    ) -> None:
        row.lifecycle_state = state.value
        if state == MemoryLifecycleState.VISIBLE and row.visible_at is None:
            row.visible_at = _naive_utcnow()
        await self._session.flush()

    async def get(self, memory_entry_id: uuid.UUID) -> MemoryEntryRow | None:
        return await self._session.get(MemoryEntryRow, memory_entry_id)

    async def entries_for_thread(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryEntryRow]:
        stmt = select(MemoryEntryRow).where(
            MemoryEntryRow.patient_id == patient_id,
            MemoryEntryRow.thread_id == thread_id,
        )
        if memory_type is not None:
            stmt = stmt.where(MemoryEntryRow.memory_type == memory_type.value)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def source_refs_for(
        self, memory_entry_id: uuid.UUID
    ) -> list[MemorySourceRefRow]:
        stmt = select(MemorySourceRefRow).where(
            MemorySourceRefRow.memory_entry_id == memory_entry_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def to_source_ref(self, row: MemorySourceRefRow) -> MemorySourceRef:
        from wellbe_contracts.c8_memory import SourceRefType

        return MemorySourceRef(
            source_ref_id=row.source_ref_id,
            source_ref_type=SourceRefType(row.source_ref_type),
            link_role=LinkRole(row.link_role),
            field_path=row.field_path,
            source_ref_version=row.source_ref_version,
        )
