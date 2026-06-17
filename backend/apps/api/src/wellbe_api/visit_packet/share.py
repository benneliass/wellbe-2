"""Share-time C10 gate + share-link token helpers for visit packets.

At share time we assemble the included statements into one text, build a C10
claim map (one entry per statement, classified + source-linked), and run the
fail-closed C10 evaluator. A ``new_ai_diagnosis`` statement, an unsupported
claim, or any diagnosis assertion blocks the share. Absent statements are
modelled as ``meta_or_disclaimer`` (they assert a known gap, not a health claim).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from wellbe_contracts.c10_safety import (
    C10SafetyEvaluationRequestV1,
    C10SafetyEvaluationResponseV1,
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
from wellbe_contracts.visit_packet import StatementClassification

from wellbe_api.config import ApiSettings
from wellbe_api.visit_packet.models import StatementRow

_settings = ApiSettings()

_POLICY_VERSION = "vp-c10-v1"

# Decision taxonomy -> C10 ClaimType. Absent statements are handled separately
# as meta_or_disclaimer (they assert a known gap, not a health claim).
_CLAIM_TYPE_MAP = {
    StatementClassification.DIRECT_SOURCE_FACT: ClaimType.PERSONAL_FACT,
    StatementClassification.PATIENT_REPORTED: ClaimType.PATIENT_REPORTED,
    StatementClassification.GENERATED_SYNTHESIS: ClaimType.DERIVED_PATTERN,
    StatementClassification.GENERATED_INFERENCE: ClaimType.DERIVED_PATTERN,
    StatementClassification.SOURCE_RECORD_DIAGNOSIS: ClaimType.SOURCE_RECORD_DIAGNOSIS,
    StatementClassification.NEW_AI_DIAGNOSIS: ClaimType.NEW_AI_DIAGNOSIS,
}


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mint_share_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token is shown to the user once."""
    token = secrets.token_urlsafe(32)
    return token, sha256_hex(token)


def _evidence_ref(statement: StatementRow) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for idx, sr in enumerate(statement.source_refs or []):
        refs.append(
            EvidenceRef(
                evidence_ref_id=f"{statement.id}:{idx}",
                ref_type=EvidenceRefType.EXTRACTED_FACT,
                source_type=SourceType.PATIENT_ENTERED_NOTE,
                source_id=str(sr.get("source_id", statement.id)),
            )
        )
    return refs


def build_share_evaluation_request(
    *,
    statements: list[StatementRow],
    patient_id: uuid.UUID,
    purpose: str,
    correlation_id: str,
    packet_id: uuid.UUID,
) -> C10SafetyEvaluationRequestV1:
    included = [s for s in statements if s.included]

    parts: list[str] = []
    claim_map: list[ClaimMapEntry] = []
    cursor = 0
    for s in included:
        text = s.text
        start = cursor
        end = start + len(text)
        cursor = end + 1  # account for the joining newline

        if s.absent:
            claim_type = ClaimType.META_OR_DISCLAIMER
            evidence_refs: list[EvidenceRef] = []
        else:
            claim_type = _CLAIM_TYPE_MAP.get(
                StatementClassification(s.classification), ClaimType.PERSONAL_FACT
            )
            evidence_refs = _evidence_ref(s)

        claim_map.append(
            ClaimMapEntry(
                claim_id=str(s.id),
                char_start=start,
                char_end=end,
                claim_type=claim_type,
                personal_specific=not s.absent,
                external_context_only=False,
                evidence_refs=evidence_refs,
                provenance_complete=True,
                uncertainty_label="patient_prepared",
            )
        )
        parts.append(text)

    output_text = "\n".join(parts)
    has_claims = bool(claim_map)

    return C10SafetyEvaluationRequestV1(
        request_id=str(uuid.uuid4()),
        requested_at=datetime.now(UTC),
        idempotency_key=f"visit-packet-share:{packet_id}",
        output_text=output_text,
        output_format=OutputFormat.STRUCTURED_BLOCKS,
        output_type=OutputType.VISIT_PACKET,
        target_audience="clinician",
        surface="visit_packet_share",
        review_markers=[
            ReviewMarker.PATIENT_ENTERED,
            ReviewMarker.NOT_CLINICIAN_REVIEWED,
            ReviewMarker.READY_FOR_VISIT,
        ],
        urgency=UrgencyContext(
            urgency_class=UrgencyClass.NONE, urgency_source=UrgencySource.NONE
        ),
        claim_map=claim_map,
        claim_map_complete=True,
        no_health_claims_asserted=not has_claims,
        engine_name="visit_packet_composer",
        engine_version="1.0",
        engine_risk_tier=EngineRiskTier.MEDIUM,
        upstream_run_id=str(packet_id),
        actor_id=str(patient_id),
        workspace_id=str(patient_id),
        workspace_type=WorkspaceType.INDIVIDUAL,
        active_role_type="controller",
        purpose_code=purpose,
        access_decision_id="self",
        access_predicate_hash="self",
        c10_policy_version=_POLICY_VERSION,
        deterministic_ruleset_version=_POLICY_VERSION,
        nemo_guardrails_config_id=_POLICY_VERSION,
        llama_guard_policy_version=_POLICY_VERSION,
        risk_tier_policy_version=_POLICY_VERSION,
        correlation_id=correlation_id,
        patient_id=str(patient_id),
        visit_packet_id=str(packet_id),
        provenance_completeness=(
            ProvenanceCompleteness.COMPLETE
            if has_claims
            else ProvenanceCompleteness.NOT_APPLICABLE_NO_HEALTH_CLAIMS
        ),
    )


def run_share_gate(
    *,
    statements: list[StatementRow],
    patient_id: uuid.UUID,
    purpose: str,
    correlation_id: str,
    packet_id: uuid.UUID,
) -> C10SafetyEvaluationResponseV1:
    from wellbe_c10_safety import SafetyGateEvaluator

    evaluator = SafetyGateEvaluator(
        token_secret=_settings.c10_token_secret.get_secret_value()
    )
    request = build_share_evaluation_request(
        statements=statements,
        patient_id=patient_id,
        purpose=purpose,
        correlation_id=correlation_id,
        packet_id=packet_id,
    )
    return evaluator.evaluate(request)
