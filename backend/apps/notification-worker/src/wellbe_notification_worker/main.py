"""C12 Notification Worker: turns C9 pending-item events into in-app notifications.

The single consumer of ``c9.pending_item.created`` / ``.due`` / ``.overdue`` in
the transactional outbox. Each poll claims undelivered rows FOR UPDATE SKIP
LOCKED (a second replica can never double-process), and handles every event in
its own savepoint *inside the claiming transaction*: the notification insert and
the ``delivered_at`` mark commit atomically. A failing event rolls back only its
savepoint and stays undelivered for the next poll. Inserts are idempotent on the
notification key, so even a replayed event cannot duplicate a notification.

In-app only: no push, email, or messaging channel is ever contacted.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_c12_audit.notifications import (
    PENDING_ITEM_EVENT_KINDS,
    NotificationStore,
    PendingItemSnapshot,
    draft_for_pending_item_event,
)
from wellbe_db import AsyncSessionFactory, create_engine, create_session_factory
from wellbe_events.models import OutboxEventRow

from wellbe_notification_worker.config import NotificationWorkerSettings

logger = logging.getLogger("wellbe.notification_worker")

CONSUMED_EVENT_TYPES = tuple(PENDING_ITEM_EVENT_KINDS)


async def handle_pending_item_event(
    session: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
    event_id: uuid.UUID | None,
) -> str:
    """Create the notification for one C9 event. Returns a short outcome label."""
    raw_id = payload.get("pending_item_id")
    try:
        pending_item_id = uuid.UUID(str(raw_id))
    except ValueError:
        return "skipped: malformed pending_item_id"

    row = await ContinuityRepository(session).get(pending_item_id)
    snapshot = (
        PendingItemSnapshot(
            pending_item_id=row.pending_item_id,
            patient_id=row.patient_id,
            thread_id=row.primary_thread_id,
            item_type=row.item_type,
            status=row.status,
            title=row.title,
            due_at=row.due_at,
        )
        if row is not None
        else None
    )
    draft = draft_for_pending_item_event(event_type, payload, snapshot)
    if draft is None:
        return "skipped: item gone, settled, or superseded"
    created = await NotificationStore(session).create(draft, source_event_id=event_id)
    return f"created {draft.kind.value}" if created else "duplicate"


async def consume_once(session_factory: AsyncSessionFactory, *, batch_size: int = 50) -> int:
    """Claim and handle one batch. Returns how many events were marked delivered."""
    delivered = 0
    async with session_factory() as session, session.begin():
        rows = (
            await session.execute(
                select(OutboxEventRow)
                .where(OutboxEventRow.delivered_at.is_(None))
                .where(OutboxEventRow.event_type.in_(CONSUMED_EVENT_TYPES))
                .order_by(OutboxEventRow.created_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        for row in rows:
            try:
                async with session.begin_nested():
                    outcome = await handle_pending_item_event(
                        session,
                        event_type=row.event_type,
                        payload=row.payload if isinstance(row.payload, dict) else {},
                        event_id=row.id,
                    )
                    row.delivered_at = datetime.now(UTC).replace(tzinfo=None)
                delivered += 1
                logger.info("%s %s -> %s", row.event_type, row.id, outcome)
            except Exception:
                logger.exception("error handling %s %s; will retry", row.event_type, row.id)
    return delivered


async def run(settings: NotificationWorkerSettings) -> None:
    engine = create_engine(settings.database_url)
    factory = create_session_factory(engine)
    logger.info(
        "Notification worker consuming %s every %.0fs (in-app only)",
        ", ".join(CONSUMED_EVENT_TYPES),
        settings.notification_poll_interval_seconds,
    )
    try:
        while True:
            try:
                await consume_once(factory, batch_size=settings.notification_batch_size)
            except Exception:
                logger.exception("notification consumer loop error")
            await asyncio.sleep(settings.notification_poll_interval_seconds)
    finally:
        await engine.dispose()


def main() -> None:
    settings = NotificationWorkerSettings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
