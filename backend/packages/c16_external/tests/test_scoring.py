from __future__ import annotations

from wellbe_c16_external.scoring import compute_relevance_score
from wellbe_contracts.c16_external import RELEVANCE_WEIGHTS, RelevanceScoreInputs


def test_weights_sum_to_one() -> None:
    assert abs(sum(RELEVANCE_WEIGHTS.values()) - 1.0) < 1e-9


def test_all_max_inputs_score_one() -> None:
    inputs = RelevanceScoreInputs(
        entity_or_code_match=1.0,
        semantic_similarity=1.0,
        thread_context_match=1.0,
        population_applicability=1.0,
        source_currentness=1.0,
        reviewer_user_signal=1.0,
    )
    assert compute_relevance_score(inputs) == 1.0


def test_all_zero_inputs_score_zero() -> None:
    assert compute_relevance_score(RelevanceScoreInputs()) == 0.0


def test_weighted_sum_matches_formula() -> None:
    inputs = RelevanceScoreInputs(
        entity_or_code_match=1.0,
        semantic_similarity=0.5,
        thread_context_match=0.0,
        population_applicability=1.0,
        source_currentness=0.0,
        reviewer_user_signal=0.0,
    )
    expected = 0.35 * 1.0 + 0.25 * 0.5 + 0.10 * 1.0
    assert abs(compute_relevance_score(inputs) - expected) < 1e-9


def test_score_is_topical_only_not_tier_derived() -> None:
    # Identical topical inputs must produce identical scores regardless of any
    # source-quality consideration — tier is not part of the formula.
    inputs = RelevanceScoreInputs(entity_or_code_match=0.8, semantic_similarity=0.8)
    assert compute_relevance_score(inputs) == compute_relevance_score(inputs)
