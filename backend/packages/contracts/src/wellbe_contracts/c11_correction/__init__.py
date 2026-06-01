"""C11 Correction Service contracts.

Corrections are append-only, source-linked overlays written THROUGH C5. They never
mutate C2 raw events, C4 facts, C5 links, C6 rows, C8 entries, or C12 audit. Only
``applied`` corrections participate in resolved reads; role/system proposals stay
``pending_controller_acceptance`` until the controller accepts. Downstream C6, C8,
and C13 reads use ONE shared deterministic resolver (this package's resolver).

Authoritative decision: docs/decisions/correction-service-layered-provenance.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

C11_CORRECTION_REQUESTED = "c11.correction.requested"
C11_CORRECTION_PROPOSED = "c11.correction.proposed"
C11_CORRECTION_ACCEPTED = "c11.correction.accepted"
C11_CORRECTION_APPLIED = "c11.correction.applied"
C11_CORRECTION_SUPERSEDED = "c11.correction.superseded"
C11_CORRECTION_REJECTED = "c11.correction.rejected"
C11_CORRECTION_WITHDRAWN = "c11.correction.withdrawn"
C11_RESOLUTION_CHANGED = "c11.correction.resolution_changed"
# Compatibility alias some C6 workers may consume.
CORRECTION_APPLIED_COMPAT = "correction.applied"

RESOLUTION_RULE_VERSION = "c11-resolve-v1"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CorrectionType(StrEnum):
    REPLACE_VALUE = "replace_value"
    MARK_INCORRECT = "mark_incorrect"
    ADD_MISSING_CONTEXT = "add_missing_context"
    MARK_STALE = "mark_stale"
    WITHDRAW_FROM_CURRENT_VIEW = "withdraw_from_current_view"
    RELABEL_THREAD = "relabel_thread"
    MERGE_DUPLICATE = "merge_duplicate"
    SPLIT_CONTEXT = "split_context"
    CHANGE_EVIDENCE_WEIGHT = "change_evidence_weight"


class CorrectionStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONTROLLER_ACCEPTANCE = "pending_controller_acceptance"
    APPLIED = "applied"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ActorAuthority(StrEnum):
    CONTROLLER = "controller"
    CONTROLLER_ACCEPTED_PROPOSAL = "controller_accepted_proposal"
    DELEGATED_CONTROLLER = "delegated_controller"
    ROLE_PROPOSED = "role_proposed"
    SYSTEM_SUGGESTED = "system_suggested"


class CorrectionTargetKind(StrEnum):
    C2_RAW_EVENT = "c2_raw_event"
    C4_EXTRACTED_FACT = "c4_extracted_fact"
    C5_EVIDENCE_LINK = "c5_evidence_link"
    C6_KG_NODE = "c6_kg_node"
    C6_KG_EDGE = "c6_kg_edge"
    C7_THREAD_LABEL = "c7_thread_label"
    C8_MEMORY_ENTRY = "c8_memory_entry"
    C9_PENDING_ITEM = "c9_pending_item"
    C14_INVESTIGATION = "c14_investigation"
    C15_THEORY = "c15_theory"


class ResolutionAction(StrEnum):
    BECAME_ACTIVE = "became_active"
    SUPERSEDED_PRIOR = "superseded_prior"
    LOST_PRECEDENCE = "lost_precedence"
    REMOVED_FROM_CURRENT_VIEW = "removed_from_current_view"
    REJECTED_PENDING = "rejected_pending"
    WITHDRAWN_BY_CONTROLLER = "withdrawn_by_controller"


# Authority rank (higher wins). Resolved user-facing view includes rank >= 80.
AUTHORITY_RANK: dict[ActorAuthority, int] = {
    ActorAuthority.CONTROLLER: 100,
    ActorAuthority.CONTROLLER_ACCEPTED_PROPOSAL: 90,
    ActorAuthority.DELEGATED_CONTROLLER: 80,
    ActorAuthority.ROLE_PROPOSED: 20,
    ActorAuthority.SYSTEM_SUGGESTED: 10,
}

# Semantic rank for conflicting types on the same field (higher wins).
SEMANTIC_TYPE_RANK: dict[CorrectionType, int] = {
    CorrectionType.WITHDRAW_FROM_CURRENT_VIEW: 90,
    CorrectionType.MARK_INCORRECT: 85,
    CorrectionType.REPLACE_VALUE: 70,
    CorrectionType.MARK_STALE: 60,
    CorrectionType.RELABEL_THREAD: 55,
    CorrectionType.CHANGE_EVIDENCE_WEIGHT: 50,
    CorrectionType.ADD_MISSING_CONTEXT: 40,
    CorrectionType.MERGE_DUPLICATE: 35,
    CorrectionType.SPLIT_CONTEXT: 35,
}

# Authorities admitted into the resolved (user-facing) view.
RESOLVED_VIEW_MIN_AUTHORITY_RANK = 80

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class CorrectionTargetRef(BaseModel):
    target_kind: CorrectionTargetKind
    target_id: UUID
    target_version: str | None = None
    field_path: str | None = None
    base_value_hash: str | None = None
    proposed_value_hash: str | None = None
    semantic_rank: int = 50


class Correction(BaseModel):
    correction_id: UUID
    patient_id: PatientId
    status: CorrectionStatus
    correction_type: CorrectionType
    actor_authority: ActorAuthority
    raw_correction_event_id: UUID
    rationale: str | None = None
    proposed_payload: dict = Field(default_factory=dict)
    supersedes_correction_id: UUID | None = None
    effective_at: AwareDatetime | None = None
    applied_at: AwareDatetime | None = None
    created_at: AwareDatetime | None = None
    targets: list[CorrectionTargetRef] = Field(default_factory=list)


class ResolvedOverlay(BaseModel):
    """Output of the shared resolver for one (target, field_path)."""

    target_kind: CorrectionTargetKind
    target_id: UUID
    field_path: str | None
    resolved_state: str  # 'base' | 'overlaid' | 'withdrawn' | 'stale' | 'augmented'
    active_correction_id: UUID | None
    inactive_correction_ids: list[UUID] = Field(default_factory=list)
    resolved_value: dict | None = None
    resolution_rule_version: str = RESOLUTION_RULE_VERSION
    explanation_code: str = "no_applied_corrections"


class CorrectionResult(BaseModel):
    correction_id: UUID
    status: CorrectionStatus
    actor_authority: ActorAuthority
    evidence_link_ids: list[UUID] = Field(default_factory=list)
    superseded_correction_id: UUID | None = None
    event_id: UUID | None = None


__all__ = [
    "C11_CORRECTION_REQUESTED",
    "C11_CORRECTION_PROPOSED",
    "C11_CORRECTION_ACCEPTED",
    "C11_CORRECTION_APPLIED",
    "C11_CORRECTION_SUPERSEDED",
    "C11_CORRECTION_REJECTED",
    "C11_CORRECTION_WITHDRAWN",
    "C11_RESOLUTION_CHANGED",
    "CORRECTION_APPLIED_COMPAT",
    "RESOLUTION_RULE_VERSION",
    "AUTHORITY_RANK",
    "SEMANTIC_TYPE_RANK",
    "RESOLVED_VIEW_MIN_AUTHORITY_RANK",
    "CorrectionType",
    "CorrectionStatus",
    "ActorAuthority",
    "CorrectionTargetKind",
    "ResolutionAction",
    "CorrectionTargetRef",
    "Correction",
    "ResolvedOverlay",
    "CorrectionResult",
]
