from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from wellbe_c10_safety import SafetyGateEvaluator
from wellbe_contracts.c10_safety import (
    AccessValidationResult,
    C10Decision,
    C10ReasonCode,
    C10SafetyEvaluationRequestV1,
    ClaimMapEntry,
    ClaimType,
    EngineRiskTier,
    EvidenceRef,
    EvidenceRefType,
    GuardrailResult,
    GuardrailStatus,
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


class _PassGuardrail:
    def __init__(self) -> None:
        self.called = False

    def evaluate(self, request: C10SafetyEvaluationRequestV1) -> GuardrailResult:
        self.called = True
        return GuardrailResult(status=GuardrailStatus.PASS, reason_codes=[])


class _TimeoutGuardrail:
    def evaluate(self, request: C10SafetyEvaluationRequestV1) -> GuardrailResult:
        return GuardrailResult(
            status=GuardrailStatus.TIMEOUT,
            reason_codes=[C10ReasonCode.C10_GUARDRAIL_UNAVAILABLE],
        )


class _AccessValidator:
    def validate(self, request: C10SafetyEvaluationRequestV1) -> AccessValidationResult:
        return AccessValidationResult(allow=True)


def _safe_request(
    *,
    text: str = "Your uploaded note reports fatigue after the March lab result.",
    output_type: OutputType = OutputType.THREAD_SUMMARY,
    engine_risk_tier: EngineRiskTier = EngineRiskTier.LOW,
    claim_map: list[ClaimMapEntry] | None = None,
    provenance_completeness: ProvenanceCompleteness = ProvenanceCompleteness.COMPLETE,
    review_markers: list[ReviewMarker] | None = None,
    urgency: UrgencyContext | None = None,
) -> C10SafetyEvaluationRequestV1:
    if claim_map is None:
        evidence = EvidenceRef(
            evidence_ref_id=str(uuid4()),
            ref_type=EvidenceRefType.RAW_CONTEXT_EVENT,
            source_type=SourceType.PATIENT_ENTERED_NOTE,
            source_id=str(uuid4()),
        )
        claim_map = [
            ClaimMapEntry(
                claim_id="claim-1",
                char_start=0,
                char_end=len(text),
                claim_type=ClaimType.PATIENT_REPORTED,
                personal_specific=True,
                external_context_only=False,
                evidence_refs=[evidence],
                provenance_complete=True,
            )
        ]

    return C10SafetyEvaluationRequestV1(
        request_id=str(uuid4()),
        requested_at=datetime.now(UTC),
        idempotency_key="idem-1",
        output_text=text,
        output_format=OutputFormat.PLAIN_TEXT,
        output_type=output_type,
        target_audience="individual",
        surface="individual_workspace",
        review_markers=review_markers
        if review_markers is not None
        else [ReviewMarker.AI_SUMMARIZED, ReviewMarker.NOT_CLINICIAN_REVIEWED],
        urgency=urgency
        if urgency is not None
        else UrgencyContext(
            urgency_class=UrgencyClass.NONE,
            urgency_source=UrgencySource.NONE,
        ),
        claim_map=claim_map,
        claim_map_complete=True,
        no_health_claims_asserted=False,
        engine_name="thread-summary",
        engine_version="0.1.0",
        engine_risk_tier=engine_risk_tier,
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
        provenance_completeness=provenance_completeness,
        c10_policy_version="c10.v1",
        deterministic_ruleset_version="rules.v1",
        nemo_guardrails_config_id="nemo.v1",
        llama_guard_policy_version="llama.v1",
        risk_tier_policy_version="tiers.v1",
        correlation_id="corr-1",
    )


def test_allows_safe_sourced_text_with_obligations_and_render_token():
    evaluator = SafetyGateEvaluator(
        access_validator=_AccessValidator(),
        nemo_guardrail=_PassGuardrail(),
        llama_guard=_PassGuardrail(),
        token_secret="test-secret",
    )

    request = _safe_request()
    response = evaluator.evaluate(request)

    assert response.decision == C10Decision.ALLOW_WITH_OBLIGATIONS
    assert response.original_text_allowed is True
    assert response.render_token is not None
    assert response.render_token.binds_text_sha256 == request.text_sha256
    assert response.audit.primary_event_name == "ai_output.allowed_with_obligations"
    assert {obligation.type for obligation in response.obligations} >= {
        "display_review_markers",
        "display_source_refs",
    }


def test_diagnosis_assertion_blocks_before_model_guardrails():
    nemo = _PassGuardrail()
    llama = _PassGuardrail()
    evaluator = SafetyGateEvaluator(
        access_validator=_AccessValidator(),
        nemo_guardrail=nemo,
        llama_guard=llama,
        token_secret="test-secret",
    )

    response = evaluator.evaluate(_safe_request(text="You have lupus."))

    assert response.decision == C10Decision.BLOCK
    assert response.original_text_allowed is False
    assert C10ReasonCode.C10_DIAGNOSIS_ASSERTION in response.reason_codes
    assert response.audit.primary_event_name == "ai_output.blocked"
    assert nemo.called is False
    assert llama.called is False


def test_missing_claim_map_fails_closed():
    request = _safe_request(claim_map=[])

    response = SafetyGateEvaluator(
        access_validator=_AccessValidator(),
        nemo_guardrail=_PassGuardrail(),
        llama_guard=_PassGuardrail(),
        token_secret="test-secret",
    ).evaluate(request)

    assert response.decision == C10Decision.FAIL_CLOSED
    assert C10ReasonCode.C10_CONTRACT_INVALID in response.reason_codes
    assert response.audit.primary_event_name == "ai_output.fail_closed"


def test_external_evidence_personalized_as_fact_blocks():
    text = "This paper proves your fatigue is caused by X."
    claim = ClaimMapEntry(
        claim_id="claim-1",
        char_start=0,
        char_end=len(text),
        claim_type=ClaimType.EXTERNAL_CONTEXT,
        personal_specific=True,
        external_context_only=False,
        evidence_refs=[
            EvidenceRef(
                evidence_ref_id=str(uuid4()),
                ref_type=EvidenceRefType.EXTERNAL_SOURCE,
                source_type=SourceType.PEER_REVIEWED_PAPER,
                source_id=str(uuid4()),
            )
        ],
        provenance_complete=True,
    )

    response = SafetyGateEvaluator(
        access_validator=_AccessValidator(),
        nemo_guardrail=_PassGuardrail(),
        llama_guard=_PassGuardrail(),
        token_secret="test-secret",
    ).evaluate(
        _safe_request(
            text=text,
            output_type=OutputType.EXTERNAL_RESEARCH_RELEVANCE,
            engine_risk_tier=EngineRiskTier.HIGH,
            claim_map=[claim],
        )
    )

    assert response.decision == C10Decision.BLOCK
    assert C10ReasonCode.C10_EXTERNAL_EVIDENCE_PERSONALIZED in response.reason_codes


def test_guardrail_timeout_fails_closed():
    response = SafetyGateEvaluator(
        access_validator=_AccessValidator(),
        nemo_guardrail=_TimeoutGuardrail(),
        llama_guard=_PassGuardrail(),
        token_secret="test-secret",
    ).evaluate(_safe_request())

    assert response.decision == C10Decision.FAIL_CLOSED
    assert C10ReasonCode.C10_GUARDRAIL_UNAVAILABLE in response.reason_codes
    assert response.audit.primary_event_name == "ai_output.fail_closed"
