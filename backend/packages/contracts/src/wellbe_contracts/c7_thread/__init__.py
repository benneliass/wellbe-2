"""C7 Health Thread Engine contracts.

The Health Thread is the central product object (C7). These contracts define the
lifecycle status enum, the structurally-allowed transition graph, the
``transition_thread`` command inputs/result, and the ``thread.state_changed``
outbox event payload consumed by C8, C9, C12, and C13.

Authoritative decision: docs/decisions/health-thread-state-machine-enforcement.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

THREAD_STATE_CHANGED = "thread.state_changed"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HealthThreadStatus(StrEnum):
    """Lifecycle states for a Health Thread.

    Defined in docs/system-design/health_thread_state_machine.md.
    """

    DRAFT = "draft"
    ACTIVE_UNRESOLVED = "active_unresolved"
    WAITING_FOR_RESULT = "waiting_for_result"
    REFERRED = "referred"
    WATCHFUL_WAITING = "watchful_waiting"
    ESCALATED = "escalated"
    EXPLAINED = "explained"
    CHRONIC_MONITORING = "chronic_monitoring"
    CLOSED = "closed"
    REOPENED = "reopened"
    ARCHIVED = "archived"


class ThreadActorType(StrEnum):
    """Who initiated a transition."""

    USER = "user"
    CLINICIAN = "clinician"
    SYSTEM = "system"
    WORKFLOW = "workflow"
    ADMIN = "admin"


# ---------------------------------------------------------------------------
# Structurally-allowed transition graph (edge validity)
#
# This is the single source of truth for *edge* validity. Contextual safety
# guards (closure-on-one-normal-test, persistent symptoms, AI final diagnosis)
# are evaluated separately by the C7 domain layer. The DB seeds
# ``thread.health_thread_allowed_transitions`` from this same graph and a
# trigger enforces it as defence-in-depth.
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[HealthThreadStatus, frozenset[HealthThreadStatus]] = {
    HealthThreadStatus.DRAFT: frozenset(
        {HealthThreadStatus.ACTIVE_UNRESOLVED, HealthThreadStatus.ARCHIVED}
    ),
    HealthThreadStatus.ACTIVE_UNRESOLVED: frozenset(
        {
            HealthThreadStatus.WAITING_FOR_RESULT,
            HealthThreadStatus.REFERRED,
            HealthThreadStatus.WATCHFUL_WAITING,
            HealthThreadStatus.ESCALATED,
            HealthThreadStatus.EXPLAINED,
            HealthThreadStatus.CHRONIC_MONITORING,
        }
    ),
    HealthThreadStatus.WAITING_FOR_RESULT: frozenset(
        {
            HealthThreadStatus.ACTIVE_UNRESOLVED,
            HealthThreadStatus.EXPLAINED,
            HealthThreadStatus.ESCALATED,
            HealthThreadStatus.CHRONIC_MONITORING,
        }
    ),
    HealthThreadStatus.REFERRED: frozenset(
        {
            HealthThreadStatus.ACTIVE_UNRESOLVED,
            HealthThreadStatus.WAITING_FOR_RESULT,
            HealthThreadStatus.EXPLAINED,
            HealthThreadStatus.CHRONIC_MONITORING,
        }
    ),
    HealthThreadStatus.WATCHFUL_WAITING: frozenset(
        {
            HealthThreadStatus.ACTIVE_UNRESOLVED,
            HealthThreadStatus.ESCALATED,
            HealthThreadStatus.EXPLAINED,
            HealthThreadStatus.CHRONIC_MONITORING,
        }
    ),
    HealthThreadStatus.ESCALATED: frozenset(
        {
            HealthThreadStatus.ACTIVE_UNRESOLVED,
            HealthThreadStatus.WAITING_FOR_RESULT,
            HealthThreadStatus.REFERRED,
            HealthThreadStatus.EXPLAINED,
        }
    ),
    HealthThreadStatus.EXPLAINED: frozenset(
        {
            HealthThreadStatus.CLOSED,
            HealthThreadStatus.CHRONIC_MONITORING,
            HealthThreadStatus.ACTIVE_UNRESOLVED,
        }
    ),
    HealthThreadStatus.CHRONIC_MONITORING: frozenset(
        {
            HealthThreadStatus.ACTIVE_UNRESOLVED,
            HealthThreadStatus.ESCALATED,
            HealthThreadStatus.CLOSED,
        }
    ),
    HealthThreadStatus.CLOSED: frozenset({HealthThreadStatus.REOPENED}),
    HealthThreadStatus.REOPENED: frozenset({HealthThreadStatus.ACTIVE_UNRESOLVED}),
    HealthThreadStatus.ARCHIVED: frozenset(),
}


def is_edge_allowed(
    from_status: HealthThreadStatus, to_status: HealthThreadStatus
) -> bool:
    """Return True if ``from_status -> to_status`` is a structurally valid edge."""
    return to_status in ALLOWED_TRANSITIONS.get(from_status, frozenset())


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class ThreadActor(BaseModel):
    """The actor that initiated a transition."""

    type: ThreadActorType
    id: UUID | None = None


class ThreadEvidenceRef(BaseModel):
    """A lightweight reference to evidence backing a transition."""

    type: str
    id: UUID


class TransitionGuardContext(BaseModel):
    """Contextual inputs the C7 safety guards evaluate before a transition.

    These encode the closure-safety rules from the decision record:
    a thread cannot be closed on a single normal test, cannot be closed while
    symptoms persist, and no transition may assert a final AI diagnosis.
    """

    closure_basis_single_normal_test: bool = False
    symptoms_persist: bool = False
    ai_final_diagnosis_claim: bool = False


class HealthThread(BaseModel):
    """Read model for a Health Thread (current state)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: PatientId
    title: str
    status: HealthThreadStatus
    status_version: int
    status_changed_at: AwareDatetime
    created_at: AwareDatetime


# Statuses from which a thread is considered "resolved enough" that a linked
# investigation may be closed. A thread in any other status means the concern is
# still open, so the investigation must use handed_off / monitoring instead.
RESOLVED_THREAD_STATUSES: frozenset[HealthThreadStatus] = frozenset(
    {
        HealthThreadStatus.EXPLAINED,
        HealthThreadStatus.CHRONIC_MONITORING,
        HealthThreadStatus.CLOSED,
        HealthThreadStatus.ARCHIVED,
    }
)


class ThreadClosureSnapshot(BaseModel):
    """Authoritative C7 view of whether a thread permits closure.

    C7 is the sole owner of this judgement. C14 consumes it and never recomputes
    symptom-resolution or single-normal-test sufficiency itself.
    """

    thread_id: UUID
    status: HealthThreadStatus
    status_version: int
    is_resolved: bool


class ThreadTransitionResult(BaseModel):
    """Result of a ``transition_thread`` command."""

    thread_id: UUID
    from_status: HealthThreadStatus
    to_status: HealthThreadStatus
    status_version: int
    transition_seq: int
    event_id: UUID | None = None
    safety_flags: list[str] = Field(default_factory=list)
    idempotent_replay: bool = False


# ---------------------------------------------------------------------------
# Event payload emitted on the outbox
# ---------------------------------------------------------------------------


class ThreadStateChangedPayload(BaseModel):
    """Payload for the ``thread.state_changed`` outbox event.

    Consumers order by ``(thread_id, transition_seq)`` and deduplicate on
    ``event_id``. Schema version 1.
    """

    schema_version: int = 1
    thread_id: UUID
    patient_id: PatientId
    from_status: HealthThreadStatus
    to_status: HealthThreadStatus
    transition_seq: int
    actor: ThreadActor
    reason_code: str
    idempotency_key: str
    correlation_id: str
    trace_id: str
    evidence_refs: list[ThreadEvidenceRef] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


__all__ = [
    # Event type constants
    "THREAD_STATE_CHANGED",
    # Enums
    "HealthThreadStatus",
    "ThreadActorType",
    # Transition graph
    "ALLOWED_TRANSITIONS",
    "is_edge_allowed",
    # Core types
    "ThreadActor",
    "ThreadEvidenceRef",
    "TransitionGuardContext",
    "HealthThread",
    "ThreadTransitionResult",
    "ThreadClosureSnapshot",
    "RESOLVED_THREAD_STATUSES",
    # Event payloads
    "ThreadStateChangedPayload",
]
