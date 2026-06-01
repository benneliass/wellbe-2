"""C9 Continuity & Closure Engine contracts.

C9 owns durable continuity: a Postgres pending-item ledger (operational source of
truth for follow-ups/referrals/results — never for clinical facts or thread state)
plus one Temporal workflow per active pending item. C9 consumes C7
``thread.state_changed`` (dedupe by event_id, order by (thread_id, transition_seq))
and may request a thread transition ONLY through C7 ``transition_thread`` with
``expected_version``, an idempotency key, evidence refs, and guard metadata. A C7
stale/guard rejection is a terminal no-op for that timer epoch.

The normal-test safety net is represented at two layers: a C9 pending item that
blocks any C9 closure request, and C7 guard context on every C9 transition request.

Authoritative decision: docs/decisions/continuity-pending-ledger-durable-timers.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event constants (lower-case dotted, per decision)
# ---------------------------------------------------------------------------

C9_PENDING_ITEM_CREATED = "c9.pending_item.created"
C9_PENDING_ITEM_UPDATED = "c9.pending_item.updated"
C9_PENDING_ITEM_DUE = "c9.pending_item.due"
C9_PENDING_ITEM_OVERDUE = "c9.pending_item.overdue"
C9_PENDING_ITEM_RESOLVED = "c9.pending_item.resolved"
C9_PENDING_ITEM_CANCELLED = "c9.pending_item.cancelled"
C9_REFERRAL_STATUS_CHANGED = "c9.referral.status_changed"
C9_RESULT_RECEIVED = "c9.result.received"
C9_TIMER_NO_OP_STALE = "c9.timer.no_op_stale"
C9_TIMER_NO_OP_C7_REJECTED = "c9.timer.no_op_c7_rejected"
C9_THREAD_TRANSITION_ACCEPTED = "c9.thread_transition.accepted"

TASK_QUEUE = "c9-continuity"


def workflow_id(pending_item_id: UUID) -> str:
    """Deterministic per-item Temporal workflow id."""
    return f"c9-pending-{pending_item_id}"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PendingItemType(StrEnum):
    RESULT_PENDING = "result_pending"
    REFERRAL_PENDING = "referral_pending"
    FOLLOW_UP_DUE = "follow_up_due"
    REPEAT_TEST_DUE = "repeat_test_due"
    POST_VISIT_PLAN_CHECK = "post_visit_plan_check"
    NORMAL_TEST_SAFETY_NET = "normal_test_safety_net"
    USER_NEXT_STEP = "user_next_step"
    CARE_TEAM_NEXT_STEP = "care_team_next_step"


class PendingItemStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    WAITING_EXTERNAL = "waiting_external"
    SCHEDULED = "scheduled"
    DUE = "due"
    OVERDUE = "overdue"
    IN_PROGRESS = "in_progress"
    RESULT_RECEIVED = "result_received"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    NO_DUE_DATE = "no_due_date"


class DuePrecision(StrEnum):
    UNKNOWN = "unknown"
    DATE = "date"
    DATETIME = "datetime"
    RELATIVE_POLICY = "relative_policy"


class SymptomsPersistState(StrEnum):
    UNKNOWN = "unknown"
    REPORTED_PERSISTENT = "reported_persistent"
    REPORTED_RESOLVED = "reported_resolved"
    NOT_APPLICABLE = "not_applicable"


class TimerActionType(StrEnum):
    STARTED = "started"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    FIRED = "fired"
    C7_TRANSITION_REQUESTED = "c7_transition_requested"
    C7_TRANSITION_ACCEPTED = "c7_transition_accepted"
    NO_OP_STALE = "no_op_stale"
    NO_OP_C7_REJECTED = "no_op_c7_rejected"
    FAILED_TRANSIENT = "failed_transient"


# Statuses that no longer need an active timer.
TERMINAL_STATUSES = {
    PendingItemStatus.RESOLVED,
    PendingItemStatus.CANCELLED,
    PendingItemStatus.SUPERSEDED,
}

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class PendingItem(BaseModel):
    pending_item_id: UUID
    patient_id: PatientId
    primary_thread_id: UUID
    item_type: PendingItemType
    status: PendingItemStatus
    title: str
    due_at: AwareDatetime | None = None
    due_precision: DuePrecision = DuePrecision.UNKNOWN
    blocks_c9_closure_request: bool = False
    normal_test_safety_net: bool = False
    symptoms_persist_state: SymptomsPersistState = SymptomsPersistState.UNKNOWN
    timer_epoch: int = 0
    version: int = 1
    workflow_id: str | None = None
    source_ref: dict = Field(default_factory=dict)
    evidence_refs: list[dict] = Field(default_factory=list)


class TimerFireResult(BaseModel):
    pending_item_id: UUID
    timer_epoch: int
    action: TimerActionType
    c7_transition_id: UUID | None = None
    c7_rejection_code: str | None = None


__all__ = [
    "C9_PENDING_ITEM_CREATED",
    "C9_PENDING_ITEM_UPDATED",
    "C9_PENDING_ITEM_DUE",
    "C9_PENDING_ITEM_OVERDUE",
    "C9_PENDING_ITEM_RESOLVED",
    "C9_PENDING_ITEM_CANCELLED",
    "C9_REFERRAL_STATUS_CHANGED",
    "C9_RESULT_RECEIVED",
    "C9_TIMER_NO_OP_STALE",
    "C9_TIMER_NO_OP_C7_REJECTED",
    "C9_THREAD_TRANSITION_ACCEPTED",
    "TASK_QUEUE",
    "workflow_id",
    "PendingItemType",
    "PendingItemStatus",
    "DuePrecision",
    "SymptomsPersistState",
    "TimerActionType",
    "TERMINAL_STATUSES",
    "PendingItem",
    "TimerFireResult",
]
