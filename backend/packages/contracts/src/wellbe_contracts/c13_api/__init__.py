from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ProblemCode(StrEnum):
    GRANT_REQUIRED = "grant_required"
    GRANT_EXPIRED = "grant_expired"
    GRANT_REVOKED = "grant_revoked"
    SCOPE_DENIED = "scope_denied"
    CAPABILITY_DENIED = "capability_denied"
    ACTIVE_ROLE_REQUIRED = "active_role_required"
    WORKSPACE_MEMBERSHIP_NOT_ACCESS = "workspace_membership_not_access"
    C10_TOKEN_REQUIRED = "c10_token_required"
    C10_TOKEN_HASH_MISMATCH = "c10_token_hash_mismatch"
    C10_OBLIGATIONS_UNFULFILLED = "c10_obligations_unfulfilled"
    PROVENANCE_MISSING = "provenance_missing"
    EXTERNAL_CONTEXT_ONLY_VIOLATION = "external_context_only_violation"
    THEORY_DIAGNOSIS_VIOLATION = "theory_diagnosis_violation"
    INSTITUTION_AGGREGATE_ONLY_VIOLATION = "institution_aggregate_only_violation"
    CROSS_PATIENT_OPT_IN_REQUIRED = "cross_patient_opt_in_required"
    RESEARCH_PROTOCOL_CONSENT_REQUIRED = "research_protocol_consent_required"
    AUDIT_WRITE_FAILED = "audit_write_failed"
    EXPORT_REQUIRES_CAPABILITY = "export_requires_capability"
    UNKNOWN_CONTRACT_VERSION = "unknown_contract_version"
    UNKNOWN_AUTHORIZATION_FIELD = "unknown_authorization_field"
    RENDER_TOKEN_EXPIRED = "render_token_expired"
    RENDER_TOKEN_INVALID = "render_token_invalid"
    POLICY_UNAVAILABLE = "policy_unavailable"
    AUDIT_REF_UNAVAILABLE = "audit_ref_unavailable"


class SourceQualityTierV2(StrEnum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"
    TIER_5 = "tier_5"


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProblemDetailsV2(StrictBaseModel):
    type: str
    title: str
    status: int
    code: ProblemCode
    detail: str
    correlation_id: str
    audit_event_id: str | None = None
    remediation: str | None = None


class AuditRefV2(StrictBaseModel):
    schema_version: Literal["c13.audit_ref.v2"] = "c13.audit_ref.v2"
    audit_event_id: str
    correlation_id: str
    trace_id: str | None = None
    visibility: list[str]
    event_summary: str


class SourceRefV2(StrictBaseModel):
    schema_version: Literal["c13.source_ref.v2"] = "c13.source_ref.v2"
    source_ref_id: str
    component: Literal["c2", "c5", "c16"]
    provenance_id: str
    source_hash: str
    display_label: str
    source_scope: Literal["personal", "external"]
    access_required: list[str] = Field(default_factory=list)


class C10ObligationV2(StrictBaseModel):
    schema_version: Literal["c13.c10_obligation.v2"] = "c13.c10_obligation.v2"
    obligation_code: str
    required: bool = True
    display_location: Literal["inline", "banner", "source_panel"] = "inline"
    blocking_if_unfulfilled: bool = True


class InvestigationV2(StrictBaseModel):
    schema_version: Literal["c13.investigation.v2"] = "c13.investigation.v2"
    investigation_id: str
    health_thread_ids: list[str]
    primary_question: str
    scope: dict[str, Any]
    status: str
    safety_level: str
    workspace_id: str
    participants: list[dict[str, Any]] = Field(default_factory=list)
    evidence_bundle_ref: str
    linked_theory_ids: list[str] = Field(default_factory=list)
    missing_context_items: list[dict[str, Any]] = Field(default_factory=list)
    pending_items: list[dict[str, Any]] = Field(default_factory=list)
    review_cadence: dict[str, Any] | None = None
    external_context_refs: list[str] = Field(default_factory=list)
    created_by: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class TheoryV2(StrictBaseModel):
    schema_version: Literal["c13.theory.v2"] = "c13.theory.v2"
    theory_id: str
    investigation_id: str
    health_thread_id: str
    label: str
    proposed_by: dict[str, Any]
    status: str
    safety_level: str
    evidence_for: list[dict[str, Any]] = Field(default_factory=list)
    evidence_against: list[dict[str, Any]] = Field(default_factory=list)
    missing_data: list[dict[str, Any]] = Field(default_factory=list)
    external_context_refs: list[str] = Field(default_factory=list)
    review_marker: str | None = None
    clinician_annotation_ref: str | None = None
    not_diagnosis: Literal[True]
    created_at: datetime
    updated_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class ExternalSourceRefV2(StrictBaseModel):
    schema_version: Literal["c13.external_source_ref.v2"] = "c13.external_source_ref.v2"
    external_source_id: str
    source_quality_tier: SourceQualityTierV2
    source_type: str
    publisher: str | None = None
    publication_date: str | None = None
    retrieved_at: datetime | None = None
    source_url_ref: str | None = None
    display_label: str
    context_only: Literal[True]
    not_personal_evidence: Literal[True]
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class RelevanceLinkV2(StrictBaseModel):
    schema_version: Literal["c13.relevance_link.v2"] = "c13.relevance_link.v2"
    relevance_link_id: str
    external_source_id: str
    external_claim_id: str
    linked_thread_id: str
    linked_investigation_id: str
    relevance_status: str
    why_relevant_summary: str
    source_quality_tier: SourceQualityTierV2
    context_only: Literal[True]
    not_personal_evidence: Literal[True]
    obligations: list[str] = Field(default_factory=list)
    created_at: datetime
    evaluated_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class WorkspaceV2(StrictBaseModel):
    schema_version: Literal["c13.workspace.v2"] = "c13.workspace.v2"
    workspace_id: str
    workspace_type: str
    display_name: str
    controller_subject_ref: str
    membership_state: str
    active_role_binding: dict[str, Any] | None = None
    capability_summary: dict[str, Any] = Field(default_factory=dict)
    data_access_not_implied: Literal[True]
    created_at: datetime
    updated_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class RoleBindingV2(StrictBaseModel):
    schema_version: Literal["c13.role_binding.v2"] = "c13.role_binding.v2"
    role_binding_id: str
    workspace_id: str
    role_type: str
    principal_ref: str
    state: str
    starts_at: datetime
    expires_at: datetime | None = None
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class GrantCapabilitiesV2(StrictBaseModel):
    can_read: bool = False
    can_search: bool = False
    can_comment: bool = False
    can_export: bool = False
    can_invite: bool = False
    can_contribute: bool = False
    can_request_correction: bool = False
    can_view_external_context: bool = False
    can_run_aggregate: bool = False
    can_use_research_sandbox: bool = False


class GrantV2(StrictBaseModel):
    schema_version: Literal["c13.grant.v2"] = "c13.grant.v2"
    grant_id: str
    grant_type: str
    subject_ref: str
    grantee_ref: str
    workspace_id: str
    role_binding_id: str
    scope_codes: list[str]
    scope_profile_version: str
    purpose_code: str
    status: str
    starts_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    capabilities: GrantCapabilitiesV2 = Field(default_factory=GrantCapabilitiesV2)
    contribution_policy: dict[str, Any] = Field(default_factory=dict)
    resource_constraints_summary: str
    obligations: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class AccessPredicateV2(StrictBaseModel):
    schema_version: Literal["c13.access_predicate.v2"] = "c13.access_predicate.v2"
    access_predicate_hash: str
    decision: Literal["allow", "deny", "allow_with_obligations"]
    decision_reason_codes: list[str] = Field(default_factory=list)
    grant_id: str | None = None
    workspace_id: str | None = None
    role_binding_id: str | None = None
    purpose_code: str
    scope_codes: list[str] = Field(default_factory=list)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    resource_constraints_summary: str | None = None
    obligations: list[str] = Field(default_factory=list)
    valid_until: datetime
    policy_version: str
    evaluated_at: datetime
    audit_event_id: str


class RenderApprovalV2(StrictBaseModel):
    schema_version: Literal["c13.render_approval.v2"] = "c13.render_approval.v2"
    render_authorization_ref: str
    render_token: str | None = None
    binds_request_id: str
    binds_text_sha256: str
    expires_at: datetime
    c10_decision: str
    obligations: list[C10ObligationV2] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    review_markers: list[str] = Field(default_factory=list)
    source_display_requirements: list[str] = Field(default_factory=list)
    audit_event_id: str


class RenderValidateRequestV2(StrictBaseModel):
    schema_version: Literal["c13.render_validate.request.v2"] = "c13.render_validate.request.v2"
    text: str
    render_approval: RenderApprovalV2 | None = None
    surface_capabilities: list[str] = Field(default_factory=list)
    correlation_id: str = "corr-render"


class RenderValidateResponseV2(StrictBaseModel):
    schema_version: Literal["c13.render_validate.response.v2"] = "c13.render_validate.response.v2"
    render_approval: RenderApprovalV2
    audit_ref: AuditRefV2


class PendingItemV2(StrictBaseModel):
    schema_version: Literal["c13.pending_item.v2"] = "c13.pending_item.v2"
    pending_item_id: str
    primary_thread_id: str
    item_type: str
    status: str
    title: str
    next_action_code: str | None = None
    due_at: datetime | None = None
    due_precision: str = "unknown"
    investigation_ids: list[str] = Field(default_factory=list)
    blocks_closure: bool = False
    created_at: datetime
    updated_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class MemoryEntryV2(StrictBaseModel):
    schema_version: Literal["c13.memory_entry.v2"] = "c13.memory_entry.v2"
    memory_entry_id: str
    memory_type: str
    lifecycle_state: str
    title: str
    thread_id: str
    # Pointers only — C8 never exposes displayed clinical values from its own payload.
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    resolved_overlays: list[dict[str, Any]] = Field(default_factory=list)
    projection_stale: bool = False
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


class CorrectionTargetV2(StrictBaseModel):
    target_kind: str
    target_id: str
    field_path: str | None = None
    semantic_rank: int | None = None


class CorrectionV2(StrictBaseModel):
    schema_version: Literal["c13.correction.v2"] = "c13.correction.v2"
    correction_id: str
    status: str
    correction_type: str
    actor_authority: str
    rationale: str | None = None
    targets: list[CorrectionTargetV2] = Field(default_factory=list)
    applied_at: datetime | None = None
    effective_at: datetime | None = None
    created_at: datetime
    audit_refs: list[AuditRefV2] = Field(default_factory=list)


SUPPORTED_SCHEMA_VERSIONS = [
    "c13.access_predicate.v2",
    "c13.audit_ref.v2",
    "c13.c10_obligation.v2",
    "c13.correction.v2",
    "c13.external_source_ref.v2",
    "c13.grant.v2",
    "c13.investigation.v2",
    "c13.memory_entry.v2",
    "c13.pending_item.v2",
    "c13.relevance_link.v2",
    "c13.render_approval.v2",
    "c13.render_validate.request.v2",
    "c13.render_validate.response.v2",
    "c13.role_binding.v2",
    "c13.source_ref.v2",
    "c13.theory.v2",
    "c13.workspace.v2",
]


class SupportedSchemaVersionsV2(StrictBaseModel):
    schema_version: Literal["c13.schema_versions.v2"] = "c13.schema_versions.v2"
    supported_schema_versions: list[str] = Field(default_factory=lambda: SUPPORTED_SCHEMA_VERSIONS)


__all__ = [
    "AccessPredicateV2",
    "AuditRefV2",
    "C10ObligationV2",
    "CorrectionTargetV2",
    "CorrectionV2",
    "ExternalSourceRefV2",
    "GrantCapabilitiesV2",
    "GrantV2",
    "InvestigationV2",
    "MemoryEntryV2",
    "PendingItemV2",
    "ProblemCode",
    "ProblemDetailsV2",
    "RelevanceLinkV2",
    "RenderApprovalV2",
    "RenderValidateRequestV2",
    "RenderValidateResponseV2",
    "RoleBindingV2",
    "SUPPORTED_SCHEMA_VERSIONS",
    "SourceQualityTierV2",
    "SourceRefV2",
    "SupportedSchemaVersionsV2",
    "TheoryV2",
    "WorkspaceV2",
]
