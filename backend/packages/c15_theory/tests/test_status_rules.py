from __future__ import annotations

from wellbe_c15_theory.status_rules import status_from_personal_evidence
from wellbe_contracts.c15_theory import TheoryStatus


def test_no_evidence_needs_more_data() -> None:
    assert (
        status_from_personal_evidence(evidence_for=0, evidence_against=0, has_missing_data=False)
        is TheoryStatus.NEEDS_MORE_DATA
    )


def test_support_only_is_partially_supported() -> None:
    assert (
        status_from_personal_evidence(evidence_for=2, evidence_against=0, has_missing_data=False)
        is TheoryStatus.PARTIALLY_SUPPORTED
    )


def test_support_with_missing_data_downgrades() -> None:
    assert (
        status_from_personal_evidence(evidence_for=2, evidence_against=0, has_missing_data=True)
        is TheoryStatus.NEEDS_MORE_DATA
    )


def test_contradiction_only() -> None:
    assert (
        status_from_personal_evidence(evidence_for=0, evidence_against=1, has_missing_data=False)
        is TheoryStatus.CONTRADICTED_BY_CURRENT_DATA
    )


def test_mixed_signals_never_overstate() -> None:
    assert (
        status_from_personal_evidence(evidence_for=3, evidence_against=1, has_missing_data=False)
        is TheoryStatus.NEEDS_MORE_DATA
    )


def test_status_is_never_diagnostic() -> None:
    # Sanity: status taxonomy never contains a confirmed/ruled_out value.
    values = {s.value for s in TheoryStatus}
    assert "confirmed" not in values
    assert "ruled_out" not in values
    assert "diagnosed" not in values
