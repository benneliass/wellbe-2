from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select, update

from wellbe_db import AsyncSessionFactory
from wellbe_events.models import OutboxEventRow

logger = logging.getLogger(__name__)


class RedisStreamPublisher:
    def __init__(
        self,
        redis_url: str,
        session_factory: AsyncSessionFactory,
        stream_name: str = "wellbe:events",
    ) -> None:
        self._redis = aioredis.from_url(redis_url)
        self._session_factory = session_factory
        self._stream_name = stream_name

    async def poll_and_publish(self, batch_size: int = 100) -> int:
        async with self._session_factory() as session:
            stmt = (
                select(OutboxEventRow)
                .where(OutboxEventRow.delivered_at.is_(None))
                .order_by(OutboxEventRow.created_at)
                .limit(batch_size)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return 0

            for row in rows:
                await self._redis.xadd(
                    self._stream_name,
                    {
                        "event_id": str(row.id),
                        "event_type": row.event_type,
                        "payload": json.dumps(row.payload),
                        "correlation_id": row.correlation_id,
                        "trace_id": row.trace_id,
                    },
                )

            ids = [row.id for row in rows]
            await session.execute(
                update(OutboxEventRow)
                .where(OutboxEventRow.id.in_(ids))
                .values(delivered_at=datetime.now(timezone.utc))
            )
            await session.commit()

        return len(ids)

    async def run_forever(self, interval_seconds: float = 1.0) -> None:
        while True:
            try:
                count = await self.poll_and_publish()
                if count:
                    logger.info("published %d events", count)
            except Exception:
                logger.exception("error in poll_and_publish")
            await asyncio.sleep(interval_seconds)

    async def close(self) -> None:
        await self._redis.aclose()
