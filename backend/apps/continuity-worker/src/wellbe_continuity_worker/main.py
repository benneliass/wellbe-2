"""C9 Continuity Worker.

Runs the Temporal worker for the C9 ``c9-continuity`` task queue: it hosts the
per-pending-item durable-timer workflow and the timer-fire activity. The activity
is where all non-deterministic work (DB reads, C7 ``transition_thread`` calls)
happens; the workflow only owns the durable timer and reschedule/cancel signals.

Durability guarantee: because the timer lives in Temporal (backed by Postgres),
a pending follow-up survives both worker restarts and Temporal service restarts.
"""

from __future__ import annotations

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)
from wellbe_c9_continuity.temporal.activities import fire_timer_activity
from wellbe_c9_continuity.temporal.workflows import PendingItemWorkflow
from wellbe_contracts.c9_continuity import TASK_QUEUE

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

logging.basicConfig(level=os.environ.get("WELLBE_LOG_LEVEL", "INFO"))
logger = logging.getLogger("wellbe.continuity_worker")


async def main() -> None:
    temporal_host = os.environ.get("WELLBE_TEMPORAL_HOST", "temporal:7233")
    namespace = os.environ.get("WELLBE_TEMPORAL_NAMESPACE", "default")
    logger.info(
        "Connecting continuity worker to Temporal at %s (namespace=%s, queue=%s)",
        temporal_host,
        namespace,
        TASK_QUEUE,
    )
    client = await Client.connect(temporal_host, namespace=namespace)

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


if __name__ == "__main__":
    asyncio.run(main())
