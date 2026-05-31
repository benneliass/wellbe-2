from __future__ import annotations

import pytest

from wellbe_contracts.c5_evidence import EvidenceLinkType

from wellbe_c6_graph.scoring import (
    CONTRADICTION_PENALTY,
    PotentialScoreComputer,
    ScoreInput,
)


@pytest.fixture
def scorer():
    return PotentialScoreComputer()


class TestPotentialScoreComputer:
    def test_empty_inputs_returns_zero(self, scorer: PotentialScoreComputer):
        result = scorer.compute([])
        assert result.potential_score == 0.0
        assert result.score_inputs["evidence_count"] == 0

    def test_single_primary_high_confidence(self, scorer: PotentialScoreComputer):
        result = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.95,
                edge_category="causal",
            )
        ])
        assert result.potential_score == 0.95
        assert result.score_version == 1

    def test_single_primary_low_confidence(self, scorer: PotentialScoreComputer):
        result = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.50,
                edge_category="causal",
            )
        ])
        assert result.potential_score == 0.50

    def test_corroborating_adds_less_weight(self, scorer: PotentialScoreComputer):
        primary_only = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.80,
                edge_category="correlation",
            )
        ])
        with_corroboration = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.80,
                edge_category="correlation",
            ),
            ScoreInput(
                link_type=EvidenceLinkType.CORROBORATING,
                confidence=0.70,
                edge_category="correlation",
            ),
        ])
        assert with_corroboration.potential_score > primary_only.potential_score

    def test_contradiction_reduces_score(self, scorer: PotentialScoreComputer):
        without_contradiction = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.90,
                edge_category="causal",
            )
        ])
        with_contradiction = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.90,
                edge_category="causal",
            ),
            ScoreInput(
                link_type=EvidenceLinkType.CONTRADICTING,
                confidence=0.80,
                edge_category="causal",
            ),
        ])
        assert with_contradiction.potential_score < without_contradiction.potential_score
        assert with_contradiction.score_inputs["has_contradiction"] is True

    def test_score_always_in_zero_one_range(self, scorer: PotentialScoreComputer):
        result = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.CONTRADICTING,
                confidence=1.0,
                edge_category="causal",
            ),
            ScoreInput(
                link_type=EvidenceLinkType.CONTRADICTING,
                confidence=1.0,
                edge_category="causal",
            ),
        ])
        assert result.potential_score >= 0.0
        assert result.potential_score <= 1.0

    def test_contextual_has_small_weight(self, scorer: PotentialScoreComputer):
        result = scorer.compute([
            ScoreInput(
                link_type=EvidenceLinkType.CONTEXTUAL,
                confidence=0.90,
                edge_category="correlation",
            )
        ])
        assert result.potential_score > 0.0
        assert result.potential_score < 1.0
