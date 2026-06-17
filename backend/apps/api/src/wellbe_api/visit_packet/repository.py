"""Persistence for visit packets, statements, and share links."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_api.visit_packet.models import PacketRow, ShareLinkRow, StatementRow


class VisitPacketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_packet(self, row: PacketRow) -> PacketRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_statements(self, rows: list[StatementRow]) -> None:
        self._session.add_all(rows)
        await self._session.flush()

    async def get_packet(self, packet_id: uuid.UUID) -> PacketRow | None:
        return await self._session.get(PacketRow, packet_id)

    async def statements_for_packet(self, packet_id: uuid.UUID) -> list[StatementRow]:
        stmt = (
            select(StatementRow)
            .where(StatementRow.packet_id == packet_id)
            .order_by(StatementRow.ordinal)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_statement(self, statement_id: uuid.UUID) -> StatementRow | None:
        return await self._session.get(StatementRow, statement_id)

    async def add_share_link(self, row: ShareLinkRow) -> ShareLinkRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_share_link(self, link_id: uuid.UUID) -> ShareLinkRow | None:
        return await self._session.get(ShareLinkRow, link_id)

    async def share_link_by_token_hash(self, token_hash: str) -> ShareLinkRow | None:
        stmt = select(ShareLinkRow).where(ShareLinkRow.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
