"""Live integration test for the what-changed delta reads (WEL-56).

Skipped unless WELLBE_DATABASE_URL is set, e.g.:

    kubectl port-forward -n wellbe svc/wellbe-postgres 5432:5432 &
    WELLBE_DATABASE_URL="postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe" \
        uv run pytest packages/c9_continuity/tests/integration -v

Verifies the privacy-critical guarantees the digest relies on against the live
schema: C9 ``changed_since_for_patient`` and C7 ``transitions_since_for_patient``
return ONLY the authenticated patient's rows, and respect the ``since`` window.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_contracts.c9_continuity import PendingItemStatus, PendingItemType
from wellbe_db import create_engine, create_session_factory

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


async def _cleanup(session_factory, patient_ids, thread_ids) -> None:
    async with session_factory() as session, session.begin():
        for pid in patient_ids:
            await session.execute(
                text("DELETE FROM c9.pending_items WHERE patient_id = :p"), {"p": pid}
            )
        for tid in thread_ids:
            await session.execute(
                text("DELETE FROM thread.thread_state_transitions WHERE thread_id = :t"),
                {"t": tid},
            )
            await session.execute(
                text("DELETE FROM thread.health_threads WHERE id = :t"), {"t": tid}
            )


@pytest.mark.asyncio
async def test_delta_reads_are_patient_scoped_and_windowed(session_factory):
    patient = uuid.uuid4()
    other = uuid.uuid4()
    thread = uuid.uuid4()
    other_thread = uuid.uuid4()
    since = datetime.now(UTC) - timedelta(days=7)
    try:
        async with session_factory() as session, session.begin():
            c9 = ContinuityRepository(session)
            c7 = ThreadRepository(session)
            # Our patient: a recent pending item + a thread transition.
            await c9.insert_pending_item(
                pending_item_id=uuid.uuid4(), patient_id=patient,
                primary_thread_id=thread, item_type=PendingItemType.RESULT_PENDING,
                status=PendingItemStatus.ACTIVE, title="My x-ray result",
                idempotency_key=f"k-{uuid.uuid4()}",
            )
            await c7.create_thread(thread_id=thread, patient_id=patient, title="My cough")
            await c7.insert_transition(
                transition_id=uuid.uuid4(), thread_id=thread, from_status="draft",
                to_status="waiting_for_result", transition_seq=1, actor_type="user",
                actor_id=patient, reason_code="user_action", evidence_refs=[],
                safety_flags=[], idempotency_key=f"t-{uuid.uuid4()}",
                correlation_id="test", event_id=None,
            )
            # Another patient: a pending item + thread transition that must NOT leak.
            await c9.insert_pending_item(
                pending_item_id=uuid.uuid4(), patient_id=other,
                primary_thread_id=other_thread, item_type=PendingItemType.RESULT_PENDING,
                status=PendingItemStatus.ACTIVE, title="Intruder result",
                idempotency_key=f"k-{uuid.uuid4()}",
            )
            await c7.create_thread(
                thread_id=other_thread, patient_id=other, title="Intruder thread"
            )
            await c7.insert_transition(
                transition_id=uuid.uuid4(), thread_id=other_thread, from_status="draft",
                to_status="referred", transition_seq=1, actor_type="user",
                actor_id=other, reason_code="user_action", evidence_refs=[],
                safety_flags=[], idempotency_key=f"t-{uuid.uuid4()}",
                correlation_id="test", event_id=None,
            )

        async with session_factory() as session:
            c9 = ContinuityRepository(session)
            c7 = ThreadRepository(session)

            items = await c9.changed_since_for_patient(patient, since=since)
            assert {i.title for i in items} == {"My x-ray result"}

            transitions = await c7.transitions_since_for_patient(patient, since=since)
            assert {title for _, title in transitions} == {"My cough"}
            assert all(t.to_status == "waiting_for_result" for t, _ in transitions)

            # Window excludes old changes.
            future = datetime.now(UTC) + timedelta(days=1)
            assert await c9.changed_since_for_patient(patient, since=future) == []
            assert await c7.transitions_since_for_patient(patient, since=future) == []
    finally:
        await _cleanup(session_factory, [patient, other], [thread, other_thread])
