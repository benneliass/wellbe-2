from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c2_vault.models import RawContextEventRow


class VaultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_event(self, **kwargs: object) -> UUID:
        row = RawContextEventRow(**kwargs)
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def get_event(self, event_id: UUID) -> RawContextEventRow | None:
        return await self._session.get(RawContextEventRow, event_id)

    async def find_duplicate(
        self, patient_id: UUID, content_hash: str
    ) -> UUID | None:
        stmt = (
            select(RawContextEventRow.id)
            .where(
                RawContextEventRow.patient_id == patient_id,
                RawContextEventRow.content_hash == content_hash,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row
