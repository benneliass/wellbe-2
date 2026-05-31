from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime, EventId, PatientId

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

EVIDENCE_LINKED = "evidence.linked"
EVIDENCE_CORRECTED = "evidence.corrected"
PROVENANCE_ORPHAN_REJECTED = "provenance.orphan_rejected"

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

EvidenceLinkId = Annotated[UUID, Field(description="Unique identifier for an EvidenceLink")]
CorrectionId = Annotated[UUID, Field(description="Unique identifier for a C11 correction")]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvidenceLinkType(str, Enum):
    """Relationship between a derived object and its raw source event.

    primary       — the main evidence supporting the derived claim
    corroborating — additional evidence reinforcing the claim (diminishing weight)
    contradicting — evidence that opposes the claim (negative weight in scoring)
    contextual    — background context that influenced extraction, not the direct source
    """

    PRIMARY = "primary"
    CORROBORATING = "corroborating"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"


class EvidenceSourceType(str, Enum):
    """The type of derived object the evidence link points FROM."""

    EXTRACTED_FACT = "extracted_fact"
    HEALTH_SIGNAL = "health_signal"
    MEMORY_ENTRY = "memory_entry"
    AI_SUMMARY = "ai_summary"
    AI_RESPONSE = "ai_response"


class ConfidenceBasis(str, Enum):
    EXTRACTION_MODEL = "extraction_model"
    USER_CONFIRMATION = "user_confirmation"
    CLINICAL_SOURCE = "clinical_source"
    SYSTEM_COMPUTED = "system_computed"
    CORRECTION_SERVICE = "correction_service"


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """Reference passed to the C5 write gate alongside a derived object.

    Every derived object write must include at least one EvidenceRef.
    The C5 service validates all raw_context_event_ids exist in C2 before
    writing the derived object and its evidence links atomically.
    """

    raw_context_event_id: EventId
    link_type: EvidenceLinkType
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_basis: ConfidenceBasis = ConfidenceBasis.EXTRACTION_MODEL
    relevance_span_start: Optional[int] = None
    relevance_span_end: Optional[int] = None


class EvidenceLink(BaseModel):
    """A single row in the evidence_links join table.

    One row per (derived object, raw source event) pair. A fact derived from
    multiple raw events has multiple EvidenceLink rows — one per source.
    """

    model_config = ConfigDict(from_attributes=True)

    id: EvidenceLinkId
    source_type: EvidenceSourceType
    source_id: UUID

    raw_context_event_id: EventId
    patient_id: PatientId

    link_type: EvidenceLinkType
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_basis: ConfidenceBasis

    relevance_span_start: Optional[int] = None
    relevance_span_end: Optional[int] = None

    linked_at: AwareDatetime
    linked_by: str  # "user" | "system" | "pipeline" | "correction_service"
    correction_id: Optional[CorrectionId] = None

    schema_version: int = 1
    created_at: AwareDatetime


# ---------------------------------------------------------------------------
# Event payloads emitted on the outbox
# ---------------------------------------------------------------------------


class EvidenceLinkedPayload(BaseModel):
    """Payload for the evidence.linked outbox event consumed by C6 scoring workers.

    C6 uses confidence and link_type from this payload directly — it does not
    call C5 synchronously to retrieve these values.
    """

    evidence_link_id: EvidenceLinkId
    source_type: EvidenceSourceType
    source_id: UUID
    raw_context_event_id: EventId
    patient_id: PatientId
    link_type: EvidenceLinkType
    confidence: float
    confidence_basis: ConfidenceBasis
    correlation_id: str
    trace_id: str


class EvidenceCorrectedPayload(BaseModel):
    """Payload for the evidence.corrected outbox event — emitted when C11
    creates a new EvidenceLink with correction_id set."""

    evidence_link_id: EvidenceLinkId
    correction_id: CorrectionId
    source_type: EvidenceSourceType
    source_id: UUID
    patient_id: PatientId
    old_link_type: Optional[EvidenceLinkType] = None
    new_link_type: EvidenceLinkType
    correlation_id: str
    trace_id: str


class ProvenanceOrphanRejectedPayload(BaseModel):
    """Payload for the provenance.orphan_rejected event — emitted when the C5
    write gate rejects a derived object that has no valid evidence refs."""

    source_type: EvidenceSourceType
    source_id: UUID
    patient_id: PatientId
    missing_raw_context_event_ids: list[EventId]
    rejection_reason: str
    correlation_id: str
    trace_id: str


__all__ = [
    # Event type constants
    "EVIDENCE_LINKED",
    "EVIDENCE_CORRECTED",
    "PROVENANCE_ORPHAN_REJECTED",
    # Type aliases
    "CorrectionId",
    "EvidenceLinkId",
    # Enums
    "ConfidenceBasis",
    "EvidenceLinkType",
    "EvidenceSourceType",
    # Core types
    "EvidenceLink",
    "EvidenceRef",
    # Event payloads
    "EvidenceCorrectedPayload",
    "EvidenceLinkedPayload",
    "ProvenanceOrphanRejectedPayload",
]
