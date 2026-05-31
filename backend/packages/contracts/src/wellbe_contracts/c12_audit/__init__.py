from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class AuditPayloadClassification(StrEnum):
    NO_PHI = "no_phi"
    METADATA_ONLY = "metadata_only"
    SOURCE_REFS = "source_refs"
    RESTRICTED_TEXT_REF = "restricted_text_ref"
    ENCRYPTED_PHI_FRAGMENT = "encrypted_phi_fragment"
    PROHIBITED = "prohibited"


class AuditVisibility(StrEnum):
    CONTROLLER_VISIBLE = "controller_visible"
    PARTICIPANT_VISIBLE = "participant_visible"
    ADMIN_ONLY = "admin_only"
    SECURITY_ONLY = "security_only"
    SAFETY_REVIEW = "safety_review"
    RESEARCH_ADMIN = "research_admin"
    INSTITUTION_AGGREGATE_ADMIN = "institution_aggregate_admin"
    SYSTEM_INTERNAL = "system_internal"


class AuditRetentionClass(StrEnum):
    TRUST_LEDGER = "trust_ledger"
    SECURITY = "security"
    SAFETY = "safety"
    OPERATIONAL = "operational"
    RESEARCH_GOVERNANCE = "research_governance"
    NOTIFICATION_DELIVERY = "notification_delivery"


class AuditOutcomeStatus(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    REJECTED = "rejected"
    FAILED = "failed"
    ROUTED = "routed"


class AuditNotificationPolicy(StrEnum):
    NONE = "none"
    DIGEST = "digest"
    IMMEDIATE = "immediate"
    STATIC_TEMPLATE = "static_template"
    URGENT_ROUTE = "urgent_route"


class NotificationClass(StrEnum):
    INLINE_CONFIRMATION = "inline_confirmation"
    DIGEST = "digest"
    IMMEDIATE_CLOSURE = "immediate_closure"
    SECURITY_NOTICE = "security_notice"
    URGENT_ROUTE = "urgent_route"
    SILENT_AUDIT = "silent_audit"


class AuditActorV1(BaseModel):
    actor_type: str
    actor_id_hash: str
    role_type: str | None = None
    auth_session_id_hash: str | None = None


class AuditSubjectV1(BaseModel):
    patient_id_hash: str | None = None
    controller_user_id_hash: str | None = None
    workspace_id: str | None = None
    grant_id: str | None = None
    role_binding_id: str | None = None
    resource_type: str | None = None
    resource_id_hash: str | None = None


class AuditAuthorityV1(BaseModel):
    entitlement_type: str
    access_predicate_hash: str
    purpose_code: str
    scope_codes: list[str] = Field(default_factory=list)
    policy_version: str


class AuditContextV1(BaseModel):
    correlation_id: str
    trace_id: str | None = None
    request_id: str | None = None
    idempotency_key: str | None = None
    client_app: str | None = None
    user_agent_hash: str | None = None
    ip_geo_bucket: str | None = None


class AuditOutcomeV1(BaseModel):
    status: AuditOutcomeStatus
    reason_codes: list[str] = Field(default_factory=list)


class AuditEventCreateV1(BaseModel):
    schema_version: Literal["c12.audit_event.create.v1"] = "c12.audit_event.create.v1"
    event_type: str
    event_version: str
    producer_component: str
    producer_service: str
    environment: str
    occurred_at: datetime
    actor: AuditActorV1
    subject: AuditSubjectV1 = Field(default_factory=AuditSubjectV1)
    authority: AuditAuthorityV1 | None = None
    context: AuditContextV1
    outcome: AuditOutcomeV1
    payload_classification: AuditPayloadClassification
    payload_min: dict[str, Any] = Field(default_factory=dict)
    payload_ref: str | None = None
    notification_policy: AuditNotificationPolicy = AuditNotificationPolicy.NONE
    visibility: list[AuditVisibility]
    retention_class: AuditRetentionClass

    @model_validator(mode="after")
    def validate_audit_contract(self) -> AuditEventCreateV1:
        if self.payload_classification == AuditPayloadClassification.PROHIBITED:
            raise ValueError("prohibited payloads must not be stored in C12")
        if _requires_authority(self.event_type) and self.authority is None:
            raise ValueError("authority is required for access-sensitive audit events")
        return self


class AuditEventV1(AuditEventCreateV1):
    schema_version: Literal["c12.audit_event.v1"] = "c12.audit_event.v1"
    event_id: str
    recorded_at: datetime
    time_skew_ms: int
    payload_hash: str
    previous_event_hash: str | None = None
    event_hash: str
    hash_chain_scope: str
    signature_ref: str | None = None


class NotificationTemplateV1(BaseModel):
    template_id: str
    notification_class: NotificationClass
    rendered_copy: str
    allowed_variables: list[str] = Field(default_factory=list)
    c10_required: bool = False


class NotificationWorkItemV1(BaseModel):
    schema_version: Literal["c12.notification_work_item.v1"] = "c12.notification_work_item.v1"
    notification_id: str
    source_event_type: str
    notification_class: NotificationClass
    template_id: str
    rendered_copy: str
    dedupe_key: str
    patient_id_hash: str | None = None
    resource_id_hash: str | None = None
    context_only: bool = False
    not_personal_evidence: bool = False


def _requires_authority(event_type: str) -> bool:
    sensitive_terms = (
        ".access.",
        ".grant.",
        ".export.",
        ".render_token.",
        ".output.rendered",
        ".share_link.",
        ".research.",
        ".institution.",
    )
    return any(term in event_type for term in sensitive_terms)


__all__ = [
    "AuditActorV1",
    "AuditAuthorityV1",
    "AuditContextV1",
    "AuditEventCreateV1",
    "AuditEventV1",
    "AuditNotificationPolicy",
    "AuditOutcomeStatus",
    "AuditOutcomeV1",
    "AuditPayloadClassification",
    "AuditRetentionClass",
    "AuditSubjectV1",
    "AuditVisibility",
    "NotificationClass",
    "NotificationTemplateV1",
    "NotificationWorkItemV1",
]
