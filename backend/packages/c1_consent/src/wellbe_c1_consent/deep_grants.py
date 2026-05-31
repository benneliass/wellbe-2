from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class RoleType(StrEnum):
    INDIVIDUAL_CONTROLLER = "individual_controller"
    CAREGIVER = "caregiver"
    CLINICIAN = "clinician"
    CARE_TEAM = "care_team"
    INSTITUTION = "institution"
    RESEARCHER = "researcher"


class WorkspaceType(StrEnum):
    INDIVIDUAL = "individual"
    CLINICIAN_CASE_INVESTIGATION = "clinician_case_investigation"
    SHARED_HEALTH_THREAD = "shared_health_thread"
    INSTITUTION_CONTINUITY = "institution_continuity"
    RESEARCH_SANDBOX = "research_sandbox"


class GrantType(StrEnum):
    CONTROLLER_ENTITLEMENT = "controller_entitlement"
    DELEGATED_INDIVIDUAL = "delegated_individual"
    WORKSPACE_SHARE = "workspace_share"
    INSTITUTION_AGGREGATE = "institution_aggregate"
    RESEARCH_SANDBOX = "research_sandbox"


class GrantStatus(StrEnum):
    DRAFT = "draft"
    REQUESTED = "requested"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ScopeCode(StrEnum):
    VISIT_PACKET_ONLY = "visit-packet-only"
    SPECIFIC_THREAD = "specific-thread"
    LABS_SYMPTOMS = "labs+symptoms"
    WEARABLE_TRENDS_ONLY = "wearable-trends-only"
    FULL_INVESTIGATION = "full-investigation"
    AGGREGATE_METRICS = "aggregate-metrics"
    RESEARCH_PROTOCOL = "research-protocol"


class Capability(StrEnum):
    READ = "read"
    COMMENT = "comment"
    EXPORT = "export"
    INVITE = "invite"
    CONTRIBUTE = "contribute"
    VIEW_AGGREGATE = "view_aggregate"
    RUN_ANALYSIS = "run_analysis"


class ContributionMode(StrEnum):
    EXTERNAL_ANNOTATION_ONLY = "external_annotation_only"
    PENDING_CONTROLLER_ACCEPTANCE = "pending_controller_acceptance"
    DIRECT_WRITE_ALLOWED_FOR_CONTROLLER_ONLY = "direct_write_allowed_for_controller_only"


@dataclass(frozen=True)
class RoleBinding:
    id: uuid.UUID
    actor_id: uuid.UUID
    role_type: RoleType
    status: str
    subject_user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    credential_ref: str | None = None


@dataclass(frozen=True)
class Workspace:
    id: uuid.UUID
    workspace_type: WorkspaceType
    controller_model: str
    subject_user_id: uuid.UUID | None
    status: str


@dataclass(frozen=True)
class WorkspaceMembership:
    id: uuid.UUID
    workspace_id: uuid.UUID
    role_binding_id: uuid.UUID
    status: str


@dataclass
class GrantScopeInstance:
    scope_code: ScopeCode
    scope_profile_version: int
    selector_type: str
    resource_ids: list[uuid.UUID] = field(default_factory=list)
    data_categories: list[str] = field(default_factory=list)
    include_security_labels: list[str] = field(default_factory=list)
    exclude_security_labels: list[str] = field(default_factory=list)
    raw_data_allowed: bool = False
    time_start: datetime | None = None
    time_end: datetime | None = None


@dataclass(frozen=True)
class GrantCapability:
    capability: Capability
    allowed: bool
    constraints: dict = field(default_factory=dict)


@dataclass
class Grant:
    id: uuid.UUID
    grant_type: GrantType
    status: GrantStatus
    grantor_user_id: uuid.UUID
    purpose_code: str
    scope_instances: list[GrantScopeInstance]
    capabilities: list[GrantCapability]
    effective_at: datetime
    expires_at: datetime | None = None
    recipient_role_binding_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    contribution_mode: ContributionMode = ContributionMode.EXTERNAL_ANNOTATION_ONLY
    aggregate_only: bool = False
    authz_epoch: int = 1
    revoked_at: datetime | None = None

    def allows_capability(self, capability: Capability) -> bool:
        return any(c.capability == capability and c.allowed for c in self.capabilities)


@dataclass(frozen=True)
class ResourceFilter:
    resource_ids: list[uuid.UUID] = field(default_factory=list)
    data_categories: list[str] = field(default_factory=list)
    include_security_labels: list[str] = field(default_factory=list)
    exclude_security_labels: list[str] = field(default_factory=list)
    patient_wildcard: bool = False


@dataclass(frozen=True)
class AccessPredicate:
    allow: bool
    reason_code: str
    grant_id: uuid.UUID | None = None
    grant_version: int | None = None
    allowed_actions: list[Capability] = field(default_factory=list)
    resource_filter: ResourceFilter = field(default_factory=ResourceFilter)
    obligations: list[str] = field(default_factory=list)
    expires_at: datetime | None = None


@dataclass(frozen=True)
class AccessDecisionRequest:
    actor_id: uuid.UUID
    role_binding: RoleBinding
    workspace: Workspace
    memberships: list[WorkspaceMembership]
    grants: list[Grant]
    action: Capability
    purpose_code: str
    resource_type: str
    resource_id: uuid.UUID | None
    data_category: str
    security_labels: list[str]
    now: datetime | None = None


class WorkspaceAccessEvaluator:
    """Pure C1 policy evaluator for deep grants.

    The evaluator deliberately returns a scoped predicate rather than a bare
    boolean. Downstream services must use the predicate to constrain reads before
    retrieval, search, export, or agent prompt construction.
    """

    def evaluate(self, request: AccessDecisionRequest) -> AccessPredicate:
        now = request.now or datetime.now(UTC)

        if request.role_binding.actor_id != request.actor_id:
            return self._deny("WB_AUTHZ_ROLE_NOT_ALLOWED")

        if request.role_binding.status != "active" or request.workspace.status != "active":
            return self._deny("WB_AUTHZ_DENIED")

        if not self._has_active_membership(request):
            return self._deny("WB_AUTHZ_WORKSPACE_MEMBERSHIP_REQUIRED")

        grant = self._select_matching_grant(request, now)
        if grant is None:
            return self._deny("WB_AUTHZ_DENIED")

        if grant.status == GrantStatus.REVOKED or grant.revoked_at is not None:
            return self._deny("WB_AUTHZ_GRANT_REVOKED")
        if grant.status == GrantStatus.EXPIRED or (grant.expires_at and now >= grant.expires_at):
            return self._deny("WB_AUTHZ_GRANT_EXPIRED")
        if grant.status != GrantStatus.ACTIVE:
            return self._deny("WB_AUTHZ_DENIED")

        if grant.aggregate_only and request.action != Capability.VIEW_AGGREGATE:
            return self._deny("WB_AUTHZ_AGGREGATE_ONLY_GRANT")

        if request.action == Capability.EXPORT and not grant.allows_capability(Capability.EXPORT):
            return self._deny("WB_AUTHZ_EXPORT_NOT_ALLOWED")
        if request.action == Capability.INVITE and not grant.allows_capability(Capability.INVITE):
            return self._deny("WB_AUTHZ_INVITE_NOT_ALLOWED")
        if not grant.allows_capability(request.action):
            return self._deny("WB_AUTHZ_INSUFFICIENT_CAPABILITY")

        scope = self._select_matching_scope(grant, request)
        if scope is None:
            return self._deny("WB_AUTHZ_RESOURCE_OUT_OF_SCOPE")

        denied_labels = set(scope.exclude_security_labels) & set(request.security_labels)
        if denied_labels:
            return self._deny("WB_AUTHZ_RESOURCE_OUT_OF_SCOPE")

        if scope.resource_ids and request.resource_id not in scope.resource_ids:
            return self._deny("WB_AUTHZ_RESOURCE_OUT_OF_SCOPE")

        if scope.data_categories and request.data_category not in scope.data_categories:
            return self._deny("WB_AUTHZ_RESOURCE_OUT_OF_SCOPE")

        return AccessPredicate(
            allow=True,
            reason_code="ok",
            grant_id=grant.id,
            grant_version=grant.authz_epoch,
            allowed_actions=[c.capability for c in grant.capabilities if c.allowed],
            resource_filter=ResourceFilter(
                resource_ids=list(scope.resource_ids),
                data_categories=list(scope.data_categories),
                include_security_labels=list(scope.include_security_labels),
                exclude_security_labels=list(scope.exclude_security_labels),
                patient_wildcard=False,
            ),
            obligations=["audit_each_view"],
            expires_at=grant.expires_at,
        )

    def can_directly_mutate_permanent_record(self, grant: Grant) -> bool:
        return (
            grant.contribution_mode
            == ContributionMode.DIRECT_WRITE_ALLOWED_FOR_CONTROLLER_ONLY
            and grant.grant_type == GrantType.CONTROLLER_ENTITLEMENT
        )

    def can_enable_research_participation(self, role_binding: RoleBinding) -> bool:
        return role_binding.role_type == RoleType.INDIVIDUAL_CONTROLLER

    def _has_active_membership(self, request: AccessDecisionRequest) -> bool:
        return any(
            membership.workspace_id == request.workspace.id
            and membership.role_binding_id == request.role_binding.id
            and membership.status == "active"
            for membership in request.memberships
        )

    def _select_matching_grant(
        self, request: AccessDecisionRequest, now: datetime
    ) -> Grant | None:
        for grant in request.grants:
            if grant.workspace_id != request.workspace.id:
                continue
            if grant.recipient_role_binding_id != request.role_binding.id:
                continue
            if grant.purpose_code != request.purpose_code:
                continue
            if grant.effective_at > now:
                continue
            return grant
        return None

    def _select_matching_scope(
        self, grant: Grant, request: AccessDecisionRequest
    ) -> GrantScopeInstance | None:
        for scope in grant.scope_instances:
            if scope.scope_code == ScopeCode.AGGREGATE_METRICS:
                continue
            if scope.data_categories and request.data_category not in scope.data_categories:
                continue
            return scope
        return None

    def _deny(self, reason_code: str) -> AccessPredicate:
        return AccessPredicate(allow=False, reason_code=reason_code)
