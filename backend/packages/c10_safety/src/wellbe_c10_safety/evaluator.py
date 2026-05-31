from __future__ import annotations

import base64
import hmac
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol
from uuid import uuid4

from wellbe_contracts.c10_safety import (
    AccessValidationResult,
    C10AuditMetadata,
    C10Decision,
    C10Obligation,
    C10ReasonCode,
    C10SafetyEvaluationRequestV1,
    C10SafetyEvaluationResponseV1,
    ClaimType,
    GuardrailResult,
    GuardrailStatus,
    LayerResult,
    LayerStatus,
    ProvenanceCompleteness,
    RenderToken,
    ReviewMarker,
    UrgencyClass,
)


class AccessValidator(Protocol):
    def validate(self, request: C10SafetyEvaluationRequestV1) -> AccessValidationResult: ...


class Guardrail(Protocol):
    def evaluate(self, request: C10SafetyEvaluationRequestV1) -> GuardrailResult: ...


class AllowAllAccessValidator:
    def validate(self, request: C10SafetyEvaluationRequestV1) -> AccessValidationResult:
        return AccessValidationResult(allow=True)


class PassingGuardrail:
    def evaluate(self, request: C10SafetyEvaluationRequestV1) -> GuardrailResult:
        return GuardrailResult(status=GuardrailStatus.PASS)


class SafetyGateEvaluator:
    """Synchronous C10 evaluator with deterministic hard rules before model guardrails."""

    _DIAGNOSIS_PATTERNS = (
        re.compile(r"\byou\s+(?:definitely\s+|certainly\s+)?have\s+[a-z][a-z0-9 -]*", re.I),
        re.compile(r"\bthis\s+is\s+(?:definitely\s+|certainly\s+)?[a-z][a-z0-9 -]*", re.I),
    )
    _EXTERNAL_PERSONALIZATION_PATTERNS = (
        re.compile(r"\b(?:paper|study|guideline|source)\s+proves\s+your\b", re.I),
        re.compile(r"\bcaused\s+by\b", re.I),
    )

    def __init__(
        self,
        *,
        access_validator: AccessValidator | None = None,
        nemo_guardrail: Guardrail | None = None,
        llama_guard: Guardrail | None = None,
        token_secret: str,
    ) -> None:
        self._access_validator = access_validator or AllowAllAccessValidator()
        self._nemo_guardrail = nemo_guardrail or PassingGuardrail()
        self._llama_guard = llama_guard or PassingGuardrail()
        self._token_secret = token_secret.encode("utf-8")

    def evaluate(self, request: C10SafetyEvaluationRequestV1) -> C10SafetyEvaluationResponseV1:
        try:
            return self._evaluate(request)
        except Exception:
            return self._response(
                request=request,
                decision=C10Decision.FAIL_CLOSED,
                reason_codes=[C10ReasonCode.C10_CONTRACT_INVALID],
                layer_results={
                    "schema_validation": LayerResult(
                        status=LayerStatus.FAIL_CLOSED,
                        reason_codes=[C10ReasonCode.C10_CONTRACT_INVALID],
                    )
                },
            )

    def _evaluate(self, request: C10SafetyEvaluationRequestV1) -> C10SafetyEvaluationResponseV1:
        layer_results: dict[str, LayerResult] = {}

        contract_reasons = self._validate_contract(request)
        if contract_reasons:
            layer_results["schema_validation"] = LayerResult(
                status=LayerStatus.FAIL_CLOSED,
                reason_codes=contract_reasons,
            )
            return self._response(
                request=request,
                decision=C10Decision.FAIL_CLOSED,
                reason_codes=contract_reasons,
                layer_results=layer_results,
            )
        layer_results["schema_validation"] = LayerResult(status=LayerStatus.PASS)

        access_result = self._access_validator.validate(request)
        if not access_result.allow:
            reasons = access_result.reason_codes or [C10ReasonCode.C10_ACCESS_SCOPE_VIOLATION]
            layer_results["access_validation"] = LayerResult(
                status=LayerStatus.FAIL_CLOSED,
                reason_codes=reasons,
            )
            return self._response(
                request=request,
                decision=C10Decision.FAIL_CLOSED,
                reason_codes=reasons,
                layer_results=layer_results,
            )
        layer_results["access_validation"] = LayerResult(status=LayerStatus.PASS)

        deterministic_reasons = self._run_deterministic_rules(request)
        if deterministic_reasons:
            layer_results["deterministic_rules"] = LayerResult(
                status=LayerStatus.BLOCK,
                reason_codes=deterministic_reasons,
            )
            return self._response(
                request=request,
                decision=C10Decision.BLOCK,
                reason_codes=deterministic_reasons,
                layer_results=layer_results,
            )
        layer_results["deterministic_rules"] = LayerResult(status=LayerStatus.PASS)

        nemo_result = self._nemo_guardrail.evaluate(request)
        if nemo_result.status != GuardrailStatus.PASS:
            return self._guardrail_failure_response(
                request=request,
                layer_name="nemo_guardrails",
                guardrail_result=nemo_result,
                layer_results=layer_results,
            )
        layer_results["nemo_guardrails"] = LayerResult(status=LayerStatus.PASS)

        llama_result = self._llama_guard.evaluate(request)
        if llama_result.status != GuardrailStatus.PASS:
            return self._guardrail_failure_response(
                request=request,
                layer_name="llama_guard",
                guardrail_result=llama_result,
                layer_results=layer_results,
            )
        layer_results["llama_guard"] = LayerResult(status=LayerStatus.PASS)

        obligations = self._obligations(request)
        decision = (
            C10Decision.ALLOW_WITH_OBLIGATIONS if obligations else C10Decision.ALLOW
        )
        layer_results["final_contract_validation"] = LayerResult(status=LayerStatus.PASS)
        return self._response(
            request=request,
            decision=decision,
            reason_codes=[],
            layer_results=layer_results,
            obligations=obligations,
        )

    def _validate_contract(self, request: C10SafetyEvaluationRequestV1) -> list[C10ReasonCode]:
        reasons: list[C10ReasonCode] = []
        if not request.review_markers:
            reasons.append(C10ReasonCode.C10_REVIEW_MARKER_MISSING)
        if not request.no_health_claims_asserted and not request.claim_map:
            reasons.append(C10ReasonCode.C10_CONTRACT_INVALID)
        if not request.claim_map_complete:
            reasons.append(C10ReasonCode.C10_CONTRACT_INVALID)
        if request.provenance_completeness == ProvenanceCompleteness.ABSENT:
            reasons.append(C10ReasonCode.C10_PROVENANCE_MISSING)
        if (
            request.urgency.urgency_class in {UrgencyClass.ORANGE, UrgencyClass.RED}
            and request.urgency.action_path is None
        ):
            reasons.append(C10ReasonCode.C10_URGENCY_WITHOUT_ACTION)
        return reasons

    def _run_deterministic_rules(
        self, request: C10SafetyEvaluationRequestV1
    ) -> list[C10ReasonCode]:
        reasons: list[C10ReasonCode] = []
        text = request.output_text
        if any(pattern.search(text) for pattern in self._DIAGNOSIS_PATTERNS):
            reasons.append(C10ReasonCode.C10_DIAGNOSIS_ASSERTION)

        for claim in request.claim_map:
            if claim.claim_type != ClaimType.META_OR_DISCLAIMER and not claim.evidence_refs:
                reasons.append(C10ReasonCode.C10_PROVENANCE_MISSING)
            if not claim.provenance_complete:
                reasons.append(C10ReasonCode.C10_PROVENANCE_MISSING)
            if claim.claim_type == ClaimType.EXTERNAL_CONTEXT and (
                claim.personal_specific or not claim.external_context_only
            ):
                reasons.append(C10ReasonCode.C10_EXTERNAL_EVIDENCE_PERSONALIZED)

        if any(pattern.search(text) for pattern in self._EXTERNAL_PERSONALIZATION_PATTERNS):
            has_external_claim = any(
                claim.claim_type == ClaimType.EXTERNAL_CONTEXT for claim in request.claim_map
            )
            if has_external_claim:
                reasons.append(C10ReasonCode.C10_EXTERNAL_EVIDENCE_PERSONALIZED)

        return list(dict.fromkeys(reasons))

    def _guardrail_failure_response(
        self,
        *,
        request: C10SafetyEvaluationRequestV1,
        layer_name: str,
        guardrail_result: GuardrailResult,
        layer_results: dict[str, LayerResult],
    ) -> C10SafetyEvaluationResponseV1:
        reasons = guardrail_result.reason_codes or [C10ReasonCode.C10_GUARDRAIL_UNAVAILABLE]
        if guardrail_result.status in {GuardrailStatus.ERROR, GuardrailStatus.TIMEOUT}:
            status = LayerStatus.FAIL_CLOSED
            decision = C10Decision.FAIL_CLOSED
        else:
            status = LayerStatus.BLOCK
            decision = C10Decision.BLOCK
        layer_results[layer_name] = LayerResult(status=status, reason_codes=reasons)
        return self._response(
            request=request,
            decision=decision,
            reason_codes=reasons,
            layer_results=layer_results,
        )

    def _obligations(self, request: C10SafetyEvaluationRequestV1) -> list[C10Obligation]:
        obligations = [
            C10Obligation(
                type="display_review_markers",
                markers=request.review_markers,
            )
        ]
        claim_ids = [
            claim.claim_id
            for claim in request.claim_map
            if claim.claim_type != ClaimType.META_OR_DISCLAIMER
        ]
        if claim_ids:
            obligations.append(
                C10Obligation(type="display_source_refs", claim_ids=claim_ids)
            )
        if ReviewMarker.NOT_CLINICIAN_REVIEWED in request.review_markers:
            obligations.append(
                C10Obligation(type="display_uncertainty_language", claim_ids=claim_ids)
            )
        return obligations

    def _response(
        self,
        *,
        request: C10SafetyEvaluationRequestV1,
        decision: C10Decision,
        reason_codes: list[C10ReasonCode],
        layer_results: dict[str, LayerResult],
        obligations: list[C10Obligation] | None = None,
    ) -> C10SafetyEvaluationResponseV1:
        evaluated_at = datetime.now(UTC)
        allowed = decision in {
            C10Decision.ALLOW,
            C10Decision.ALLOW_WITH_OBLIGATIONS,
            C10Decision.ROUTE_URGENT,
        }
        effective_text = request.output_text if allowed else None
        return C10SafetyEvaluationResponseV1(
            evaluation_id=str(uuid4()),
            request_id=request.request_id,
            evaluated_at=evaluated_at,
            decision=decision,
            original_text_allowed=allowed,
            effective_text=effective_text,
            effective_text_sha256=request.text_sha256 if allowed else None,
            render_token=self._render_token(request, evaluated_at) if allowed else None,
            obligations=obligations or [],
            reason_codes=reason_codes,
            layer_results=layer_results,
            audit=C10AuditMetadata(primary_event_name=self._audit_event_name(decision)),
        )

    def _render_token(
        self, request: C10SafetyEvaluationRequestV1, issued_at: datetime
    ) -> RenderToken:
        payload = f"{request.request_id}:{request.text_sha256}:{issued_at.isoformat()}"
        signature = hmac.new(self._token_secret, payload.encode("utf-8"), sha256).digest()
        token = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return RenderToken(
            token=token,
            binds_request_id=request.request_id,
            binds_text_sha256=request.text_sha256,
            expires_at=issued_at + timedelta(minutes=5),
        )

    def _audit_event_name(self, decision: C10Decision) -> str:
        return {
            C10Decision.ALLOW: "ai_output.allowed",
            C10Decision.ALLOW_WITH_OBLIGATIONS: "ai_output.allowed_with_obligations",
            C10Decision.REWRITE_REQUIRED: "ai_output.rewrite_required",
            C10Decision.BLOCK: "ai_output.blocked",
            C10Decision.ROUTE_URGENT: "ai_output.routed_urgent",
            C10Decision.MANUAL_REVIEW_REQUIRED: "ai_output.manual_review_required",
            C10Decision.FAIL_CLOSED: "ai_output.fail_closed",
        }[decision]
