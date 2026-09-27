"""Live integration test for things-noticed review holds (ignore / remind later).

Skipped unless WELLBE_DATABASE_URL is set, e.g.:

    kubectl port-forward -n wellbe svc/wellbe-postgres 5432:5432 &
    WELLBE_DATABASE_URL="postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe" \
        uv run pytest packages/c9_continuity/tests/integration -v

Verifies against the live schema (migration 026) that ``list_pending`` hides a
snoozed candidate until its ``snoozed_until`` and an ignored candidate until it
is seen again, while both stay ``pending``.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c9_continuity.genesis.candidate_repository import CandidateRepository
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


async def _upsert(repo: CandidateRepository, user_id: uuid.UUID, key: str):
    row, _ = await repo.upsert(
        candidate_id=uuid.uuid4(),
        user_id=user_id,
        candidate_key=key,
        concern_key={"concern_type": "symptom"},
        episode_bucket="2026-09",
        display_title=key,
        candidate_type="symptom",
        source_capture_ids=[uuid.uuid4()],
        source_fact_ids=[],
        source_graph_entity_ids=[],
        evidence_link_ids=[],
        confidence=0.5,
        reason_code="default_candidate_pending_classification",
    )
    return row


@pytest.mark.asyncio
async def test_holds_hide_candidates_until_due_or_seen_again(session_factory):
    user_id = uuid.uuid4()
    suffix = uuid.uuid4().hex[:8]
    try:
        async with session_factory() as session, session.begin():
            repo = CandidateRepository(session)
            snoozed = await _upsert(repo, user_id, f"snoozed-{suffix}")
            ignored = await _upsert(repo, user_id, f"ignored-{suffix}")
            plain = await _upsert(repo, user_id, f"plain-{suffix}")
            now = datetime.now(UTC)
            await repo.set_hold(
                candidate_id=snoozed.candidate_id,
                snoozed_until=now + timedelta(days=3),
                ignored_at=None,
            )
            await repo.set_hold(
                candidate_id=ignored.candidate_id,
                snoozed_until=None,
                ignored_at=now + timedelta(seconds=1),
            )

            visible = {r.candidate_id for r in await repo.list_pending(user_id)}
            assert visible == {plain.candidate_id}

            later = {
                r.candidate_id
                for r in await repo.list_pending(user_id, now=now + timedelta(days=4))
            }
            assert snoozed.candidate_id in later
            assert ignored.candidate_id not in later

            # A repeat mention advances last_seen_at past ignored_at.
            ignored.last_seen_at = (now + timedelta(minutes=5)).replace(tzinfo=None)
            await session.flush()
            again = {r.candidate_id for r in await repo.list_pending(user_id)}
            assert ignored.candidate_id in again
            assert snoozed.status == "pending" and ignored.status == "pending"
    finally:
        async with session_factory() as session, session.begin():
            await session.execute(
                text("DELETE FROM genesis.thread_candidates WHERE user_id = :u"),
                {"u": user_id},
            )
