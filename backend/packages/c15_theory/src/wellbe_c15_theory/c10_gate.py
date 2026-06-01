"""Route a theory's user-facing text through the C10 Safety & Governance Gate.

C15 consumes C10 via its stable evaluator contract — it does not modify C10.
Every user-facing theory output must pass C10 before it is shown or summarised
into C8 (decision §4.5). The gate result is stored verbatim on the evaluation.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from wellbe_c10_safety import SafetyGateEvaluator
from wellbe_contracts.c10_safety import (
    C10SafetyEvaluationRequestV1,
    C10SafetyEvaluationResponseV1,
    ClaimMapEntry,
    ClaimType,
    EngineRiskTier,
    OutputFormat,
    OutputType,
    ProvenanceCompleteness,
    ReviewMarker,
    UrgencyActionPath,
    UrgencyClass,
    UrgencyContext,
    UrgencySource,
)
from wellbe_contracts.c15_theory import TheorySafetyLevel

_POLICY_VERSION = "c15-theory-v1"


def _evaluator() -> SafetyGateEvaluator:
    secret = os.environ.get("C10_TOKEN_SECRET", "local-dev-secret")
    return SafetyGateEvaluator(token_secret=secret)


def evaluate_theory_output(
    *,
    theory_id: uuid.UUID,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    output_text: str,
    safety_level: TheorySafetyLevel,
    correlation_id: str,
    trace_id: str,
) -> C10SafetyEvaluationResponseV1:
    """Build a valid C10 request for the theory question and evaluate it.

    The theory question asserts no personal health claim (it is phrased as a
    question), so it carries a single meta/disclaimer claim and
    NOT_APPLICABLE_NO_HEALTH_CLAIMS provenance.
    """
    now = datetime.now(UTC)
    request_id = str(uuid.uuid4())

    if safety_level is TheorySafetyLevel.URGENT_SYMPTOM_PRESENT:
        urgency = UrgencyContext(
            urgency_class=UrgencyClass.RED,
            urgency_source=UrgencySource.PATTERN_DETECTION,
            action_path=UrgencyActionPath(
                type="seek_care_now",
                display_text="Some of your recent data may need urgent attention. "
                "Please contact a clinician or emergency services.",
            ),
        )
        markers = [
            ReviewMarker.NOT_CLINICIAN_REVIEWED,
            ReviewMarker.NEEDS_URGENT_CARE_CONSIDERATION,
        ]
    else:
        urgency = UrgencyContext(urgency_class=UrgencyClass.NONE, urgency_source=UrgencySource.NONE)
        markers = [ReviewMarker.NOT_CLINICIAN_REVIEWED, ReviewMarker.AI_SUMMARIZED]

    claim = ClaimMapEntry(
        claim_id="theory-question",
        char_start=0,
        char_end=len(output_text),
        claim_type=ClaimType.META_OR_DISCLAIMER,
        personal_specific=False,
        external_context_only=False,
        evidence_refs=[],
        provenance_complete=True,
    )

    request = C10SafetyEvaluationRequestV1(
        request_id=request_id,
        requested_at=now,
        idempotency_key=f"theory:{theory_id}:{request_id}",
        output_text=output_text,
        output_format=OutputFormat.PLAIN_TEXT,
        output_type=OutputType.THEORY_EVALUATION,
        target_audience="individual",
        surface="theory_detail",
        review_markers=markers,
        urgency=urgency,
        claim_map=[claim],
        claim_map_complete=True,
        no_health_claims_asserted=False,
        engine_name="c15_theory_service",
        engine_version="0.1.0",
        engine_risk_tier=EngineRiskTier.HIGH,
        upstream_run_id=request_id,
        actor_id=str(actor_id) if actor_id else str(patient_id),
        workspace_id=str(patient_id),
        workspace_type="individual",
        active_role_type="owner",
        purpose_code="theory_evaluation",
        access_decision_id=str(uuid.uuid4()),
        access_predicate_hash="n/a",
        c10_policy_version=_POLICY_VERSION,
        deterministic_ruleset_version="v1",
        nemo_guardrails_config_id="default",
        llama_guard_policy_version="default",
        risk_tier_policy_version="v1",
        correlation_id=correlation_id,
        patient_id=str(patient_id),
        theory_id=str(theory_id),
        provenance_completeness=ProvenanceCompleteness.NOT_APPLICABLE_NO_HEALTH_CLAIMS,
        trace_id=trace_id,
    )
    return _evaluator().evaluate(request)
