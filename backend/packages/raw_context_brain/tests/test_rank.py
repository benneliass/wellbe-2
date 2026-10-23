"""Rank order and digest."""

from __future__ import annotations

import hashlib

from wellbe_raw_context_brain.rank import apply_hysteresis, compare_rank
from wellbe_raw_context_brain.text import sha256
from wellbe_raw_context_brain.types import Rankable


def _rank(event_id: str, **partial: float) -> Rankable:
    values = {
        "authorized": 1.0,
        "provenance": 1.0,
        "relevance": 0.0,
        "novelty": 0.0,
        "inverse_degree": 0.0,
        "inverse_hop": 0.0,
    }
    values.update(partial)
    return Rankable(id=event_id, **values)


def test_hashes_with_sha256() -> None:
    assert sha256("wellbe") == hashlib.sha256(b"wellbe").hexdigest()


def test_orders_authorization_before_relevance_before_degree() -> None:
    blocked = _rank("b", authorized=0, relevance=1)
    allowed = _rank("a", authorized=1, relevance=0.1)
    assert compare_rank(allowed, blocked) < 0


def test_lets_a_closer_match_beat_a_more_specific_note() -> None:
    hub = _rank("hub", relevance=0.9, inverse_degree=0.1)
    specific = _rank("leaf", relevance=0.8, inverse_degree=1)
    assert compare_rank(hub, specific) < 0


def test_uses_degree_only_when_the_match_ties() -> None:
    hub = _rank("hub", relevance=0.8, inverse_degree=0.1)
    specific = _rank("leaf", relevance=0.8, inverse_degree=1)
    assert compare_rank(specific, hub) < 0


def test_keeps_a_nearly_equal_previous_route() -> None:
    ranked = [{"id": "new", "relevance": 0.52}, {"id": "old", "relevance": 0.5}]
    held = apply_hysteresis(ranked, "old")
    assert [item["id"] for item in held.ranked] == ["old", "new"]
    assert held.held_previous is True


def test_does_not_hold_a_previous_note_that_loses_on_a_higher_key() -> None:
    ranked = [
        _rank("new", provenance=2, relevance=0.52),
        _rank("old", provenance=0, relevance=0.5),
    ]
    held = apply_hysteresis(ranked, "old")
    assert [item.id for item in held.ranked] == ["new", "old"]
    assert held.held_previous is False
