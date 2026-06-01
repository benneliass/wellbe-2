"""C15 Theory contracts.

The Theory object is the safe vehicle for user/clinician hypotheses — the most
diagnosis-adjacent surface in the product. Status describes what *personal-data*
review found; safety_level tells C10 what to do with any output. Neither is ever
a diagnosis (G1). External sources are context only, never personal evidence (G2).

Authoritative decision: docs/decisions/theory-object-evaluation-and-safety.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event type constants (v1)
# ---------------------------------------------------------------------------

THEORY_CREATED = "theory.created.v1"
THEORY_EVALUATED = "theory.evaluated.v1"
THEORY_SAFETY_LEVEL_CHANGED = "theory.safety_level_changed.v1"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TheoryStatus(StrEnum):
    """What personal-data review found. NEVER a diagnosis (no confirmed/ruled_out)."""

    UNREVIEWED = "unreviewed"
    NEEDS_MORE_DATA = "needs_more_data"
    PARTIALLY_SUPPORTED = "partially_supported"
    NOT_SUPPORTED_BY_CURRENT_DATA = "not_supported_by_current_data"
    CONTRADICTED_BY_CURRENT_DATA = "contradicted_by_current_data"
    DISCUSS_WITH_CLINICIAN = "discuss_with_clinician"
    CLINICIAN_REVIEWED = "clinician_reviewed"


class TheorySafetyLevel(StrEnum):
    """What C10 should do with any output derived from this theory."""

    LOW = "low"
    NEEDS_CLINICIAN_CONTEXT = "needs_clinician_context"
    URGENT_SYMPTOM_PRESENT = "urgent_symptom_present"
    BLOCKED_DUE_TO_DIAGNOSTIC_CLAIM = "blocked_due_to_diagnostic_claim"


class TheoryType(StrEnum):
    SYMPTOM_CAUSE = "symptom_cause"
    TREATMENT_EFFECT = "treatment_effect"
    TRIGGER = "trigger"
    PATTERN = "pattern"
    OTHER = "other"


class EvidenceDirection(StrEnum):
    """Direction of a *personal* evidence edge to the Theory node."""

    FOR = "for"
    AGAINST = "against"


class ContextDirection(StrEnum):
    """External context only — never asserts truth about the user."""

    SUPPORTING_PLAUSIBILITY = "supporting_plausibility"
    CONTRADICTING_PLAUSIBILITY = "contradicting_plausibility"
    NEUTRAL = "neutral"


# ---------------------------------------------------------------------------
# Status transition matrix
# ---------------------------------------------------------------------------

ALLOWED_THEORY_TRANSITIONS: dict[TheoryStatus, frozenset[TheoryStatus]] = {
    TheoryStatus.UNREVIEWED: frozenset(
        {
            TheoryStatus.NEEDS_MORE_DATA,
            TheoryStatus.PARTIALLY_SUPPORTED,
            TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA,
            TheoryStatus.CONTRADICTED_BY_CURRENT_DATA,
            TheoryStatus.DISCUSS_WITH_CLINICIAN,
        }
    ),
    TheoryStatus.NEEDS_MORE_DATA: frozenset(
        {
            TheoryStatus.PARTIALLY_SUPPORTED,
            TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA,
            TheoryStatus.CONTRADICTED_BY_CURRENT_DATA,
            TheoryStatus.DISCUSS_WITH_CLINICIAN,
        }
    ),
    TheoryStatus.PARTIALLY_SUPPORTED: frozenset(
        {
            TheoryStatus.NEEDS_MORE_DATA,
            TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA,
            TheoryStatus.CONTRADICTED_BY_CURRENT_DATA,
            TheoryStatus.DISCUSS_WITH_CLINICIAN,
            TheoryStatus.CLINICIAN_REVIEWED,
        }
    ),
    TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA: frozenset(
        {
            TheoryStatus.NEEDS_MORE_DATA,
            TheoryStatus.PARTIALLY_SUPPORTED,
            TheoryStatus.DISCUSS_WITH_CLINICIAN,
            TheoryStatus.CLINICIAN_REVIEWED,
        }
    ),
    TheoryStatus.CONTRADICTED_BY_CURRENT_DATA: frozenset(
        {
            TheoryStatus.NEEDS_MORE_DATA,
            TheoryStatus.DISCUSS_WITH_CLINICIAN,
            TheoryStatus.CLINICIAN_REVIEWED,
        }
    ),
    TheoryStatus.DISCUSS_WITH_CLINICIAN: frozenset(
        {
            TheoryStatus.CLINICIAN_REVIEWED,
            TheoryStatus.NEEDS_MORE_DATA,
            TheoryStatus.PARTIALLY_SUPPORTED,
            TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA,
            TheoryStatus.CONTRADICTED_BY_CURRENT_DATA,
        }
    ),
    TheoryStatus.CLINICIAN_REVIEWED: frozenset(
        {
            TheoryStatus.NEEDS_MORE_DATA,
            TheoryStatus.DISCUSS_WITH_CLINICIAN,
        }
    ),
}


def is_theory_edge_allowed(from_status: TheoryStatus, to_status: TheoryStatus) -> bool:
    if from_status == to_status:
        return True  # idempotent re-evaluation to the same status is allowed
    return to_status in ALLOWED_THEORY_TRANSITIONS.get(from_status, frozenset())


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class TheoryTextNormalization(BaseModel):
    """Result of normalizing free-text into a safe, non-diagnostic question."""

    blocked: bool
    normalized_question: str | None = None
    safety_level: TheorySafetyLevel
    blocked_reason: str | None = None


class PersonalEvidenceRef(BaseModel):
    """A personal fact backing a theory. Must carry C5 provenance (G3)."""

    node_id: UUID
    direction: EvidenceDirection
    evidence_link_id: UUID


class ExternalContextRef(BaseModel):
    """External source attached as context only (G2)."""

    external_source_id: UUID
    external_claim_id: UUID | None = None
    relevance_link_id: UUID
    context_direction: ContextDirection


class Theory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    patient_id: PatientId
    theory_text: str
    normalized_question: str | None
    theory_type: TheoryType
    status: TheoryStatus
    safety_level: TheorySafetyLevel
    linked_investigation_id: UUID | None = None
    latest_evaluation_id: UUID | None = None
    projection_node_id: UUID | None = None
    created_at: AwareDatetime


class TheoryEvaluationResult(BaseModel):
    theory_id: UUID
    evaluation_id: UUID
    evaluation_version: int
    status: TheoryStatus
    safety_level: TheorySafetyLevel
    evidence_for_count: int
    evidence_against_count: int
    c10_decision: str
    event_id: UUID | None = None


# ---------------------------------------------------------------------------
# Event payloads
# ---------------------------------------------------------------------------


class TheoryCreatedPayload(BaseModel):
    schema_version: int = 1
    theory_id: UUID
    patient_id: PatientId
    theory_type: TheoryType
    status: TheoryStatus
    safety_level: TheorySafetyLevel
    normalized_question: str | None = None
    blocked: bool = False
    projection_node_id: UUID | None = None
    correlation_id: str
    trace_id: str


class TheoryEvaluatedPayload(BaseModel):
    schema_version: int = 1
    theory_id: UUID
    patient_id: PatientId
    evaluation_id: UUID
    evaluation_version: int
    status: TheoryStatus
    safety_level: TheorySafetyLevel
    c10_decision: str
    correlation_id: str
    trace_id: str


class TheorySafetyLevelChangedPayload(BaseModel):
    schema_version: int = 1
    theory_id: UUID
    patient_id: PatientId
    from_safety_level: TheorySafetyLevel
    to_safety_level: TheorySafetyLevel
    correlation_id: str
    trace_id: str


__all__ = [
    "THEORY_CREATED",
    "THEORY_EVALUATED",
    "THEORY_SAFETY_LEVEL_CHANGED",
    "TheoryStatus",
    "TheorySafetyLevel",
    "TheoryType",
    "EvidenceDirection",
    "ContextDirection",
    "ALLOWED_THEORY_TRANSITIONS",
    "is_theory_edge_allowed",
    "TheoryTextNormalization",
    "PersonalEvidenceRef",
    "ExternalContextRef",
    "Theory",
    "TheoryEvaluationResult",
    "TheoryCreatedPayload",
    "TheoryEvaluatedPayload",
    "TheorySafetyLevelChangedPayload",
]
