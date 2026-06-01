"""In-cluster durability smoke test for C9 Temporal timers.

Required by the approved decision record
(docs/decisions/continuity-pending-ledger-durable-timers.md): prove that a pending
follow-up timer survives BOTH a continuity-worker restart AND a Temporal service
restart, and still fires exactly once.

Run as two phases (the orchestrator restarts worker/Temporal between them):

    python -m wellbe_continuity_worker.smoke start    # create ledger item + start timer
    python -m wellbe_continuity_worker.smoke verify    # assert the timer fired

IDs are derived deterministically from TEST_RUN_ID so the phases share state without
passing values around. The timer uses requested_target_status=None, so firing is a
pure C9 effect (status -> due + a 'fired' timer_action) with no C7 dependency.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from temporalio.client import Client
from wellbe_c9_continuity.service import ContinuityService
from wellbe_c9_continuity.temporal.workflows import (
    PendingItemWorkflow,
    PendingItemWorkflowInput,
)
from wellbe_contracts.c9_continuity import (
    DuePrecision,
    PendingItemStatus,
    PendingItemType,
    workflow_id,
)
from wellbe_db import create_engine, create_session_factory

_NS = uuid.UUID("00000000-0000-0000-0000-00000000c900")
DELAY_SECONDS = int(os.environ.get("SMOKE_DELAY_SECONDS", "60"))


def _ids() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    run = os.environ["TEST_RUN_ID"]
    pending = uuid.uuid5(_NS, f"pending:{run}")
    patient = uuid.uuid5(_NS, f"patient:{run}")
    thread = uuid.uuid5(_NS, f"thread:{run}")
    return pending, patient, thread


async def _start() -> None:
    pending_id, patient_id, thread_id = _ids()
    db_url = os.environ["WELLBE_DATABASE_URL"]
    engine = create_engine(db_url)
    factory = create_session_factory(engine)
    async with factory() as s, s.begin():
        svc = ContinuityService(s)
        await svc.create_pending_item(
            patient_id=patient_id,
            primary_thread_id=thread_id,
            item_type=PendingItemType.FOLLOW_UP_DUE,
            title="Durability smoke timer",
            status=PendingItemStatus.SCHEDULED,
            due_at=datetime.now(UTC),
            due_precision=DuePrecision.DATETIME,
            pending_item_id=pending_id,
            idempotency_key=f"smoke:{pending_id}",
            correlation_id=f"smoke-{pending_id}",
        )
    await engine.dispose()

    client = await Client.connect(
        os.environ.get("WELLBE_TEMPORAL_HOST", "temporal:7233"),
        namespace=os.environ.get("WELLBE_TEMPORAL_NAMESPACE", "default"),
    )
    await client.start_workflow(
        PendingItemWorkflow.run,
        PendingItemWorkflowInput(
            pending_item_id=str(pending_id),
            timer_epoch=0,
            delay_seconds=DELAY_SECONDS,
        ),
        id=workflow_id(pending_id),
        task_queue="c9-continuity",
    )
    print(f"STARTED workflow {workflow_id(pending_id)} delay={DELAY_SECONDS}s")


async def _verify() -> None:
    pending_id, _, _ = _ids()
    engine = create_engine(os.environ["WELLBE_DATABASE_URL"])
    factory = create_session_factory(engine)
    async with factory() as s:
        status = (
            await s.execute(
                text("SELECT status FROM c9.pending_items WHERE pending_item_id = :p"),
                {"p": str(pending_id)},
            )
        ).scalar_one_or_none()
        fired = (
            await s.execute(
                text(
                    "SELECT count(*) FROM c9.timer_actions "
                    "WHERE pending_item_id = :p AND action_type = 'fired'"
                ),
                {"p": str(pending_id)},
            )
        ).scalar_one()
    await engine.dispose()
    print(f"VERIFY status={status} fired_count={fired}")
    if status != "due" or fired != 1:
        raise SystemExit(
            f"DURABILITY FAILED: expected status=due fired=1, got status={status} "
            f"fired={fired}"
        )
    print("DURABILITY OK: timer fired exactly once after restarts")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "start"
    asyncio.run(_start() if mode == "start" else _verify())


if __name__ == "__main__":
    main()
