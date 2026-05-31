from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_events.models import OutboxEventRow


class OutboxWriter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def emit(
        self,
        event_type: str,
        payload: dict,
        correlation_id: str,
        trace_id: str,
    ) -> uuid.UUID:
        row = OutboxEventRow(
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row.id


async def emit_event(
    session: AsyncSession,
    event_type: str,
    payload: dict,
    correlation_id: str,
    trace_id: str,
) -> uuid.UUID:
    writer = OutboxWriter(session)
    return await writer.emit(event_type, payload, correlation_id, trace_id)
