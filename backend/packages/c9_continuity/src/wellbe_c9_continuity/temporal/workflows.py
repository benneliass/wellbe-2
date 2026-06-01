"""C9 per-item Temporal workflow: one workflow per active pending item.

Deterministic: it sleeps until the due time (a durable timer that survives worker
and Temporal restarts) then calls the ``c9_fire_timer`` activity. Reschedule and
cancel are delivered as signals carrying the item version + timer epoch so stale
signals are ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Only pure, dependency-free types are imported into the workflow module. The
# activity is invoked by name so the workflow sandbox never imports the activity
# module (which pulls in SQLAlchemy / DB code and breaks sandbox validation).
from wellbe_c9_continuity.temporal.types import (
    FIRE_TIMER_ACTIVITY,
    FireTimerInput,
    FireTimerOutput,
)


@dataclass
class PendingItemWorkflowInput:
    pending_item_id: str
    timer_epoch: int
    delay_seconds: int
    requested_target_status: str | None = None
    closure_basis_single_normal_test: bool = False
    symptoms_persist: bool = False


@dataclass
class ReconcileSignal:
    timer_epoch: int
    delay_seconds: int


@workflow.defn(name="C9PendingItemWorkflow")
class PendingItemWorkflow:
    def __init__(self) -> None:
        self._input: PendingItemWorkflowInput | None = None
        self._cancelled = False
        self._rescheduled = False

    @workflow.signal
    async def reconcile_timer(self, signal: ReconcileSignal) -> None:
        # A newer epoch supersedes the current wait; wake the run loop to re-arm
        # the durable timer with the new delay. Stale epochs are ignored here and,
        # as defence-in-depth, re-checked against the ledger inside the activity.
        if self._input is not None and signal.timer_epoch > self._input.timer_epoch:
            self._input.timer_epoch = signal.timer_epoch
            self._input.delay_seconds = signal.delay_seconds
            self._rescheduled = True

    @workflow.signal
    async def cancel_timer(self) -> None:
        self._cancelled = True

    @workflow.run
    async def run(self, wf_input: PendingItemWorkflowInput) -> FireTimerOutput | None:
        self._input = wf_input
        # Durable sleep until due. wait_condition raises TimeoutError when the timer
        # elapses without cancel/reschedule — that is the normal "due" path. A
        # reschedule re-arms the timer; a cancel exits without firing.
        while True:
            self._rescheduled = False
            try:
                await workflow.wait_condition(
                    lambda: self._cancelled or self._rescheduled,
                    timeout=timedelta(seconds=max(self._input.delay_seconds, 0)),
                )
            except TimeoutError:
                break  # due time reached
            if self._cancelled:
                return None
            # else: rescheduled — loop re-arms with the new delay

        return await workflow.execute_activity(
            FIRE_TIMER_ACTIVITY,
            FireTimerInput(
                pending_item_id=self._input.pending_item_id,
                timer_epoch=self._input.timer_epoch,
                requested_target_status=self._input.requested_target_status,
                closure_basis_single_normal_test=self._input.closure_basis_single_normal_test,
                symptoms_persist=self._input.symptoms_persist,
            ),
            result_type=FireTimerOutput,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )
