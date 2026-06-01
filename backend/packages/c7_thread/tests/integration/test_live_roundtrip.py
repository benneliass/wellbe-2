"""Live C7 integration test against a real Postgres (the kind cluster).

Skipped unless WELLBE_DATABASE_URL is set, e.g.:

    kubectl port-forward -n wellbe svc/wellbe-postgres 5432:5432 &
    WELLBE_DATABASE_URL="postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe" \
        uv run pytest packages/c7_thread/tests/integration -v

Exercises the full transactional command path: create -> transition chain,
outbox emission in the same transaction, idempotency replay, optimistic version
conflict, and the closure-safety guard — all against the live schema + trigger.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_contracts.c7_thread import (
    THREAD_STATE_CHANGED,
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
    TransitionGuardContext,
)
from wellbe_db import create_engine, create_session_factory

from wellbe_c7_thread.errors import ClosureSafetyError, VersionConflictError
from wellbe_c7_thread.service import ThreadService

DATABASE_URL = os.environ.get("WELLBE_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="WELLBE_DATABASE_URL not set; live integration test skipped",
)


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


def _actor() -> ThreadActor:
    return ThreadActor(type=ThreadActorType.USER, id=uuid.uuid4())


async def _cleanup(session_factory, thread_id: uuid.UUID) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(
            text("DELETE FROM thread.thread_state_transitions WHERE thread_id = :tid"),
            {"tid": thread_id},
        )
        await session.execute(
            text("DELETE FROM thread.health_threads WHERE id = :tid"),
            {"tid": thread_id},
        )
        await session.execute(
            text(
                "DELETE FROM events.outbox_events "
                "WHERE event_type = :et AND payload->>'thread_id' = :tid"
            ),
            {"et": THREAD_STATE_CHANGED, "tid": str(thread_id)},
        )


@pytest.mark.asyncio
async def test_live_transition_chain_and_outbox(session_factory):
    patient_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    try:
        # Create
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            await svc.create_thread(
                patient_id=patient_id, title="Live thread", thread_id=thread_id
            )

        # draft -> active_unresolved
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            r1 = await svc.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                actor=_actor(),
                reason_code="opened",
                idempotency_key="k1",
                correlation_id="c1",
                trace_id="t1",
            )
        assert r1.status_version == 2
        assert r1.transition_seq == 1
        assert r1.event_id is not None

        # active_unresolved -> waiting_for_result
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            r2 = await svc.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                actor=_actor(),
                reason_code="labs_ordered",
                idempotency_key="k2",
                correlation_id="c2",
                trace_id="t2",
            )
        assert r2.status_version == 3
        assert r2.transition_seq == 2

        # Verify persisted state, transition history, and outbox events
        async with session_factory() as session:
            status = (
                await session.execute(
                    text("SELECT status, status_version FROM thread.health_threads WHERE id = :tid"),
                    {"tid": thread_id},
                )
            ).one()
            assert status.status == "waiting_for_result"
            assert status.status_version == 3

            tcount = (
                await session.execute(
                    text("SELECT count(*) FROM thread.thread_state_transitions WHERE thread_id = :tid"),
                    {"tid": thread_id},
                )
            ).scalar_one()
            assert tcount == 2

            ecount = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM events.outbox_events "
                        "WHERE event_type = :et AND payload->>'thread_id' = :tid"
                    ),
                    {"et": THREAD_STATE_CHANGED, "tid": str(thread_id)},
                )
            ).scalar_one()
            assert ecount == 2

        # Idempotent replay: same key -> prior result, no new event
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            replay = await svc.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.WAITING_FOR_RESULT,
                actor=_actor(),
                reason_code="labs_ordered",
                idempotency_key="k2",
                correlation_id="c2",
                trace_id="t2",
            )
        assert replay.idempotent_replay is True
        assert replay.transition_seq == 2

        async with session_factory() as session:
            ecount2 = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM events.outbox_events "
                        "WHERE event_type = :et AND payload->>'thread_id' = :tid"
                    ),
                    {"et": THREAD_STATE_CHANGED, "tid": str(thread_id)},
                )
            ).scalar_one()
            assert ecount2 == 2  # unchanged

        # Optimistic version conflict
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            with pytest.raises(VersionConflictError):
                await svc.transition_thread(
                    thread_id=thread_id,
                    target_status=HealthThreadStatus.ESCALATED,
                    actor=_actor(),
                    reason_code="stale",
                    idempotency_key="k3",
                    correlation_id="c3",
                    trace_id="t3",
                    expected_version=99,
                )
    finally:
        await _cleanup(session_factory, thread_id)


@pytest.mark.asyncio
async def test_live_closure_safety_guard(session_factory):
    patient_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    try:
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            await svc.create_thread(
                patient_id=patient_id, title="Closure guard", thread_id=thread_id
            )
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            await svc.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                actor=_actor(),
                reason_code="opened",
                idempotency_key="k1",
                correlation_id="c1",
                trace_id="t1",
            )
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            await svc.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.EXPLAINED,
                actor=_actor(),
                reason_code="explained",
                idempotency_key="k2",
                correlation_id="c2",
                trace_id="t2",
            )
        # explained -> closed while symptoms persist must be rejected
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            with pytest.raises(ClosureSafetyError):
                await svc.transition_thread(
                    thread_id=thread_id,
                    target_status=HealthThreadStatus.CLOSED,
                    actor=_actor(),
                    reason_code="premature_close",
                    idempotency_key="k3",
                    correlation_id="c3",
                    trace_id="t3",
                    guard_context=TransitionGuardContext(symptoms_persist=True),
                )
        # Safe closure succeeds
        async with session_factory() as session, session.begin():
            svc = ThreadService(session)
            ok = await svc.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.CLOSED,
                actor=_actor(),
                reason_code="resolved",
                idempotency_key="k4",
                correlation_id="c4",
                trace_id="t4",
                guard_context=TransitionGuardContext(),
            )
        assert ok.to_status is HealthThreadStatus.CLOSED
    finally:
        await _cleanup(session_factory, thread_id)
