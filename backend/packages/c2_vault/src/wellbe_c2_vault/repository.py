from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c2_vault.models import RawContextEventRow, RawContextProvenanceRow


class VaultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_event(self, **kwargs: object) -> UUID:
        row = RawContextEventRow(**kwargs)
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def insert_event_idempotent(self, **kwargs: object) -> tuple[UUID, bool]:
        """Append a raw event idempotently on its (deterministic) primary key.

        Returns ``(event_id, created)``. ``created`` is ``False`` when a row with
        the same id already exists — re-delivery/retry is then a no-op replay,
        which makes the duplicate-write class structurally impossible against the
        append-only Vault (the id is a deterministic uuid5 of the natural key).
        """
        event_id = kwargs["id"]
        stmt = (
            pg_insert(RawContextEventRow)
            .values(**kwargs)
            .on_conflict_do_nothing(index_elements=["id"])
            .returning(RawContextEventRow.id)
        )
        result = await self._session.execute(stmt)
        inserted = result.scalar_one_or_none()
        if inserted is None:
            return UUID(str(event_id)), False
        return inserted, True

    async def insert_provenance(self, **kwargs: object) -> UUID:
        """Append the ingest provenance row idempotently on its unique event_id."""
        stmt = (
            pg_insert(RawContextProvenanceRow)
            .values(**kwargs)
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(RawContextProvenanceRow.provenance_id)
        )
        result = await self._session.execute(stmt)
        pid = result.scalar_one_or_none()
        return pid if pid is not None else UUID(str(kwargs["provenance_id"]))

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
