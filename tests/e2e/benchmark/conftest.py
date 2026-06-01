"""E2E benchmark fixtures: reset the pipeline, seed the corpus, wait for it to settle.

Lifecycle (once per session):
  1. TRUNCATE every pipeline table so the run is clean and reproducible. The user
     authorized wiping pipeline data; after this the DB contains ONLY what we seed.
  2. Seed all five benchmark cases in blind_pre_diagnosis mode via the ingestion-worker.
  3. Poll Postgres until ingestion + async C4/C5/C6 processing has settled
     (all events landed AND fact/link/node counts stable across consecutive polls).

The reset+seed runs in its own asyncio loop inside a synchronous session fixture so it
fully completes before any per-test event loop starts; each test then opens its own
connection. Connection/URL overrides:
  INGESTION_WORKER_URL  (default http://localhost:8003)
  WELLBE_PG_DSN         (default postgresql://wellbe:wellbe_dev@localhost:5432/wellbe)
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest
import pytest_asyncio

from . import db, expected
from .seeder import seed

INGESTION_WORKER_URL = os.environ.get("INGESTION_WORKER_URL", "http://localhost:8003")

# Generous bounds: 197 sequential POSTs + outbox-poller-driven async processing.
SETTLE_TIMEOUT_S = float(os.environ.get("BENCHMARK_SETTLE_TIMEOUT_S", "300"))
SETTLE_POLL_INTERVAL_S = 3.0
SETTLE_STABLE_POLLS = 3  # counts must be unchanged this many polls in a row


async def _wait_until_settled() -> dict[str, int]:
    conn = await db.connect()
    try:
        deadline = time.monotonic() + SETTLE_TIMEOUT_S
        last: tuple[int, int, int, int] | None = None
        stable = 0
        while time.monotonic() < deadline:
            await asyncio.sleep(SETTLE_POLL_INTERVAL_S)
            snapshot = (
                await db.count_events(conn),
                await db.count_facts(conn),
                await db.count_links(conn),
                await db.count_nodes(conn),
            )
            all_events_in = snapshot[0] >= expected.TOTAL_EVENTS
            if snapshot == last and all_events_in:
                stable += 1
                if stable >= SETTLE_STABLE_POLLS:
                    break
            else:
                stable = 0
            last = snapshot
        return {
            "events": last[0] if last else 0,
            "facts": last[1] if last else 0,
            "links": last[2] if last else 0,
            "nodes": last[3] if last else 0,
        }
    finally:
        await conn.close()


async def _reset_seed_settle() -> dict:
    conn = await db.connect()
    try:
        await db.reset_pipeline(conn)
    finally:
        await conn.close()

    sent_by_case = await seed(INGESTION_WORKER_URL, mode=expected.MODE)
    total_sent = sum(sent_by_case.values())
    if total_sent != expected.TOTAL_EVENTS:
        raise RuntimeError(
            f"Seeded {total_sent} events but expected {expected.TOTAL_EVENTS}; "
            f"per-case: {sent_by_case}"
        )

    settled = await _wait_until_settled()
    return {"sent_by_case": sent_by_case, "settled": settled}


@pytest.fixture(scope="session", autouse=True)
def seeded_cluster() -> dict:
    """Reset + seed + settle exactly once for the whole benchmark E2E session."""
    return asyncio.run(_reset_seed_settle())


@pytest_asyncio.fixture
async def conn():
    connection = await db.connect()
    try:
        yield connection
    finally:
        await connection.close()
