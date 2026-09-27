"""Live C9 due-date policy + due/overdue sweeper against a real Postgres.

Skipped unless WELLBE_DATABASE_URL is set. Covers:
- entering waiting_for_result opens a ``scheduled`` item dated transition + 7 days
  (``relative_policy``), and leaving it resolves the item;
- the sweeper moves scheduled -> due -> overdue, bumps the epoch between phases,
  emits c9.pending_item.due / .overdue once each, and never touches settled items;
- a stale epoch is a recorded no-op; two concurrent sweepers fire each item once.

The sweeper always runs with the real clock: tests move *their own* items into
the past instead of sweeping with a future ``now``, so running this against a
shared dev database never advances anyone else's items early.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c7_thread.service import ThreadService
from wellbe_c9_continuity.policy import DuePolicy
from wellbe_c9_continuity.service import ContinuityService
from wellbe_c9_continuity.sweeper import sweep_once
from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
    ThreadStateChangedPayload,
)
from wellbe_contracts.c9_continuity import (
    C9_PENDING_ITEM_DUE,
    C9_PENDING_ITEM_OVERDUE,
    DuePrecision,
    PendingItemStatus,
    PendingItemType,
    TimerActionType,
)
from wellbe_db import create_engine, create_session_factory

DATABASE_URL = os.environ.get("WELLBE_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="WELLBE_DATABASE_URL not set; live test skipped"
)

_POLICY = DuePolicy()


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def _cleanup(factory, patient_id, thread_ids, corr):
    async with factory() as s, s.begin():
        await s.execute(
            text("DELETE FROM c9.pending_items WHERE patient_id = :p"), {"p": patient_id}
        )
        for tid in thread_ids:
            await s.execute(
                text("DELETE FROM c9.consumed_thread_events WHERE thread_id = :t"), {"t": tid}
            )
            await s.execute(
                text("DELETE FROM thread.thread_state_transitions WHERE thread_id = :t"),
                {"t": tid},
            )
            await s.execute(text("DELETE FROM thread.health_threads WHERE id = :t"), {"t": tid})
        await s.execute(
            text(
                "DELETE FROM events.outbox_events WHERE correlation_id = :c "
                "OR payload->>'patient_id' = :p"
            ),
            {"c": corr, "p": str(patient_id)},
        )


async def _transition(factory, thread_id, target, corr, key):
    async with factory() as s, s.begin():
        await ThreadService(s).transition_thread(
            thread_id=thread_id,
            target_status=target,
            actor=ThreadActor(type=ThreadActorType.USER),
            reason_code="qa",
            idempotency_key=key,
            correlation_id=corr,
            trace_id="x",
        )


async def _reconcile_all(factory, thread_id):
    """Feed this thread's thread.state_changed events to C9 in order."""
    async with factory() as s:
        rows = (
            await s.execute(
                text(
                    "SELECT id, payload FROM events.outbox_events "
                    "WHERE event_type = 'thread.state_changed' "
                    "AND payload->>'thread_id' = :t "
                    "ORDER BY (payload->>'transition_seq')::int"
                ),
                {"t": str(thread_id)},
            )
        ).all()
    for event_id, payload in rows:
        async with factory() as s, s.begin():
            await ContinuityService(s, _POLICY).reconcile_thread_state_changed(
                payload=ThreadStateChangedPayload.model_validate(payload), event_id=event_id
            )


async def _item(factory, item_id):
    async with factory() as s:
        return (
            await s.execute(
                text(
                    "SELECT status, due_at, due_precision, timer_epoch, created_at "
                    "FROM c9.pending_items WHERE pending_item_id = :i"
                ),
                {"i": item_id},
            )
        ).one()


async def _events(factory, item_id, event_type):
    async with factory() as s:
        return (
            await s.execute(
                text(
                    "SELECT count(*) FROM events.outbox_events "
                    "WHERE event_type = :e AND payload->>'pending_item_id' = :i"
                ),
                {"e": event_type, "i": str(item_id)},
            )
        ).scalar_one()


async def _set_due(factory, item_id, due_at):
    async with factory() as s, s.begin():
        await s.execute(
            text("UPDATE c9.pending_items SET due_at = :d WHERE pending_item_id = :i"),
            {"d": due_at, "i": item_id},
        )


async def _scheduled_item(factory, patient_id, thread_id, corr, *, due_at):
    async with factory() as s, s.begin():
        row = await ContinuityService(s, _POLICY).create_pending_item(
            patient_id=patient_id,
            primary_thread_id=thread_id,
            item_type=PendingItemType.RESULT_PENDING,
            title="Waiting for a result: Sweeper QA",
            status=PendingItemStatus.SCHEDULED,
            due_at=due_at,
            due_precision=DuePrecision.RELATIVE_POLICY,
            correlation_id=corr,
        )
        return row.pending_item_id


@pytest.mark.asyncio
async def test_live_waiting_item_is_dated_and_resolves(session_factory):
    patient_id, thread_id = uuid.uuid4(), uuid.uuid4()
    corr = f"c9-due-{patient_id}"
    try:
        async with session_factory() as s, s.begin():
            await ThreadService(s).create_thread(
                patient_id=patient_id, title="Ferritin", thread_id=thread_id
            )
        await _transition(
            session_factory, thread_id, HealthThreadStatus.ACTIVE_UNRESOLVED, corr, "a"
        )
        await _transition(
            session_factory, thread_id, HealthThreadStatus.WAITING_FOR_RESULT, corr, "w"
        )
        await _reconcile_all(session_factory, thread_id)

        async with session_factory() as s:
            item_id, title, opened_at = (
                await s.execute(
                    text(
                        "SELECT p.pending_item_id, p.title, t.created_at "
                        "FROM c9.pending_items p JOIN thread.thread_state_transitions t "
                        "ON t.thread_id = p.primary_thread_id AND t.to_status = "
                        "'waiting_for_result' WHERE p.patient_id = :p"
                    ),
                    {"p": patient_id},
                )
            ).one()
        status, due_at, precision, _, _ = await _item(session_factory, item_id)
        assert title == "Waiting for a result: Ferritin"
        assert status == PendingItemStatus.SCHEDULED.value
        assert precision == DuePrecision.RELATIVE_POLICY.value
        assert due_at == opened_at + timedelta(days=7)

        await _transition(
            session_factory, thread_id, HealthThreadStatus.ACTIVE_UNRESOLVED, corr, "r"
        )
        await _reconcile_all(session_factory, thread_id)
        status, *_ = await _item(session_factory, item_id)
        assert status == PendingItemStatus.RESOLVED.value
    finally:
        await _cleanup(session_factory, patient_id, [thread_id], corr)


@pytest.mark.asyncio
async def test_live_sweeper_due_then_overdue_and_settled_untouched(session_factory):
    patient_id, thread_id = uuid.uuid4(), uuid.uuid4()
    corr = f"c9-sweep-{patient_id}"
    now = datetime.now(UTC)
    try:
        item_id = await _scheduled_item(
            session_factory, patient_id, thread_id, corr, due_at=now + timedelta(days=7)
        )
        settled_id = await _scheduled_item(
            session_factory, patient_id, thread_id, corr, due_at=now - timedelta(days=30)
        )
        async with session_factory() as s, s.begin():
            svc = ContinuityService(s, _POLICY)
            row = await svc._repo.get_for_update(settled_id)
            await svc._repo.set_status(row=row, status=PendingItemStatus.RESOLVED)

        # Not yet due: untouched.
        await sweep_once(session_factory, policy=_POLICY)
        assert (await _item(session_factory, item_id))[0] == "scheduled"

        # Due now: scheduled -> due, epoch bumped (arms overdue), one due event.
        await _set_due(session_factory, item_id, now - timedelta(minutes=1))
        await sweep_once(session_factory, policy=_POLICY)
        status, _, _, epoch, _ = await _item(session_factory, item_id)
        assert (status, epoch) == ("due", 1)
        assert await _events(session_factory, item_id, C9_PENDING_ITEM_DUE) == 1

        # Within grace: stays due; a repeat sweep emits nothing new.
        await sweep_once(session_factory, policy=_POLICY)
        assert (await _item(session_factory, item_id))[0] == "due"
        assert await _events(session_factory, item_id, C9_PENDING_ITEM_DUE) == 1

        # Past grace: due -> overdue, one overdue event.
        await _set_due(session_factory, item_id, now - _POLICY.overdue_grace - timedelta(hours=1))
        await sweep_once(session_factory, policy=_POLICY)
        assert (await _item(session_factory, item_id))[0] == "overdue"
        assert await _events(session_factory, item_id, C9_PENDING_ITEM_OVERDUE) == 1
        await sweep_once(session_factory, policy=_POLICY)
        assert await _events(session_factory, item_id, C9_PENDING_ITEM_OVERDUE) == 1

        # The settled item was never advanced.
        assert (await _item(session_factory, settled_id))[0] == "resolved"
        assert await _events(session_factory, settled_id, C9_PENDING_ITEM_DUE) == 0
    finally:
        await _cleanup(session_factory, patient_id, [], corr)


@pytest.mark.asyncio
async def test_live_stale_epochs_and_concurrent_sweepers(session_factory):
    patient_id, thread_id = uuid.uuid4(), uuid.uuid4()
    corr = f"c9-race-{patient_id}"
    past = datetime.now(UTC) - timedelta(minutes=5)
    try:
        # A resolution that bumped the epoch makes an in-flight due fire stale.
        item_id = await _scheduled_item(session_factory, patient_id, thread_id, corr, due_at=past)
        async with session_factory() as s, s.begin():
            svc = ContinuityService(s, _POLICY)
            await svc._repo.bump_timer_epoch(row=await svc._repo.get_for_update(item_id))
        async with session_factory() as s, s.begin():
            stale = await ContinuityService(s, _POLICY).advance_due_item(
                pending_item_id=item_id, timer_epoch=0
            )
        assert stale.action == TimerActionType.NO_OP_STALE
        assert (await _item(session_factory, item_id))[0] == "scheduled"

        # Overdue fire with the pre-due epoch, or on a non-due item, is a no-op.
        async with session_factory() as s, s.begin():
            not_due = await ContinuityService(s, _POLICY).fire_overdue_timer(
                pending_item_id=item_id, timer_epoch=1
            )
        assert not_due.action == TimerActionType.NO_OP_STALE

        # Two sweepers racing over many due items: each fires exactly once.
        ids = [
            await _scheduled_item(session_factory, patient_id, thread_id, corr, due_at=past)
            for _ in range(6)
        ]
        await asyncio.gather(
            sweep_once(session_factory, policy=_POLICY),
            sweep_once(session_factory, policy=_POLICY),
        )
        for i in [item_id, *ids]:
            assert (await _item(session_factory, i))[0] == "due"
            assert await _events(session_factory, i, C9_PENDING_ITEM_DUE) == 1
    finally:
        await _cleanup(session_factory, patient_id, [], corr)
