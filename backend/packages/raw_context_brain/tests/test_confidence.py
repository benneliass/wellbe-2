"""Suggestion readings, confidence movement, and clinical wording."""

from __future__ import annotations

import re
from dataclasses import asdict

from wellbe_raw_context_brain.confidence import (
    NextConfidenceInput,
    association_phrase,
    is_clinical_reason,
    next_confidence,
    read_suggestion,
)
from wellbe_raw_context_brain.types import Judgment, Origin


def test_treats_uncertain_as_an_abstain_that_adds_nothing() -> None:
    reading = read_suggestion("uncertain")
    assert reading == read_suggestion("uncertain")
    assert asdict(reading) == {"kind": "uncertain", "adds_suggestion": False}
    assert reading.kind != "no_link"


def test_keeps_link_and_no_link_as_suggestions() -> None:
    assert asdict(read_suggestion("link")) == {"kind": "link", "adds_suggestion": True}
    assert asdict(read_suggestion("no_link")) == {"kind": "no_link", "adds_suggestion": True}


def test_does_not_carry_a_flag_that_removes_a_kept_link() -> None:
    judgments: tuple[Judgment, ...] = ("link", "no_link", "uncertain")
    for judgment in judgments:
        assert sorted(asdict(read_suggestion(judgment))) == ["adds_suggestion", "kind"]


_SAME = NextConfidenceInput(
    origin="model",
    proposed=0,
    existing_confidence=None,
    existing_lineages=("line-a", "line-b"),
    evidence_lineages=("line-b", "line-a"),
)


def test_returns_a_first_model_proposal_when_no_edge_exists_yet() -> None:
    assert (
        next_confidence(
            NextConfidenceInput(
                origin="model",
                proposed=0.95,
                existing_confidence=None,
                existing_lineages=(),
                evidence_lineages=("line-a",),
            )
        )
        == 0.95
    )


def test_does_not_let_the_same_evidence_set_raise_confidence() -> None:
    assert (
        next_confidence(
            NextConfidenceInput(
                origin="model",
                proposed=0.95,
                existing_confidence=0.4,
                existing_lineages=_SAME.existing_lineages,
                evidence_lineages=_SAME.evidence_lineages,
            )
        )
        == 0.4
    )


def test_allows_the_same_evidence_set_to_lower_confidence() -> None:
    assert (
        next_confidence(
            NextConfidenceInput(
                origin="model",
                proposed=0.2,
                existing_confidence=0.4,
                existing_lineages=_SAME.existing_lineages,
                evidence_lineages=_SAME.evidence_lineages,
            )
        )
        == 0.2
    )


def test_lets_a_new_independent_lineage_move_confidence_up_or_down() -> None:
    assert (
        next_confidence(
            NextConfidenceInput(
                origin="model",
                proposed=0.95,
                existing_confidence=0.4,
                existing_lineages=("line-a", "line-b"),
                evidence_lineages=("line-a", "line-c"),
            )
        )
        == 0.95
    )
    assert (
        next_confidence(
            NextConfidenceInput(
                origin="model",
                proposed=0.15,
                existing_confidence=0.4,
                existing_lineages=("line-a",),
                evidence_lineages=("line-a", "line-c"),
            )
        )
        == 0.15
    )


def test_returns_a_user_correction_unchanged() -> None:
    origins: tuple[Origin, ...] = ("user_correction", "policy")
    for origin in origins:
        assert (
            next_confidence(
                NextConfidenceInput(
                    origin=origin,
                    proposed=0.95,
                    existing_confidence=0.4,
                    existing_lineages=_SAME.existing_lineages,
                    evidence_lineages=_SAME.evidence_lineages,
                )
            )
            == 0.95
        )
        assert (
            next_confidence(
                NextConfidenceInput(
                    origin=origin,
                    proposed=0.1,
                    existing_confidence=0.9,
                    existing_lineages=_SAME.existing_lineages,
                    evidence_lineages=_SAME.evidence_lineages,
                )
            )
            == 0.1
        )


def test_returns_a_number_rather_than_an_edge_removal_flag() -> None:
    confidence = next_confidence(
        NextConfidenceInput(
            origin="model",
            proposed=0.2,
            existing_confidence=0.4,
            existing_lineages=("line-a",),
            evidence_lineages=("line-a",),
        )
    )
    assert isinstance(confidence, float)


def test_offers_a_short_conditional_association_without_clinical_claims() -> None:
    phrase = association_phrase()
    assert phrase.endswith(".")
    assert len(phrase) < 80
    assert re.search(r"\bmay\b", phrase, re.IGNORECASE)
    assert re.search(r"diagnos|cause|severity|cancer", phrase, re.IGNORECASE) is None


def test_rejects_a_clinical_reason_code_as_a_link_reason() -> None:
    assert is_clinical_reason("diagnosis of cancer") is True
    assert is_clinical_reason("DIAGNOSIS") is True
    assert is_clinical_reason("severity") is True
    assert is_clinical_reason("caused by") is True
    assert is_clinical_reason("heart disease") is True
    assert is_clinical_reason("shared_context") is False
    assert is_clinical_reason("insufficient_overlap") is False
    assert is_clinical_reason("recorded_association") is False
    assert is_clinical_reason("user_correction") is False
    assert is_clinical_reason("possible_conflict") is False
