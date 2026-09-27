"""Live notification-worker consumption against a real Postgres.

Skipped unless WELLBE_DATABASE_URL is set. Verifies the worker turns C9
pending-item events into exactly one in-app notification each (a replayed event
is a no-op), skips reminders for settled items while still marking them
delivered, and leaves other event types for their own consumers.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c9_continuity.service import ContinuityService
from wellbe_c12_audit.notifications import NotificationDraft, NotificationStore
from wellbe_contracts.c9_continuity import DuePrecision, PendingItemStatus, PendingItemType
from wellbe_contracts.c12_audit import InAppNotificationKind
from wellbe_db import create_engine, create_session_factory
from wellbe_events import emit_event
from wellbe_notification_worker.main import consume_once

DATABASE_URL = os.environ.get("WELLBE_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="WELLBE_DATABASE_URL not set; live test skipped"
)


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def _notifications(factory, patient_id):
    async with factory() as s:
        return (
            await s.execute(
                text(
                    "SELECT kind, title, thread_id FROM notifications.in_app_notifications "
                    "WHERE patient_id = :p ORDER BY created_at"
                ),
                {"p": patient_id},
            )
        ).all()


async def _drain(factory):
    while await consume_once(factory):
        pass


@pytest.mark.asyncio
async def test_live_consume_creates_one_notification_per_event(session_factory):
    patient_id, thread_id = uuid.uuid4(), uuid.uuid4()
    corr = f"notif-live-{patient_id}"
    try:
        async with session_factory() as s, s.begin():
            svc = ContinuityService(s)
            item = await svc.create_pending_item(
                patient_id=patient_id,
                primary_thread_id=thread_id,
                item_type=PendingItemType.RESULT_PENDING,
                title="Waiting for a result: Ferritin",
                status=PendingItemStatus.SCHEDULED,
                due_at=datetime.now(UTC) + timedelta(days=7),
                due_precision=DuePrecision.RELATIVE_POLICY,
                correlation_id=corr,
            )
            settled = await svc.create_pending_item(
                patient_id=patient_id,
                primary_thread_id=thread_id,
                item_type=PendingItemType.REFERRAL_PENDING,
                title="Waiting on a referral: Knee",
                correlation_id=corr,
            )
            await svc._repo.set_status(row=settled, status=PendingItemStatus.RESOLVED)
            unrelated = await emit_event(
                session=s,
                event_type="c9.timer.no_op_stale",
                payload={"pending_item_id": str(item.pending_item_id)},
                correlation_id=corr,
                trace_id=corr,
            )

        await _drain(session_factory)
        rows = await _notifications(session_factory, patient_id)
        assert [(k, t) for k, t, _ in rows] == [
            ("pending_item_created", "New follow-up: Waiting for a result: Ferritin")
        ]
        assert rows[0][2] == thread_id

        # Replay every C9 event for this patient: still exactly one notification.
        async with session_factory() as s, s.begin():
            await s.execute(
                text(
                    "UPDATE events.outbox_events SET delivered_at = NULL "
                    "WHERE correlation_id = :c AND event_type LIKE 'c9.pending_item.%'"
                ),
                {"c": corr},
            )
        await _drain(session_factory)
        assert len(await _notifications(session_factory, patient_id)) == 1

        async with session_factory() as s:
            pending = (
                await s.execute(
                    text(
                        "SELECT event_type, delivered_at IS NOT NULL FROM events.outbox_events "
                        "WHERE correlation_id = :c ORDER BY event_type"
                    ),
                    {"c": corr},
                )
            ).all()
            unrelated_delivered = (
                await s.execute(
                    text("SELECT delivered_at FROM events.outbox_events WHERE id = :i"),
                    {"i": unrelated},
                )
            ).scalar_one()
        # Both created events (including the settled item's) were consumed; the
        # unrelated event type is left for its own consumer.
        assert [p for p in pending if p[0] == "c9.pending_item.created"] == [
            ("c9.pending_item.created", True),
            ("c9.pending_item.created", True),
        ]
        assert unrelated_delivered is None

        # The store the API reads: unread first, idempotent mark-read, read-all.
        async with session_factory() as s, s.begin():
            store = NotificationStore(s)
            await store.create(
                NotificationDraft(
                    patient_id=patient_id,
                    kind=InAppNotificationKind.PENDING_ITEM_DUE,
                    title="A follow-up is due: Waiting for a result: Ferritin",
                    body="b",
                    pending_item_id=item.pending_item_id,
                    thread_id=thread_id,
                    idempotency_key=f"c9:{item.pending_item_id}:due:0",
                )
            )
        async with session_factory() as s, s.begin():
            store = NotificationStore(s)
            listed = await store.list_for_patient(patient_id)
            assert await store.unread_count(patient_id) == 2
            first = await store.mark_read(patient_id, listed[-1].id)
            assert first is not None and first.read_at is not None
            again = await store.mark_read(patient_id, listed[-1].id)
            assert again is not None and again.read_at == first.read_at
            assert await store.mark_read(uuid.uuid4(), listed[0].id) is None
        async with session_factory() as s, s.begin():
            store = NotificationStore(s)
            ordered = await store.list_for_patient(patient_id)
            assert [n.read_at is None for n in ordered] == [True, False]
            assert await store.mark_all_read(patient_id) == 1
            assert await store.unread_count(patient_id) == 0
    finally:
        async with session_factory() as s, s.begin():
            await s.execute(
                text("DELETE FROM c9.pending_items WHERE patient_id = :p"), {"p": patient_id}
            )
            await s.execute(
                text("DELETE FROM events.outbox_events WHERE correlation_id = :c"), {"c": corr}
            )
