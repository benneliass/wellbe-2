"""Unit tests for the visit-packet C10 pre-share gate (WEL-30).

Verifies the decision guarantees without a DB: a clean source-linked packet is
allowed, a new AI-generated diagnosis is blocked, absent statements are treated
as meta (no spurious provenance failure), and an unsourced summary claim is
blocked.
"""

from __future__ import annotations

import uuid

from wellbe_api.visit_packet.models import StatementRow
from wellbe_api.visit_packet.share import build_share_evaluation_request, run_share_gate
from wellbe_contracts.c10_safety import C10Decision, ClaimType
from wellbe_contracts.visit_packet import (
    AbsenceReason,
    PacketLayer,
    PacketSection,
    StatementClassification,
)


def _stmt(
    *,
    text: str,
    classification: StatementClassification,
    source_refs: list[dict] | None = None,
    absent: bool = False,
    absence_reason: AbsenceReason | None = None,
    included: bool = True,
    layer: PacketLayer = PacketLayer.SUMMARY,
    section: PacketSection = PacketSection.CONCERN,
) -> StatementRow:
    return StatementRow(
        id=uuid.uuid4(),
        packet_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        layer=layer.value,
        section=section.value,
        ordinal=0,
        text=text,
        classification=classification.value,
        source_refs=source_refs if source_refs is not None else [{"source_id": "src-1"}],
        absent=absent,
        absence_reason=absence_reason.value if absence_reason else None,
        included=included,
    )


def _run(statements: list[StatementRow]) -> C10Decision:
    return run_share_gate(
        statements=statements,
        patient_id=uuid.uuid4(),
        purpose="clinician_visit",
        correlation_id="corr-test",
        packet_id=uuid.uuid4(),
    ).decision


def test_clean_source_linked_packet_is_allowed() -> None:
    statements = [
        _stmt(
            text="Persistent cough (current status: active unresolved).",
            classification=StatementClassification.DIRECT_SOURCE_FACT,
        ),
        _stmt(
            text="What could be causing this cough?",
            classification=StatementClassification.PATIENT_REPORTED,
            layer=PacketLayer.PATIENT_PREP,
            section=PacketSection.QUESTION,
        ),
    ]
    assert _run(statements) in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}


def test_new_ai_diagnosis_statement_is_blocked() -> None:
    statements = [
        _stmt(
            text="This pattern indicates early-stage condition X.",
            classification=StatementClassification.NEW_AI_DIAGNOSIS,
        ),
    ]
    assert _run(statements) == C10Decision.BLOCK


def test_absent_statement_does_not_trigger_provenance_failure() -> None:
    statements = [
        _stmt(
            text="No active health concerns are on record for the selected scope.",
            classification=StatementClassification.DIRECT_SOURCE_FACT,
            source_refs=[],
            absent=True,
            absence_reason=AbsenceReason.KNOWN_ABSENT,
        ),
    ]
    # Absent statements are meta_or_disclaimer -> allowed despite no evidence_refs.
    assert _run(statements) in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}


def test_summary_claim_without_source_is_blocked() -> None:
    statements = [
        _stmt(
            text="An unsourced summary statement.",
            classification=StatementClassification.DIRECT_SOURCE_FACT,
            source_refs=[],
        ),
    ]
    assert _run(statements) == C10Decision.BLOCK


def test_claim_map_classification_mapping() -> None:
    statements = [
        _stmt(
            text="Patient-reported symptom.",
            classification=StatementClassification.PATIENT_REPORTED,
        ),
    ]
    request = build_share_evaluation_request(
        statements=statements,
        patient_id=uuid.uuid4(),
        purpose="clinician_visit",
        correlation_id="corr-test",
        packet_id=uuid.uuid4(),
    )
    assert request.claim_map[0].claim_type == ClaimType.PATIENT_REPORTED
    assert request.claim_map_complete is True
    assert request.output_type.value == "visit_packet"
