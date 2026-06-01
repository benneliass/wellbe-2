"""C14 Investigation contracts.

The Investigation is the engine of the "Investigate" loop step. It is a
first-class aggregate (its own lifecycle) with a many-to-many link to C7 Health
Threads. C7 stays authoritative for thread closure; C14 owns investigation
status and may only close when C7's ThreadClosureSnapshot permits.

Authoritative decision: docs/decisions/investigation-object-and-thread-coupling.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event type constants (v1)
# ---------------------------------------------------------------------------

INVESTIGATION_CREATED = "investigation.created.v1"
INVESTIGATION_LINKED_TO_THREAD = "investigation.linked_to_thread.v1"
INVESTIGATION_STATE_CHANGED = "investigation.state_changed.v1"
INVESTIGATION_SAFETY_FLAG_RAISED = "investigation.safety_flag_raised.v1"
INVESTIGATION_CLOSED = "investigation.closed.v1"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InvestigationStatus(StrEnum):
    """Workflow status (NEVER a clinical conclusion — constraint G1)."""

    OPEN = "open"
    MONITORING = "monitoring"
    WAITING_FOR_DATA = "waiting_for_data"
    READY_FOR_VISIT = "ready_for_visit"
    HANDED_OFF = "handed_off"
    CLOSED = "closed"


class InvestigationOwnerType(StrEnum):
    USER = "user"
    CAREGIVER = "caregiver"
    SYSTEM = "system"


class ThreadRelationship(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    RELATED = "related"


class ParticipantStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SafetyFlagSeverity(StrEnum):
    INFO = "info"
    ATTENTION = "attention"
    URGENT = "urgent"


# ---------------------------------------------------------------------------
# Status transition matrix (workflow-only). Closure (-> CLOSED) is additionally
# gated by the InvestigationThreadCouplingPolicy against C7 snapshots.
# ---------------------------------------------------------------------------

ALLOWED_INVESTIGATION_TRANSITIONS: dict[
    InvestigationStatus, frozenset[InvestigationStatus]
] = {
    InvestigationStatus.OPEN: frozenset(
        {
            InvestigationStatus.MONITORING,
            InvestigationStatus.WAITING_FOR_DATA,
            InvestigationStatus.READY_FOR_VISIT,
            InvestigationStatus.HANDED_OFF,
            InvestigationStatus.CLOSED,
        }
    ),
    InvestigationStatus.MONITORING: frozenset(
        {
            InvestigationStatus.OPEN,
            InvestigationStatus.WAITING_FOR_DATA,
            InvestigationStatus.READY_FOR_VISIT,
            InvestigationStatus.HANDED_OFF,
            InvestigationStatus.CLOSED,
        }
    ),
    InvestigationStatus.WAITING_FOR_DATA: frozenset(
        {
            InvestigationStatus.OPEN,
            InvestigationStatus.MONITORING,
            InvestigationStatus.READY_FOR_VISIT,
            InvestigationStatus.HANDED_OFF,
            InvestigationStatus.CLOSED,
        }
    ),
    InvestigationStatus.READY_FOR_VISIT: frozenset(
        {
            InvestigationStatus.OPEN,
            InvestigationStatus.MONITORING,
            InvestigationStatus.WAITING_FOR_DATA,
            InvestigationStatus.HANDED_OFF,
            InvestigationStatus.CLOSED,
        }
    ),
    InvestigationStatus.HANDED_OFF: frozenset(
        {InvestigationStatus.MONITORING, InvestigationStatus.CLOSED}
    ),
    InvestigationStatus.CLOSED: frozenset({InvestigationStatus.OPEN}),
}


def is_investigation_edge_allowed(
    from_status: InvestigationStatus, to_status: InvestigationStatus
) -> bool:
    return to_status in ALLOWED_INVESTIGATION_TRANSITIONS.get(
        from_status, frozenset()
    )


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class InvestigationSafetyFlag(BaseModel):
    """Structured safety flag raised on an investigation.

    C14 raises flags; C7 decides whether to escalate the thread. Workflow-only,
    never a diagnosis (G1).
    """

    flag_type: str
    severity: SafetyFlagSeverity
    source: str
    requires_thread_state: str | None = None
    message_key: str


class Investigation(BaseModel):
    """Read model for an Investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: PatientId
    primary_question: str
    status: InvestigationStatus
    status_version: int
    owner_type: InvestigationOwnerType
    safety_flags: list[InvestigationSafetyFlag] = Field(default_factory=list)
    projection_node_id: UUID | None = None
    created_at: AwareDatetime
    status_changed_at: AwareDatetime


class CloseEvaluation(BaseModel):
    """Result of the coupling policy's close evaluation."""

    allowed: bool
    unmet_thread_ids: list[UUID] = Field(default_factory=list)
    reason: str | None = None


class InvestigationTransitionResult(BaseModel):
    investigation_id: UUID
    from_status: InvestigationStatus
    to_status: InvestigationStatus
    status_version: int
    event_id: UUID | None = None
    idempotent_replay: bool = False


# ---------------------------------------------------------------------------
# Event payloads
# ---------------------------------------------------------------------------


class InvestigationCreatedPayload(BaseModel):
    schema_version: int = 1
    investigation_id: UUID
    patient_id: PatientId
    primary_question: str
    owner_type: InvestigationOwnerType
    projection_node_id: UUID | None = None
    correlation_id: str
    trace_id: str


class InvestigationLinkedToThreadPayload(BaseModel):
    schema_version: int = 1
    investigation_id: UUID
    patient_id: PatientId
    thread_id: UUID
    relationship: ThreadRelationship
    correlation_id: str
    trace_id: str


class InvestigationStateChangedPayload(BaseModel):
    schema_version: int = 1
    investigation_id: UUID
    patient_id: PatientId
    from_status: InvestigationStatus
    to_status: InvestigationStatus
    status_version: int
    reason_code: str
    idempotency_key: str
    correlation_id: str
    trace_id: str


class InvestigationSafetyFlagRaisedPayload(BaseModel):
    schema_version: int = 1
    investigation_id: UUID
    patient_id: PatientId
    flag: InvestigationSafetyFlag
    correlation_id: str
    trace_id: str


class InvestigationClosedPayload(BaseModel):
    schema_version: int = 1
    investigation_id: UUID
    patient_id: PatientId
    linked_thread_ids: list[UUID] = Field(default_factory=list)
    correlation_id: str
    trace_id: str


__all__ = [
    # Event types
    "INVESTIGATION_CREATED",
    "INVESTIGATION_LINKED_TO_THREAD",
    "INVESTIGATION_STATE_CHANGED",
    "INVESTIGATION_SAFETY_FLAG_RAISED",
    "INVESTIGATION_CLOSED",
    # Enums
    "InvestigationStatus",
    "InvestigationOwnerType",
    "ThreadRelationship",
    "ParticipantStatus",
    "SafetyFlagSeverity",
    # Transition graph
    "ALLOWED_INVESTIGATION_TRANSITIONS",
    "is_investigation_edge_allowed",
    # Core types
    "InvestigationSafetyFlag",
    "Investigation",
    "CloseEvaluation",
    "InvestigationTransitionResult",
    # Event payloads
    "InvestigationCreatedPayload",
    "InvestigationLinkedToThreadPayload",
    "InvestigationStateChangedPayload",
    "InvestigationSafetyFlagRaisedPayload",
    "InvestigationClosedPayload",
]
