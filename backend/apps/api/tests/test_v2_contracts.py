from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from wellbe_api.main import app
from wellbe_contracts.c13_api import (
    AccessPredicateV2,
    AuditRefV2,
    ExternalSourceRefV2,
    GrantCapabilitiesV2,
    GrantV2,
    InvestigationV2,
    RelevanceLinkV2,
    RenderApprovalV2,
    SourceQualityTierV2,
    TheoryV2,
    WorkspaceV2,
)


def test_v2_schema_advertises_supported_contract_versions():
    response = TestClient(app).get("/v2/schema")

    assert response.status_code == 200
    versions = response.json()["supported_schema_versions"]
    assert "c13.investigation.v2" in versions
    assert "c13.theory.v2" in versions
    assert "c13.render_approval.v2" in versions
    assert "c13.audit_ref.v2" in versions


def test_core_v2_dtos_serialize_schema_versions():
    now = datetime.now(UTC)
    audit_ref = AuditRefV2(
        audit_event_id="aud_1",
        correlation_id="corr-1",
        visibility=["controller_visible"],
        event_summary="Grant was revoked",
    )
    investigation = InvestigationV2(
        investigation_id="inv_1",
        health_thread_ids=["thr_1"],
        primary_question="What patterns might explain this recurring symptom?",
        scope={"included_thread_ids": ["thr_1"]},
        status="active",
        safety_level="routine",
        workspace_id="wrk_1",
        evidence_bundle_ref="evb_1",
        created_by={"role_type": "controller", "actor_ref": "usr_hash_1"},
        created_at=now,
        updated_at=now,
        audit_refs=[audit_ref],
    )
    theory = TheoryV2(
        theory_id="thy_1",
        investigation_id="inv_1",
        health_thread_id="thr_1",
        label="A possible pattern related to sleep timing",
        proposed_by={"role_type": "controller", "actor_ref": "usr_hash_1"},
        status="proposed",
        safety_level="routine",
        not_diagnosis=True,
        created_at=now,
        updated_at=now,
    )
    external = ExternalSourceRefV2(
        external_source_id="extsrc_1",
        source_quality_tier=SourceQualityTierV2.TIER_1,
        source_type="systematic_review",
        display_label="External source",
        context_only=True,
        not_personal_evidence=True,
    )
    relevance = RelevanceLinkV2(
        relevance_link_id="rel_1",
        external_source_id="extsrc_1",
        external_claim_id="extclaim_1",
        linked_thread_id="thr_1",
        linked_investigation_id="inv_1",
        relevance_status="visible_context",
        why_relevant_summary="May provide general context.",
        source_quality_tier=SourceQualityTierV2.TIER_1,
        context_only=True,
        not_personal_evidence=True,
        obligations=["show_context_only_label"],
        created_at=now,
        evaluated_at=now,
    )
    workspace = WorkspaceV2(
        workspace_id="wrk_1",
        workspace_type="personal",
        display_name="Personal workspace",
        controller_subject_ref="subj_hash",
        membership_state="active",
        data_access_not_implied=True,
        created_at=now,
        updated_at=now,
    )
    grant = GrantV2(
        grant_id="grt_1",
        grant_type="investigation_scope",
        subject_ref="patient_hash",
        grantee_ref="clinician_hash",
        workspace_id="wrk_1",
        role_binding_id="rb_1",
        scope_codes=["investigation.read"],
        scope_profile_version="scope.profile.2026-06-01",
        purpose_code="visit_prep",
        status="active",
        starts_at=now,
        capabilities=GrantCapabilitiesV2(can_read=True),
        resource_constraints_summary="Limited to investigation inv_1.",
        created_at=now,
        updated_at=now,
    )
    predicate = AccessPredicateV2(
        access_predicate_hash="sha256:predicate",
        decision="allow",
        grant_id="grt_1",
        workspace_id="wrk_1",
        role_binding_id="rb_1",
        purpose_code="visit_prep",
        scope_codes=["investigation.read"],
        valid_until=now,
        policy_version="c1.policy.2026-06-01",
        evaluated_at=now,
        audit_event_id="aud_1",
    )
    render = RenderApprovalV2(
        render_authorization_ref="rar_1",
        binds_request_id="req_1",
        binds_text_sha256="sha256:text",
        expires_at=now,
        c10_decision="allow_with_obligations",
        audit_event_id="aud_2",
    )

    assert investigation.model_dump(mode="json")["schema_version"] == "c13.investigation.v2"
    assert theory.model_dump(mode="json")["schema_version"] == "c13.theory.v2"
    assert external.model_dump(mode="json")["schema_version"] == "c13.external_source_ref.v2"
    assert relevance.model_dump(mode="json")["schema_version"] == "c13.relevance_link.v2"
    assert workspace.model_dump(mode="json")["schema_version"] == "c13.workspace.v2"
    assert grant.model_dump(mode="json")["schema_version"] == "c13.grant.v2"
    assert predicate.model_dump(mode="json")["schema_version"] == "c13.access_predicate.v2"
    assert render.model_dump(mode="json")["schema_version"] == "c13.render_approval.v2"


def test_theory_requires_not_diagnosis_true():
    with pytest.raises(ValidationError):
        TheoryV2(
            theory_id="thy_1",
            investigation_id="inv_1",
            health_thread_id="thr_1",
            label="Diagnosis-like label",
            proposed_by={"role_type": "controller"},
            status="proposed",
            safety_level="routine",
            not_diagnosis=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


def test_external_evidence_requires_context_only_flags():
    with pytest.raises(ValidationError):
        ExternalSourceRefV2(
            external_source_id="extsrc_1",
            source_quality_tier=SourceQualityTierV2.TIER_1,
            source_type="systematic_review",
            display_label="External source",
            context_only=False,
            not_personal_evidence=True,
        )


def test_grant_capabilities_default_false():
    capabilities = GrantCapabilitiesV2()

    assert capabilities.can_read is False
    assert capabilities.can_search is False
    assert capabilities.can_export is False
    assert capabilities.can_invite is False
    assert capabilities.can_contribute is False
