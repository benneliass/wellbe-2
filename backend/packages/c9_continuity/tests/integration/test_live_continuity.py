"""Live C9 Continuity test against the kind cluster Postgres.

Skipped unless WELLBE_DATABASE_URL is set. Verifies the safety-critical ledger +
timer-fire protocol WITHOUT requiring a running Temporal cluster (the workflow
activity calls exactly this ``fire_timer`` code):
- a timer fire requests a C7 transition only through transition_thread and stores
  acceptance;
- a late fire after a newer status_version is rejected by C7 and recorded as a
  terminal no-op (no retry storm);
- a superseded timer epoch is a no-op;
- the normal-test safety net blocks any C9 closure request;
- thread.state_changed consumption is idempotent (dedupe) and order-enforced.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c7_thread.service import ThreadService
from wellbe_c9_continuity.errors import OutOfOrderThreadEventError
from wellbe_c9_continuity.service import ContinuityService
from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
    ThreadStateChangedPayload,
)
from wellbe_contracts.c9_continuity import (
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


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def _cleanup(session_factory, patient_id, thread_id, corr):
    async with session_factory() as s, s.begin():
        # timer_actions / events / thread_links cascade on pending_items delete.
        await s.execute(
            text("DELETE FROM c9.pending_items WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM c9.consumed_thread_events WHERE thread_id = :t"),
            {"t": thread_id},
        )
        await s.execute(
            text("DELETE FROM thread.thread_state_transitions WHERE thread_id = :t"),
            {"t": thread_id},
        )
        await s.execute(
            text("DELETE FROM thread.health_threads WHERE id = :t"), {"t": thread_id}
        )
        await s.execute(
            text("DELETE FROM events.outbox_events WHERE correlation_id = :c"),
            {"c": corr},
        )


@pytest.mark.asyncio
async def test_live_timer_protocol_and_safety_net(session_factory):
    patient_id = uuid.uuid4()
    corr = f"c9-live-{patient_id}"
    thread_id = uuid.uuid4()
    try:
        # Create a thread and move it to active_unresolved (status_version -> 1).
        async with session_factory() as s, s.begin():
            ts = ThreadService(s)
            await ts.create_thread(
                patient_id=patient_id, title="Persistent fatigue", thread_id=thread_id
            )
            await ts.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                actor=ThreadActor(type=ThreadActorType.USER),
                reason_code="opened",
                idempotency_key=f"open-{thread_id}",
                correlation_id=corr,
                trace_id="x",
            )

        # A result-pending item that knows the current thread version (1).
        async with session_factory() as s, s.begin():
            item = await ContinuityService(s).create_pending_item(
                patient_id=patient_id,
                primary_thread_id=thread_id,
                item_type=PendingItemType.RESULT_PENDING,
                title="Bloodwork result pending",
                status=PendingItemStatus.SCHEDULED,
                due_at=datetime.now(UTC),
                due_precision=DuePrecision.DATETIME,
                latest_observed_thread_status_version=2,
                correlation_id=corr,
            )
        item_id = item.pending_item_id

        # 1. Timer fires and requests a valid transition through C7 -> accepted.
        async with session_factory() as s, s.begin():
            result = await ContinuityService(s).fire_timer(
                pending_item_id=item_id,
                timer_epoch=0,
                requested_target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                correlation_id=corr,
            )
            assert result.action == TimerActionType.C7_TRANSITION_ACCEPTED

        async with session_factory() as s:
            status = (
                await s.execute(
                    text("SELECT status FROM thread.health_threads WHERE id = :t"),
                    {"t": thread_id},
                )
            ).scalar_one()
            assert status == "waiting_for_result"

        # 2. A second timer that observed the OLD thread version (2) fires after the
        #    thread already advanced to version 3. C7 rejects the stale
        #    expected_version; C9 records a terminal no-op (no retry storm). This is
        #    the two-timer race the decision record requires to be safe.
        async with session_factory() as s, s.begin():
            stale = await ContinuityService(s).create_pending_item(
                patient_id=patient_id,
                primary_thread_id=thread_id,
                item_type=PendingItemType.FOLLOW_UP_DUE,
                title="Stale follow-up timer",
                status=PendingItemStatus.SCHEDULED,
                due_at=datetime.now(UTC),
                due_precision=DuePrecision.DATETIME,
                latest_observed_thread_status_version=2,
                correlation_id=corr,
            )
        async with session_factory() as s, s.begin():
            result = await ContinuityService(s).fire_timer(
                pending_item_id=stale.pending_item_id,
                timer_epoch=0,
                requested_target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                correlation_id=corr,
            )
            assert result.action == TimerActionType.NO_OP_C7_REJECTED
            assert result.c7_rejection_code == "VersionConflictError"

        # 3. Superseded epoch -> no-op stale (no C7 call).
        async with session_factory() as s, s.begin():
            svc = ContinuityService(s)
            row = await svc._repo.get_for_update(item_id)
            await svc._repo.bump_timer_epoch(row=row)  # epoch -> 1
        async with session_factory() as s, s.begin():
            result = await ContinuityService(s).fire_timer(
                pending_item_id=item_id, timer_epoch=0, correlation_id=corr
            )
            assert result.action == TimerActionType.NO_OP_STALE

        # 4. Normal-test safety net blocks any C9 closure request.
        async with session_factory() as s, s.begin():
            svc = ContinuityService(s)
            await svc.ensure_normal_test_safety_net(
                patient_id=patient_id, thread_id=thread_id, status_version=2,
                correlation_id=corr,
            )
            followup = await svc.create_pending_item(
                patient_id=patient_id,
                primary_thread_id=thread_id,
                item_type=PendingItemType.FOLLOW_UP_DUE,
                title="Recheck symptoms",
                status=PendingItemStatus.SCHEDULED,
                due_at=datetime.now(UTC),
                due_precision=DuePrecision.DATETIME,
                latest_observed_thread_status_version=2,
                correlation_id=corr,
            )
        async with session_factory() as s, s.begin():
            result = await ContinuityService(s).fire_timer(
                pending_item_id=followup.pending_item_id,
                timer_epoch=0,
                requested_target_status=HealthThreadStatus.EXPLAINED,
                correlation_id=corr,
            )
            # Blocked at the C9 layer before any closure request reaches C7.
            assert result.action == TimerActionType.NO_OP_STALE

        # 5. thread.state_changed consumption: dedupe + order enforcement.
        ev_id = uuid.uuid4()
        payload = ThreadStateChangedPayload(
            thread_id=thread_id,
            patient_id=patient_id,
            from_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
            to_status=HealthThreadStatus.WAITING_FOR_RESULT,
            transition_seq=1,
            actor=ThreadActor(type=ThreadActorType.SYSTEM),
            reason_code="x",
            idempotency_key="k1",
            correlation_id=corr,
            trace_id="x",
        )
        async with session_factory() as s, s.begin():
            applied = await ContinuityService(s).reconcile_thread_state_changed(
                payload=payload, event_id=ev_id, correlation_id=corr
            )
            assert applied is True
        async with session_factory() as s, s.begin():
            applied = await ContinuityService(s).reconcile_thread_state_changed(
                payload=payload, event_id=ev_id, correlation_id=corr
            )
            assert applied is False  # duplicate deduped

        out_of_order = payload.model_copy(update={"transition_seq": 3})
        async with session_factory() as s, s.begin():
            with pytest.raises(OutOfOrderThreadEventError):
                await ContinuityService(s).reconcile_thread_state_changed(
                    payload=out_of_order, event_id=uuid.uuid4(), correlation_id=corr
                )
    finally:
        await _cleanup(session_factory, patient_id, thread_id, corr)
