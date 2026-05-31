from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from wellbe_c1_consent.deep_grants import (
    AccessDecisionRequest,
    Capability,
    ContributionMode,
    Grant,
    GrantCapability,
    GrantScopeInstance,
    GrantStatus,
    GrantType,
    RoleBinding,
    RoleType,
    ScopeCode,
    Workspace,
    WorkspaceAccessEvaluator,
    WorkspaceMembership,
    WorkspaceType,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _clinician_grant(
    *,
    workspace_id,
    role_binding_id,
    grantor_id,
    scope_code: ScopeCode = ScopeCode.LABS_SYMPTOMS,
    capabilities: list[GrantCapability] | None = None,
) -> Grant:
    now = _now()
    return Grant(
        id=uuid4(),
        grant_type=GrantType.WORKSPACE_SHARE,
        status=GrantStatus.ACTIVE,
        grantor_user_id=grantor_id,
        recipient_role_binding_id=role_binding_id,
        workspace_id=workspace_id,
        purpose_code="care_investigation",
        scope_instances=[
            GrantScopeInstance(
                scope_code=scope_code,
                scope_profile_version=1,
                selector_type="category_time_window",
                resource_ids=[],
                data_categories=["labs", "symptoms"],
                include_security_labels=[],
                exclude_security_labels=["private_memory", "raw_wearable"],
                raw_data_allowed=False,
                time_start=now - timedelta(days=30),
                time_end=now + timedelta(days=1),
            )
        ],
        capabilities=capabilities
        or [
            GrantCapability(capability=Capability.READ, allowed=True),
            GrantCapability(capability=Capability.COMMENT, allowed=True),
            GrantCapability(capability=Capability.EXPORT, allowed=False),
        ],
        contribution_mode=ContributionMode.PENDING_CONTROLLER_ACCEPTANCE,
        effective_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(days=7),
        authz_epoch=1,
    )


class TestWorkspaceAccessEvaluator:
    def test_workspace_membership_without_grant_does_not_authorize_data_access(self):
        actor_id = uuid4()
        workspace_id = uuid4()
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=actor_id,
            role_type=RoleType.CLINICIAN,
            organization_id=uuid4(),
            status="active",
        )
        workspace = Workspace(
            id=workspace_id,
            workspace_type=WorkspaceType.CLINICIAN_CASE_INVESTIGATION,
            controller_model="single_individual",
            subject_user_id=uuid4(),
            status="active",
        )
        membership = WorkspaceMembership(
            id=uuid4(),
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            status="active",
        )

        decision = WorkspaceAccessEvaluator().evaluate(
            AccessDecisionRequest(
                actor_id=actor_id,
                role_binding=role_binding,
                workspace=workspace,
                memberships=[membership],
                grants=[],
                action=Capability.READ,
                purpose_code="care_investigation",
                resource_type="lab_result",
                resource_id=uuid4(),
                data_category="labs",
                security_labels=[],
            )
        )

        assert decision.allow is False
        assert decision.reason_code == "WB_AUTHZ_DENIED"

    def test_active_grant_returns_access_predicate_with_resource_filter_and_audit_obligation(self):
        actor_id = uuid4()
        controller_id = uuid4()
        workspace_id = uuid4()
        lab_id = uuid4()
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=actor_id,
            role_type=RoleType.CLINICIAN,
            organization_id=uuid4(),
            status="active",
        )
        workspace = Workspace(
            id=workspace_id,
            workspace_type=WorkspaceType.CLINICIAN_CASE_INVESTIGATION,
            controller_model="single_individual",
            subject_user_id=controller_id,
            status="active",
        )
        membership = WorkspaceMembership(
            id=uuid4(),
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            status="active",
        )
        grant = _clinician_grant(
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            grantor_id=controller_id,
        )
        grant.scope_instances[0].resource_ids = [lab_id]

        decision = WorkspaceAccessEvaluator().evaluate(
            AccessDecisionRequest(
                actor_id=actor_id,
                role_binding=role_binding,
                workspace=workspace,
                memberships=[membership],
                grants=[grant],
                action=Capability.READ,
                purpose_code="care_investigation",
                resource_type="lab_result",
                resource_id=lab_id,
                data_category="labs",
                security_labels=[],
            )
        )

        assert decision.allow is True
        assert decision.reason_code == "ok"
        assert decision.grant_id == grant.id
        assert decision.resource_filter.resource_ids == [lab_id]
        assert decision.resource_filter.data_categories == ["labs", "symptoms"]
        assert "audit_each_view" in decision.obligations

    def test_full_investigation_never_compiles_to_patient_wildcard(self):
        actor_id = uuid4()
        controller_id = uuid4()
        workspace_id = uuid4()
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=actor_id,
            role_type=RoleType.CLINICIAN,
            organization_id=uuid4(),
            status="active",
        )
        workspace = Workspace(
            id=workspace_id,
            workspace_type=WorkspaceType.CLINICIAN_CASE_INVESTIGATION,
            controller_model="single_individual",
            subject_user_id=controller_id,
            status="active",
        )
        membership = WorkspaceMembership(
            id=uuid4(),
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            status="active",
        )
        grant = _clinician_grant(
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            grantor_id=controller_id,
            scope_code=ScopeCode.FULL_INVESTIGATION,
        )
        grant.scope_instances[0].data_categories = ["labs", "symptoms", "documents"]
        grant.scope_instances[0].exclude_security_labels = ["private_memory", "hidden"]

        decision = WorkspaceAccessEvaluator().evaluate(
            AccessDecisionRequest(
                actor_id=actor_id,
                role_binding=role_binding,
                workspace=workspace,
                memberships=[membership],
                grants=[grant],
                action=Capability.READ,
                purpose_code="care_investigation",
                resource_type="thread_summary",
                resource_id=uuid4(),
                data_category="documents",
                security_labels=[],
            )
        )

        assert decision.allow is True
        assert decision.resource_filter.patient_wildcard is False
        assert "private_memory" in decision.resource_filter.exclude_security_labels

    def test_hidden_or_private_labeled_resource_is_denied_even_under_full_investigation(self):
        actor_id = uuid4()
        controller_id = uuid4()
        workspace_id = uuid4()
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=actor_id,
            role_type=RoleType.CLINICIAN,
            organization_id=uuid4(),
            status="active",
        )
        workspace = Workspace(
            id=workspace_id,
            workspace_type=WorkspaceType.CLINICIAN_CASE_INVESTIGATION,
            controller_model="single_individual",
            subject_user_id=controller_id,
            status="active",
        )
        membership = WorkspaceMembership(
            id=uuid4(),
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            status="active",
        )
        grant = _clinician_grant(
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            grantor_id=controller_id,
            scope_code=ScopeCode.FULL_INVESTIGATION,
        )
        grant.scope_instances[0].exclude_security_labels = ["private_memory", "hidden"]

        decision = WorkspaceAccessEvaluator().evaluate(
            AccessDecisionRequest(
                actor_id=actor_id,
                role_binding=role_binding,
                workspace=workspace,
                memberships=[membership],
                grants=[grant],
                action=Capability.READ,
                purpose_code="care_investigation",
                resource_type="memory_entry",
                resource_id=uuid4(),
                data_category="symptoms",
                security_labels=["private_memory"],
            )
        )

        assert decision.allow is False
        assert decision.reason_code == "WB_AUTHZ_RESOURCE_OUT_OF_SCOPE"

    def test_export_requires_explicit_export_capability(self):
        actor_id = uuid4()
        controller_id = uuid4()
        workspace_id = uuid4()
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=actor_id,
            role_type=RoleType.CLINICIAN,
            organization_id=uuid4(),
            status="active",
        )
        workspace = Workspace(
            id=workspace_id,
            workspace_type=WorkspaceType.CLINICIAN_CASE_INVESTIGATION,
            controller_model="single_individual",
            subject_user_id=controller_id,
            status="active",
        )
        membership = WorkspaceMembership(
            id=uuid4(),
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            status="active",
        )
        grant = _clinician_grant(
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            grantor_id=controller_id,
        )

        decision = WorkspaceAccessEvaluator().evaluate(
            AccessDecisionRequest(
                actor_id=actor_id,
                role_binding=role_binding,
                workspace=workspace,
                memberships=[membership],
                grants=[grant],
                action=Capability.EXPORT,
                purpose_code="care_investigation",
                resource_type="visit_packet",
                resource_id=uuid4(),
                data_category="labs",
                security_labels=[],
            )
        )

        assert decision.allow is False
        assert decision.reason_code == "WB_AUTHZ_EXPORT_NOT_ALLOWED"

    def test_non_controller_cannot_directly_mutate_permanent_record(self):
        grant = _clinician_grant(
            workspace_id=uuid4(),
            role_binding_id=uuid4(),
            grantor_id=uuid4(),
            capabilities=[GrantCapability(capability=Capability.CONTRIBUTE, allowed=True)],
        )

        assert grant.contribution_mode == ContributionMode.PENDING_CONTROLLER_ACCEPTANCE
        assert WorkspaceAccessEvaluator().can_directly_mutate_permanent_record(grant) is False

    def test_institution_grant_denies_patient_level_resource_access(self):
        actor_id = uuid4()
        workspace_id = uuid4()
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=actor_id,
            role_type=RoleType.INSTITUTION,
            organization_id=uuid4(),
            status="active",
        )
        workspace = Workspace(
            id=workspace_id,
            workspace_type=WorkspaceType.INSTITUTION_CONTINUITY,
            controller_model="aggregate_only",
            subject_user_id=None,
            status="active",
        )
        membership = WorkspaceMembership(
            id=uuid4(),
            workspace_id=workspace_id,
            role_binding_id=role_binding.id,
            status="active",
        )
        grant = Grant(
            id=uuid4(),
            grant_type=GrantType.INSTITUTION_AGGREGATE,
            status=GrantStatus.ACTIVE,
            grantor_user_id=uuid4(),
            recipient_role_binding_id=role_binding.id,
            workspace_id=workspace_id,
            purpose_code="continuity_metrics",
            scope_instances=[
                GrantScopeInstance(
                    scope_code=ScopeCode.AGGREGATE_METRICS,
                    scope_profile_version=1,
                    selector_type="aggregate_cohort",
                    resource_ids=[],
                    data_categories=["follow_up_metrics"],
                    raw_data_allowed=False,
                )
            ],
            capabilities=[GrantCapability(capability=Capability.VIEW_AGGREGATE, allowed=True)],
            aggregate_only=True,
            effective_at=_now() - timedelta(minutes=1),
            expires_at=_now() + timedelta(days=7),
        )

        decision = WorkspaceAccessEvaluator().evaluate(
            AccessDecisionRequest(
                actor_id=actor_id,
                role_binding=role_binding,
                workspace=workspace,
                memberships=[membership],
                grants=[grant],
                action=Capability.READ,
                purpose_code="continuity_metrics",
                resource_type="health_thread",
                resource_id=uuid4(),
                data_category="follow_up_metrics",
                security_labels=[],
            )
        )

        assert decision.allow is False
        assert decision.reason_code == "WB_AUTHZ_AGGREGATE_ONLY_GRANT"

    @pytest.mark.parametrize(
        "role_type",
        [RoleType.CLINICIAN, RoleType.INSTITUTION, RoleType.RESEARCHER],
    )
    def test_non_controller_roles_cannot_enable_research_or_cross_patient_access(self, role_type):
        role_binding = RoleBinding(
            id=uuid4(),
            actor_id=uuid4(),
            role_type=role_type,
            organization_id=uuid4(),
            status="active",
        )

        assert WorkspaceAccessEvaluator().can_enable_research_participation(role_binding) is False
