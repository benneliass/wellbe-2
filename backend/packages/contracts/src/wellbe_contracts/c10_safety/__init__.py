from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class OutputFormat(StrEnum):
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    STRUCTURED_BLOCKS = "structured_blocks"


class OutputType(StrEnum):
    TIMELINE_FORMATTING = "timeline_formatting"
    MISSING_CONTEXT_REMINDER = "missing_context_reminder"
    THREAD_SUMMARY = "thread_summary"
    INVESTIGATION_SUMMARY = "investigation_summary"
    CONTRADICTION_DETECTION = "contradiction_detection"
    CONFOUNDER_DETECTION = "confounder_detection"
    THEORY_EVALUATION = "theory_evaluation"
    EXTERNAL_EVIDENCE_SUMMARY = "external_evidence_summary"
    EXTERNAL_RESEARCH_RELEVANCE = "external_research_relevance"
    LIVE_METRIC_ESCALATION = "live_metric_escalation"
    VISIT_PACKET = "visit_packet"
    CLINICIAN_WORKSPACE_SUMMARY = "clinician_workspace_summary"
    INSTITUTION_AGGREGATE_SUMMARY = "institution_aggregate_summary"
    RESEARCH_SANDBOX_OUTPUT = "research_sandbox_output"
    CROSS_PATIENT_COMPARISON = "cross_patient_comparison"
    OTHER = "other"


class EngineRiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    MEDIUM_HIGH = "medium_high"
    HIGH = "high"
    VERY_HIGH = "very_high"


class WorkspaceType(StrEnum):
    INDIVIDUAL = "individual"
    CLINICIAN_CASE_INVESTIGATION = "clinician_case_investigation"
    SHARED_THREAD = "shared_thread"
    INSTITUTION_AGGREGATE = "institution_aggregate"
    RESEARCH_SANDBOX = "research_sandbox"


class ReviewMarker(StrEnum):
    PATIENT_ENTERED = "patient-entered"
    AI_SUMMARIZED = "AI-summarized"
    NOT_CLINICIAN_REVIEWED = "not-clinician-reviewed"
    CLINICIAN_REVIEWED = "clinician-reviewed"
    CLINICIAN_ANNOTATED = "clinician-annotated"
    READY_FOR_VISIT = "ready-for-visit"
    NEEDS_URGENT_CARE_CONSIDERATION = "needs-urgent-care-consideration"


class UrgencyClass(StrEnum):
    NONE = "none"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    SELF_HARM = "self_harm"


class UrgencySource(StrEnum):
    NONE = "none"
    PATIENT_REPORTED = "patient_reported"
    CLINICIAN_RECORD = "clinician_record"
    LAB_REPORT = "lab_report"
    WEARABLE_OR_DEVICE = "wearable_or_device"
    PATTERN_DETECTION = "pattern_detection"
    LIVE_METRIC_ENGINE = "live_metric_engine"
    EXTERNAL_REFERENCE = "external_reference"


class ProvenanceCompleteness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    ABSENT = "absent"
    NOT_APPLICABLE_NO_HEALTH_CLAIMS = "not_applicable_no_health_claims"


class ClaimType(StrEnum):
    PERSONAL_FACT = "personal_fact"
    PATIENT_REPORTED = "patient_reported"
    CLINICIAN_RECORDED = "clinician_recorded"
    LAB_RESULT = "lab_result"
    DEVICE_READING = "device_reading"
    DERIVED_PATTERN = "derived_pattern"
    MISSING_CONTEXT = "missing_context"
    THEORY_SUPPORT = "theory_support"
    THEORY_CONTRADICTION = "theory_contradiction"
    THEORY_MISSING_DATA = "theory_missing_data"
    EXTERNAL_CONTEXT = "external_context"
    URGENCY_GUIDANCE = "urgency_guidance"
    AGGREGATE_OR_COHORT = "aggregate_or_cohort"
    META_OR_DISCLAIMER = "meta_or_disclaimer"


class EvidenceRefType(StrEnum):
    RAW_CONTEXT_EVENT = "raw_context_event"
    RAW_BLOB = "raw_blob"
    SOURCE_TEXT_SPAN = "source_text_span"
    EXTRACTED_FACT = "extracted_fact"
    EVIDENCE_LINK = "evidence_link"
    GRAPH_NODE = "graph_node"
    GRAPH_EDGE = "graph_edge"
    EXTERNAL_SOURCE = "external_source"
    EXTERNAL_CLAIM = "external_claim"
    RELEVANCE_LINK = "relevance_link"
    NEGATIVE_EVIDENCE_QUERY = "negative_evidence_query"
    AGGREGATE_RESULT = "aggregate_result"


class SourceType(StrEnum):
    PATIENT_ENTERED_NOTE = "patient_entered_note"
    IMPORTED_CLINICAL_NOTE = "imported_clinical_note"
    LAB_REPORT = "lab_report"
    IMAGING_REPORT = "imaging_report"
    PRESCRIPTION_RECORD = "prescription_record"
    WEARABLE_READING = "wearable_reading"
    DEVICE_READING = "device_reading"
    CLINICAL_GUIDELINE = "clinical_guideline"
    OFFICIAL_MEDICAL_BODY = "official_medical_body"
    SYSTEMATIC_REVIEW = "systematic_review"
    PEER_REVIEWED_PAPER = "peer_reviewed_paper"
    CASE_REPORT = "case_report"
    EARLY_RESEARCH = "early_research"
    MEDICAL_BLOG_OR_EXPLAINER = "medical_blog_or_explainer"
    FORUM_OR_ANECDOTE = "forum_or_anecdote"
    AGGREGATE_DATASET = "aggregate_dataset"


class SourceQualityTier(StrEnum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"
    TIER_5 = "tier_5"


class GuardrailStatus(StrEnum):
    PASS = "pass"
    BLOCK = "block"
    ERROR = "error"
    TIMEOUT = "timeout"


class LayerStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"
    FAIL_CLOSED = "fail_closed"
    SKIPPED_NOT_APPLICABLE = "skipped_not_applicable"


class C10Decision(StrEnum):
    ALLOW = "allow"
    ALLOW_WITH_OBLIGATIONS = "allow_with_obligations"
    REWRITE_REQUIRED = "rewrite_required"
    BLOCK = "block"
    ROUTE_URGENT = "route_urgent"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    FAIL_CLOSED = "fail_closed"


class C10ReasonCode(StrEnum):
    C10_CONTRACT_INVALID = "C10_CONTRACT_INVALID"
    C10_BYPASS_ATTEMPT = "C10_BYPASS_ATTEMPT"
    C10_DIAGNOSIS_ASSERTION = "C10_DIAGNOSIS_ASSERTION"
    C10_RULE_OUT_ASSERTION = "C10_RULE_OUT_ASSERTION"
    C10_RANKED_DIFFERENTIAL = "C10_RANKED_DIFFERENTIAL"
    C10_PROBABILITY_DIAGNOSIS = "C10_PROBABILITY_DIAGNOSIS"
    C10_MEDICATION_DIRECTIVE = "C10_MEDICATION_DIRECTIVE"
    C10_FALSE_CLOSURE = "C10_FALSE_CLOSURE"
    C10_PANIC_LANGUAGE = "C10_PANIC_LANGUAGE"
    C10_URGENCY_WITHOUT_ACTION = "C10_URGENCY_WITHOUT_ACTION"
    C10_PROVENANCE_MISSING = "C10_PROVENANCE_MISSING"
    C10_EXTERNAL_EVIDENCE_PERSONALIZED = "C10_EXTERNAL_EVIDENCE_PERSONALIZED"
    C10_REVIEW_MARKER_MISSING = "C10_REVIEW_MARKER_MISSING"
    C10_ACCESS_SCOPE_VIOLATION = "C10_ACCESS_SCOPE_VIOLATION"
    C10_GUARDRAIL_UNAVAILABLE = "C10_GUARDRAIL_UNAVAILABLE"
    C10_RENDER_TOKEN_MISMATCH = "C10_RENDER_TOKEN_MISMATCH"


class UrgencyActionPath(BaseModel):
    type: str
    display_text: str
    locale: str | None = None


class UrgencyContext(BaseModel):
    urgency_class: UrgencyClass
    urgency_source: UrgencySource
    action_path: UrgencyActionPath | None = None


class EvidenceRef(BaseModel):
    evidence_ref_id: str
    ref_type: EvidenceRefType
    source_type: SourceType
    source_id: str
    source_quality_tier: SourceQualityTier | None = None
    source_text_span_hash: str | None = None
    access_scope_id: str | None = None


class ClaimMapEntry(BaseModel):
    claim_id: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    claim_type: ClaimType
    personal_specific: bool
    external_context_only: bool
    evidence_refs: list[EvidenceRef]
    provenance_complete: bool
    uncertainty_label: str = "unknown_or_missing"


class C10SafetyEvaluationRequestV1(BaseModel):
    schema_version: Literal["c10.safety_eval.request.v1"] = "c10.safety_eval.request.v1"
    request_id: str
    requested_at: datetime
    idempotency_key: str
    output_text: str
    output_format: OutputFormat
    output_type: OutputType
    target_audience: str
    surface: str
    review_markers: list[ReviewMarker]
    urgency: UrgencyContext
    claim_map: list[ClaimMapEntry]
    claim_map_complete: bool
    no_health_claims_asserted: bool
    engine_name: str
    engine_version: str
    engine_risk_tier: EngineRiskTier
    upstream_run_id: str
    actor_id: str
    workspace_id: str
    workspace_type: WorkspaceType
    active_role_type: str
    purpose_code: str
    access_decision_id: str
    access_predicate_hash: str
    c10_policy_version: str
    deterministic_ruleset_version: str
    nemo_guardrails_config_id: str
    llama_guard_policy_version: str
    risk_tier_policy_version: str
    correlation_id: str
    language: str = "en"
    subject_user_id: str | None = None
    patient_id: str | None = None
    grant_id: str | None = None
    organization_id: str | None = None
    data_scope_ids: list[str] = Field(default_factory=list)
    health_thread_id: str | None = None
    investigation_id: str | None = None
    theory_id: str | None = None
    visit_packet_id: str | None = None
    live_metric_session_id: str | None = None
    cohort_query_id: str | None = None
    aggregate_result_id: str | None = None
    evidence_bundle_id: str | None = None
    provenance_completeness: ProvenanceCompleteness
    relevance_link_ids: list[str] = Field(default_factory=list)
    trace_id: str | None = None

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.output_text.encode("utf-8")).hexdigest()


class AccessValidationResult(BaseModel):
    allow: bool
    reason_codes: list[C10ReasonCode] = Field(default_factory=list)


class GuardrailResult(BaseModel):
    status: GuardrailStatus
    reason_codes: list[C10ReasonCode] = Field(default_factory=list)
    model_or_config: str | None = None
    raw_label: str | None = None


class LayerResult(BaseModel):
    status: LayerStatus
    reason_codes: list[C10ReasonCode] = Field(default_factory=list)


class RuleResult(BaseModel):
    rule_id: str
    status: LayerStatus
    reason_code: C10ReasonCode | None = None


class RenderToken(BaseModel):
    token_type: Literal["c10_signed_render_token"] = "c10_signed_render_token"
    token: str
    binds_request_id: str
    binds_text_sha256: str
    expires_at: datetime


class C10Obligation(BaseModel):
    type: str
    claim_ids: list[str] = Field(default_factory=list)
    markers: list[ReviewMarker] = Field(default_factory=list)


class C10AuditMetadata(BaseModel):
    emitted_event_ids: list[str] = Field(default_factory=list)
    primary_event_name: str


class C10SafetyEvaluationResponseV1(BaseModel):
    schema_version: Literal["c10.safety_eval.response.v1"] = "c10.safety_eval.response.v1"
    evaluation_id: str
    request_id: str
    evaluated_at: datetime
    decision: C10Decision
    original_text_allowed: bool
    effective_text: str | None = None
    effective_text_sha256: str | None = None
    render_token: RenderToken | None = None
    obligations: list[C10Obligation] = Field(default_factory=list)
    reason_codes: list[C10ReasonCode] = Field(default_factory=list)
    layer_results: dict[str, LayerResult]
    audit: C10AuditMetadata


__all__ = [
    "AccessValidationResult",
    "C10AuditMetadata",
    "C10Decision",
    "C10Obligation",
    "C10ReasonCode",
    "C10SafetyEvaluationRequestV1",
    "C10SafetyEvaluationResponseV1",
    "ClaimMapEntry",
    "ClaimType",
    "EngineRiskTier",
    "EvidenceRef",
    "EvidenceRefType",
    "GuardrailResult",
    "GuardrailStatus",
    "LayerResult",
    "LayerStatus",
    "OutputFormat",
    "OutputType",
    "ProvenanceCompleteness",
    "RenderToken",
    "ReviewMarker",
    "RuleResult",
    "SourceQualityTier",
    "SourceType",
    "UrgencyActionPath",
    "UrgencyClass",
    "UrgencyContext",
    "UrgencySource",
    "WorkspaceType",
]
