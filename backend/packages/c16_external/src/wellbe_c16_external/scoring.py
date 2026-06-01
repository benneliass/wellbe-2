"""Relevance scoring (v1) for the Research Relevance engine (C16 / WEL-117).

This computes *topical relatedness* between a personal fact and an external
source/claim. It is deliberately NOT diagnostic confidence and NOT C5/C6
``potential_score`` — it never asserts anything is true about the user.

Source quality tier is intentionally absent from this formula: a low-quality
anecdote can be topically relevant but must surface with a low tier + warning.
Tier governs surfacing caps/labels at the presentation layer, not relatedness.
"""

from __future__ import annotations

from wellbe_contracts.c16_external import (
    RELEVANCE_WEIGHTS,
    RelevanceScoreInputs,
)


def compute_relevance_score(inputs: RelevanceScoreInputs) -> float:
    """Weighted sum of per-signal inputs, clamped to [0, 1].

    Weights sum to 1.0, so the result is already in range; the clamp guards
    against float drift and any future weight changes.
    """
    raw = (
        RELEVANCE_WEIGHTS["entity_or_code_match"] * inputs.entity_or_code_match
        + RELEVANCE_WEIGHTS["semantic_similarity"] * inputs.semantic_similarity
        + RELEVANCE_WEIGHTS["thread_context_match"] * inputs.thread_context_match
        + RELEVANCE_WEIGHTS["population_applicability"] * inputs.population_applicability
        + RELEVANCE_WEIGHTS["source_currentness"] * inputs.source_currentness
        + RELEVANCE_WEIGHTS["reviewer_user_signal"] * inputs.reviewer_user_signal
    )
    return max(0.0, min(1.0, raw))
