"""Live C14<->C7 coupling test against the kind cluster Postgres.

Skipped unless WELLBE_DATABASE_URL is set. See the C7 live test for setup.
Exercises the real InvestigationService + ThreadService: closure is denied while
a linked thread is unresolved and permitted once C7 resolves it.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_contracts.c7_thread import HealthThreadStatus, ThreadActor, ThreadActorType
from wellbe_contracts.c14_investigation import (
    INVESTIGATION_CREATED,
    InvestigationOwnerType,
    InvestigationStatus,
    ThreadRelationship,
)
from wellbe_db import create_engine, create_session_factory

from wellbe_c7_thread.service import ThreadService
from wellbe_c14_investigation.errors import ClosureBlockedByThreadError
from wellbe_c14_investigation.service import InvestigationService

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


def _actor() -> ThreadActor:
    return ThreadActor(type=ThreadActorType.USER, id=uuid.uuid4())


async def _cleanup(session_factory, investigation_id, thread_id, patient_id):
    async with session_factory() as s, s.begin():
        await s.execute(
            text("DELETE FROM c14.investigation_state_transitions WHERE investigation_id = :i"),
            {"i": investigation_id},
        )
        await s.execute(
            text("DELETE FROM c14.investigation_threads WHERE investigation_id = :i"),
            {"i": investigation_id},
        )
        await s.execute(
            text("DELETE FROM graph.kg_nodes WHERE normalized_key = :k"),
            {"k": f"investigation:{investigation_id}"},
        )
        await s.execute(
            text("DELETE FROM c14.investigations WHERE id = :i"), {"i": investigation_id}
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
            {"c": f"c14-live-{investigation_id}"},
        )


@pytest.mark.asyncio
async def test_live_investigation_closure_gated_by_thread(session_factory):
    patient_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    corr = None
    investigation_id = None
    try:
        # Create + activate a thread
        async with session_factory() as s, s.begin():
            ts = ThreadService(s)
            await ts.create_thread(patient_id=patient_id, title="dizzy", thread_id=thread_id)
        async with session_factory() as s, s.begin():
            ts = ThreadService(s)
            await ts.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.ACTIVE_UNRESOLVED,
                actor=_actor(),
                reason_code="opened",
                idempotency_key="t1",
                correlation_id="x",
                trace_id="x",
            )

        # Create investigation + link the (unresolved) thread
        async with session_factory() as s, s.begin():
            inv = InvestigationService(s, ThreadService(s))
            investigation_id = await inv.create_investigation(
                patient_id=patient_id,
                primary_question="Why am I dizzy?",
                owner_type=InvestigationOwnerType.USER,
                correlation_id="x",
                trace_id="x",
            )
        corr = f"c14-live-{investigation_id}"
        async with session_factory() as s, s.begin():
            inv = InvestigationService(s, ThreadService(s))
            await inv.link_thread(
                investigation_id=investigation_id,
                thread_id=thread_id,
                relationship=ThreadRelationship.PRIMARY,
                correlation_id=corr,
                trace_id="x",
            )

        # Projection node exists
        async with session_factory() as s:
            node = (
                await s.execute(
                    text("SELECT node_type, status FROM graph.kg_nodes WHERE normalized_key = :k"),
                    {"k": f"investigation:{investigation_id}"},
                )
            ).one()
            assert node.node_type == "Investigation"

        # Move investigation forward, then attempt close while thread unresolved -> denied
        async with session_factory() as s, s.begin():
            inv = InvestigationService(s, ThreadService(s))
            await inv.transition(
                investigation_id=investigation_id,
                target_status=InvestigationStatus.READY_FOR_VISIT,
                reason_code="prep",
                idempotency_key="i1",
                correlation_id=corr,
                trace_id="x",
            )
        async with session_factory() as s, s.begin():
            inv = InvestigationService(s, ThreadService(s))
            with pytest.raises(ClosureBlockedByThreadError):
                await inv.transition(
                    investigation_id=investigation_id,
                    target_status=InvestigationStatus.CLOSED,
                    reason_code="premature",
                    idempotency_key="i2",
                    correlation_id=corr,
                    trace_id="x",
                )

        # Resolve the thread (C7), then closing the investigation is permitted
        async with session_factory() as s, s.begin():
            ts = ThreadService(s)
            await ts.transition_thread(
                thread_id=thread_id,
                target_status=HealthThreadStatus.EXPLAINED,
                actor=_actor(),
                reason_code="explained",
                idempotency_key="t2",
                correlation_id="x",
                trace_id="x",
            )
        async with session_factory() as s, s.begin():
            inv = InvestigationService(s, ThreadService(s))
            result = await inv.transition(
                investigation_id=investigation_id,
                target_status=InvestigationStatus.CLOSED,
                reason_code="resolved",
                idempotency_key="i3",
                correlation_id=corr,
                trace_id="x",
            )
        assert result.to_status is InvestigationStatus.CLOSED

        # created event present
        async with session_factory() as s:
            count = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM events.outbox_events "
                        "WHERE event_type = :et AND payload->>'investigation_id' = :i"
                    ),
                    {"et": INVESTIGATION_CREATED, "i": str(investigation_id)},
                )
            ).scalar_one()
            assert count == 1
    finally:
        if investigation_id is not None:
            await _cleanup(session_factory, investigation_id, thread_id, patient_id)
