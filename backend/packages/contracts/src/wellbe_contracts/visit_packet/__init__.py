"""C13 Visit Packet contracts (WEL-30 / WEL-68).

Implements the approved decision docs/decisions/visit-packet-composition-gating.md:

- A **two-layer** packet: a patient-prep layer (questions/goals/observations,
  clearly patient-authored) and an optional source-backed summary layer.
- Every summary statement carries a **classification** and **source links**;
  the gate blocks ``new_ai_diagnosis``. Absence is explicit (never a silent
  omission that implies "none"); deselected statements are visibly marked,
  not dropped.
- Sharing is a **named-recipient, time-boxed, passcode-protected, revocable**
  link; revocation stops future access only (exported copies cannot be
  recalled), and "export" is a distinct, clearly-warned state.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class PacketLayer(StrEnum):
    PATIENT_PREP = "patient_prep"
    SUMMARY = "summary"


class PacketSection(StrEnum):
    CONCERN = "concern"
    TIMELINE = "timeline"
    PENDING = "pending"
    NARRATIVE = "narrative"
    QUESTION = "question"
    GOAL = "goal"
    OBSERVATION = "observation"
    MEDICATION = "medication"
    RESULT = "result"


class StatementClassification(StrEnum):
    """Per-statement provenance class (decision Q1c/Q3b).

    The gate blocks ``NEW_AI_DIAGNOSIS``. ``SOURCE_RECORD_DIAGNOSIS`` is a
    diagnosis already in the user's records (allowed, attributed), distinct from
    a *new* AI-generated diagnostic label (blocked).
    """

    DIRECT_SOURCE_FACT = "direct_source_fact"
    PATIENT_REPORTED = "patient_reported"
    GENERATED_SYNTHESIS = "generated_synthesis"
    GENERATED_INFERENCE = "generated_inference"
    SOURCE_RECORD_DIAGNOSIS = "source_record_diagnosis"
    NEW_AI_DIAGNOSIS = "new_ai_diagnosis"


class AbsenceReason(StrEnum):
    """IPS-style explicit absence — never imply "none" by silent omission."""

    KNOWN_ABSENT = "known_absent"
    NOT_ASKED = "not_asked"
    UNAVAILABLE = "unavailable"
    MASKED = "masked"


class PacketStatus(StrEnum):
    DRAFT = "draft"
    SHARED = "shared"


class ShareLinkStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class PacketSourceRef(BaseModel):
    """A claim-level pointer back to the evidence/object a statement summarizes."""

    ref_type: str
    source_id: str
    label: str | None = None


class VisitPacketStatementV2(BaseModel):
    schema_version: Literal["c13.visit_packet.statement.v2"] = "c13.visit_packet.statement.v2"
    statement_id: str
    layer: PacketLayer
    section: PacketSection
    ordinal: int
    text: str
    classification: StatementClassification
    source_refs: list[PacketSourceRef] = Field(default_factory=list)
    # Explicit absence: an included statement that asserts a known/unknown gap.
    absent: bool = False
    absence_reason: AbsenceReason | None = None
    # Deselection visibility: a deselected statement is kept and marked, not dropped.
    included: bool = True


class VisitPacketV2(BaseModel):
    schema_version: Literal["c13.visit_packet.v2"] = "c13.visit_packet.v2"
    packet_id: str
    patient_id: str
    title: str
    status: PacketStatus
    thread_ids: list[str] = Field(default_factory=list)
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    statements: list[VisitPacketStatementV2] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---- Requests ----------------------------------------------------------------


class PatientPrepInput(BaseModel):
    questions: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)


class GenerateVisitPacketRequest(BaseModel):
    title: str = "Visit packet"
    thread_ids: list[str] = Field(default_factory=list)
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    include_summary: bool = True
    prep: PatientPrepInput = Field(default_factory=PatientPrepInput)


class UpdateStatementInclusion(BaseModel):
    statement_id: str
    included: bool


class UpdatePacketRequest(BaseModel):
    inclusions: list[UpdateStatementInclusion] = Field(default_factory=list)


class SharePacketRequest(BaseModel):
    recipient_name: str
    recipient_identifier: str | None = None
    purpose: str = "clinician_visit"
    info_scope: str = "selected_threads"
    expires_in_hours: int = Field(default=168, ge=1, le=8760)
    passcode: str | None = None


class SharePacketResponse(BaseModel):
    schema_version: Literal["c13.visit_packet.share.v2"] = "c13.visit_packet.share.v2"
    share_link_id: str
    grant_id: str
    # The opaque token is returned exactly once, at mint time.
    share_token: str
    passcode_required: bool
    expires_at: datetime
    c10_decision: str


class ExportPacketResponse(BaseModel):
    schema_version: Literal["c13.visit_packet.export.v2"] = "c13.visit_packet.export.v2"
    packet: VisitPacketV2
    # Honest revocation semantics: an exported copy cannot be recalled.
    export_warning: str = (
        "This is an exported copy. Once shared or saved by a recipient it "
        "cannot be recalled — revoking a link only stops future access."
    )


class SharedPacketView(BaseModel):
    """Recipient-facing read of a shared packet (no owner-only internals)."""

    schema_version: Literal["c13.visit_packet.shared_view.v2"] = "c13.visit_packet.shared_view.v2"
    title: str
    shared_by_label: str = "the patient"
    statements: list[VisitPacketStatementV2] = Field(default_factory=list)
    expires_at: datetime
    review_note: str = (
        "Patient-prepared and not clinician-reviewed. Every statement links to "
        "its source. This packet does not contain a diagnosis from WellBe."
    )


__all__ = [
    "AbsenceReason",
    "ExportPacketResponse",
    "GenerateVisitPacketRequest",
    "PacketLayer",
    "PacketSection",
    "PacketSourceRef",
    "PacketStatus",
    "PatientPrepInput",
    "SharePacketRequest",
    "SharePacketResponse",
    "SharedPacketView",
    "ShareLinkStatus",
    "StatementClassification",
    "UpdatePacketRequest",
    "UpdateStatementInclusion",
    "VisitPacketStatementV2",
    "VisitPacketV2",
]
