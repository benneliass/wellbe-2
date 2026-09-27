"""C9 due/overdue sweeper: the homeserver timer mechanism for in-app reminders.

Periodically advances pending items along ``scheduled -> due -> overdue``:

- ``scheduled`` items whose ``due_at`` has passed fire the due phase
  (``ContinuityService.advance_due_item``: ``fire_timer`` + epoch bump) and emit
  ``c9.pending_item.due``;
- ``due`` items still open ``overdue_grace`` after ``due_at`` fire the overdue
  phase (``fire_overdue_timer``) and emit ``c9.pending_item.overdue``.

Each item is claimed ``FOR UPDATE SKIP LOCKED`` and fired in its own transaction,
so one bad row cannot stall the batch and concurrent sweepers never double-fire.
The sweeper never requests a C7 thread transition: these are reminders, not
safety-bearing closure timers (see docs/decisions/c9-due-reminders-sweeper.md).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from wellbe_contracts.c9_continuity import PendingItemStatus, TimerActionType
from wellbe_db import AsyncSessionFactory

from wellbe_c9_continuity.policy import DuePolicy, default_policy
from wellbe_c9_continuity.repository import ContinuityRepository
from wellbe_c9_continuity.service import ContinuityService

logger = logging.getLogger("wellbe.c9.sweeper")


@dataclass
class SweepResult:
    due: int = 0
    overdue: int = 0
    stale: int = 0

    @property
    def total(self) -> int:
        return self.due + self.overdue


async def sweep_once(
    session_factory: AsyncSessionFactory,
    *,
    now: datetime | None = None,
    policy: DuePolicy | None = None,
    batch_size: int = 200,
) -> SweepResult:
    """Advance every item whose due/overdue moment is at or before ``now``."""
    now = now or datetime.now(UTC)
    policy = policy or default_policy()
    result = SweepResult()

    phases = (
        (PendingItemStatus.SCHEDULED, now, "due"),
        (PendingItemStatus.DUE, now - policy.overdue_grace, "overdue"),
    )
    for status, fire_before, phase in phases:
        for _ in range(batch_size):
            async with session_factory() as session, session.begin():
                row = await ContinuityRepository(session).claim_next_timer(
                    status=status, fire_before=fire_before
                )
                if row is None:
                    break
                svc = ContinuityService(session, policy)
                if phase == "due":
                    fired = await svc.advance_due_item(
                        pending_item_id=row.pending_item_id, timer_epoch=row.timer_epoch
                    )
                else:
                    fired = await svc.fire_overdue_timer(
                        pending_item_id=row.pending_item_id,
                        timer_epoch=row.timer_epoch,
                        correlation_id="c9-sweeper",
                        trace_id="c9-sweeper",
                    )
            if fired.action != TimerActionType.FIRED:
                # Cannot happen under the claim lock; stop rather than re-claim it.
                result.stale += 1
                break
            if phase == "due":
                result.due += 1
            else:
                result.overdue += 1
    return result


async def run_sweeper(
    session_factory: AsyncSessionFactory,
    *,
    interval_seconds: float = 60.0,
    policy: DuePolicy | None = None,
) -> None:
    """Sweep forever; errors are logged and retried on the next tick."""
    while True:
        try:
            swept = await sweep_once(session_factory, policy=policy)
            if swept.total or swept.stale:
                logger.info(
                    "c9 sweep: %d due, %d overdue, %d stale no-op",
                    swept.due,
                    swept.overdue,
                    swept.stale,
                )
        except Exception:
            logger.exception("c9 sweep failed; retrying next tick")
        await asyncio.sleep(interval_seconds)
