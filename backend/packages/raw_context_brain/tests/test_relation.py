"""Relation names."""

from __future__ import annotations

from wellbe_raw_context_brain.relation import map_relation


def test_keeps_a_possible_conflict_distinct_from_a_possible_association() -> None:
    assert map_relation("model", "possible_conflict") == "possible_inconsistency"
    assert map_relation("model", "shared_context") == "possible_semantic_association"
    assert map_relation("policy", "derived_or_copied") == "derived_or_copied"
