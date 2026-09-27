"""C9 Continuity Worker.

Advances C9 pending-item timers with exactly one mechanism, chosen by
``WELLBE_C9_TIMER_MECHANISM``:

- ``sweeper`` (default, homeserver): a periodic ledger sweep that moves items
  ``scheduled -> due -> overdue`` with the race-safe timer-fire protocol and
  emits ``c9.pending_item.due`` / ``.overdue``. No Temporal dependency at runtime.
- ``temporal``: hosts the per-item durable-timer workflow and the timer-fire
  activity on the ``c9-continuity`` task queue. The activity is where all
  non-deterministic work (DB reads, C7 ``transition_thread`` calls) happens; the
  workflow only owns the durable timer and reschedule/cancel signals.

See docs/decisions/c9-due-reminders-sweeper.md for why the homeserver sweeps.
"""

from __future__ import annotations

import asyncio
import logging

from wellbe_contracts.c9_continuity import TASK_QUEUE

from wellbe_continuity_worker.config import ContinuityWorkerSettings

# The workflow module itself is deterministic (it only uses pure DTOs + the
# activity-by-name), but importing it runs the wellbe_c9_continuity package
# __init__, which pulls in SQLAlchemy/DB code. Pass those modules through the
# sandbox so import succeeds; the workflow never calls into them at runtime.
_PASSTHROUGH_MODULES = (
    "wellbe_c9_continuity",
    "wellbe_contracts",
    "wellbe_db",
    "wellbe_events",
    "wellbe_platform",
    "wellbe_c7_thread",
    "sqlalchemy",
    "asyncpg",
    "greenlet",
    "pydantic",
    "pydantic_core",
)

settings = ContinuityWorkerSettings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("wellbe.continuity_worker")


async def run_sweeper_mode() -> None:
    from wellbe_c9_continuity.policy import default_policy
    from wellbe_c9_continuity.sweeper import run_sweeper
    from wellbe_db import create_engine, create_session_factory

    policy = default_policy()
    logger.info(
        "Continuity worker sweeping C9 timers every %.0fs (windows=%s, overdue grace=%s)",
        settings.c9_sweep_interval_seconds,
        {k.value: str(v) for k, v in policy.windows.items()},
        policy.overdue_grace,
    )
    engine = create_engine(settings.database_url)
    try:
        await run_sweeper(
            create_session_factory(engine),
            interval_seconds=settings.c9_sweep_interval_seconds,
            policy=policy,
        )
    finally:
        await engine.dispose()


async def run_temporal_mode() -> None:
    from temporalio.client import Client
    from temporalio.worker import Worker
    from temporalio.worker.workflow_sandbox import (
        SandboxedWorkflowRunner,
        SandboxRestrictions,
    )
    from wellbe_c9_continuity.temporal.activities import fire_timer_activity
    from wellbe_c9_continuity.temporal.workflows import PendingItemWorkflow

    logger.info(
        "Connecting continuity worker to Temporal at %s (namespace=%s, queue=%s)",
        settings.temporal_host,
        settings.temporal_namespace,
        TASK_QUEUE,
    )
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)

    runner = SandboxedWorkflowRunner(
        restrictions=SandboxRestrictions.default.with_passthrough_modules(
            *_PASSTHROUGH_MODULES
        )
    )
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[PendingItemWorkflow],
        activities=[fire_timer_activity],
        workflow_runner=runner,
    )
    logger.info("Continuity worker started on task queue %s", TASK_QUEUE)
    await worker.run()


async def main() -> None:
    if settings.c9_timer_mechanism == "temporal":
        await run_temporal_mode()
    else:
        await run_sweeper_mode()


if __name__ == "__main__":
    asyncio.run(main())
