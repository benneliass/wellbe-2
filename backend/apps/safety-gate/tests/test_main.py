from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from wellbe_contracts.c10_safety import (
    C10Decision,
    C10SafetyEvaluationRequestV1,
    ClaimMapEntry,
    ClaimType,
    EngineRiskTier,
    EvidenceRef,
    EvidenceRefType,
    OutputFormat,
    OutputType,
    ProvenanceCompleteness,
    ReviewMarker,
    SourceType,
    UrgencyClass,
    UrgencyContext,
    UrgencySource,
    WorkspaceType,
)
from wellbe_safety_gate.main import app


def _request_payload(text: str) -> dict:
    request = C10SafetyEvaluationRequestV1(
        request_id=str(uuid4()),
        requested_at=datetime.now(UTC),
        idempotency_key="idem-1",
        output_text=text,
        output_format=OutputFormat.PLAIN_TEXT,
        output_type=OutputType.THREAD_SUMMARY,
        target_audience="individual",
        surface="individual_workspace",
        review_markers=[
            ReviewMarker.AI_SUMMARIZED,
            ReviewMarker.NOT_CLINICIAN_REVIEWED,
        ],
        urgency=UrgencyContext(
            urgency_class=UrgencyClass.NONE,
            urgency_source=UrgencySource.NONE,
        ),
        claim_map=[
            ClaimMapEntry(
                claim_id="claim-1",
                char_start=0,
                char_end=len(text),
                claim_type=ClaimType.PATIENT_REPORTED,
                personal_specific=True,
                external_context_only=False,
                evidence_refs=[
                    EvidenceRef(
                        evidence_ref_id=str(uuid4()),
                        ref_type=EvidenceRefType.RAW_CONTEXT_EVENT,
                        source_type=SourceType.PATIENT_ENTERED_NOTE,
                        source_id=str(uuid4()),
                    )
                ],
                provenance_complete=True,
            )
        ],
        claim_map_complete=True,
        no_health_claims_asserted=False,
        engine_name="thread-summary",
        engine_version="0.1.0",
        engine_risk_tier=EngineRiskTier.LOW,
        upstream_run_id="run-1",
        actor_id=str(uuid4()),
        subject_user_id=str(uuid4()),
        patient_id=str(uuid4()),
        workspace_id=str(uuid4()),
        workspace_type=WorkspaceType.INDIVIDUAL,
        active_role_type="individual_owner",
        purpose_code="individual_summary",
        access_decision_id=str(uuid4()),
        access_predicate_hash="access-hash",
        health_thread_id=str(uuid4()),
        evidence_bundle_id=str(uuid4()),
        provenance_completeness=ProvenanceCompleteness.COMPLETE,
        c10_policy_version="c10.v1",
        deterministic_ruleset_version="rules.v1",
        nemo_guardrails_config_id="nemo.v1",
        llama_guard_policy_version="llama.v1",
        risk_tier_policy_version="tiers.v1",
        correlation_id="corr-1",
    )
    return request.model_dump(mode="json")


def test_evaluate_returns_render_token_for_safe_output():
    client = TestClient(app)

    response = client.post(
        "/evaluate",
        json=_request_payload("Your uploaded note reports fatigue."),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == C10Decision.ALLOW_WITH_OBLIGATIONS
    assert payload["render_token"]["binds_text_sha256"] == payload["effective_text_sha256"]
    assert payload["audit"]["primary_event_name"] == "ai_output.allowed_with_obligations"


def test_evaluate_blocks_diagnostic_output():
    client = TestClient(app)

    response = client.post("/evaluate", json=_request_payload("You have lupus."))

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == C10Decision.BLOCK
    assert payload["original_text_allowed"] is False
    assert "C10_DIAGNOSIS_ASSERTION" in payload["reason_codes"]
