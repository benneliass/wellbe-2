"""Exploration session retention, rewind, forward frontier, and issued actions."""

from __future__ import annotations

from dataclasses import dataclass

from wellbe_raw_context_brain.routing.session_policy import (
    RewindTargetError,
    TruncatedPath,
    bound_forward_actions,
    forward_items,
    retains_session,
    select_issued_actions,
    truncate_path,
)
from wellbe_raw_context_brain.types import RouteKind, TerminalReason

_CLOSED: tuple[TerminalReason, ...] = (
    "policy_blocked",
    "authorization_changed",
    "stale_snapshot",
    "dependency_unavailable",
    "budget_exhausted",
    "insufficient_independent_evidence",
    "approximate_frontier_exhausted",
)


def test_keeps_a_supported_leaf_inspectable_and_rewindable() -> None:
    assert retains_session("supported_leaf") is True


def test_releases_policy_authorization_snapshot_and_dependency_terminals() -> None:
    reasons: tuple[TerminalReason, ...] = (
        "policy_blocked",
        "authorization_changed",
        "stale_snapshot",
        "dependency_unavailable",
    )
    for reason in reasons:
        assert retains_session(reason) is False


def test_releases_budget_exhaustion_and_insufficient_independent_evidence() -> None:
    assert retains_session("budget_exhausted") is False
    assert retains_session("insufficient_independent_evidence") is False


def test_keeps_a_null_terminal_while_the_walk_can_continue() -> None:
    assert retains_session(None) is True


def test_releases_an_exhausted_approximate_frontier() -> None:
    assert retains_session("approximate_frontier_exhausted") is False


def test_releases_every_terminal_other_than_a_supported_leaf() -> None:
    for reason in _CLOSED:
        assert retains_session(reason) is False


def test_rewind_cuts_the_path_so_the_target_is_the_tip() -> None:
    visited = ["anchor", "mid", "later", "end"]
    assert truncate_path(visited, "mid") == TruncatedPath(visited=("anchor", "mid"))
    assert visited == ["anchor", "mid", "later", "end"]


def test_rewind_returns_the_same_path_when_the_target_is_already_the_tip() -> None:
    visited = ["anchor", "mid", "tip"]
    once = truncate_path(visited, "tip")
    assert once == TruncatedPath(visited=("anchor", "mid", "tip"))
    assert isinstance(once, TruncatedPath)
    assert truncate_path(once.visited, "tip") == TruncatedPath(visited=("anchor", "mid", "tip"))
    assert truncate_path(["a", "b", "a"], "a") == TruncatedPath(visited=("a", "b", "a"))


def test_rewind_returns_rewind_target_when_the_target_is_off_the_path() -> None:
    visited = ["anchor", "mid"]
    assert truncate_path(visited, "other") == RewindTargetError(error="rewind_target")
    assert visited == ["anchor", "mid"]
    assert truncate_path([], "anchor") == RewindTargetError(error="rewind_target")


@dataclass(frozen=True)
class _Frontier:
    node_id: str
    from_id: str


def test_forward_frontier_returns_only_items_expanded_from_the_tip() -> None:
    items = [
        _Frontier(node_id="from-tip", from_id="tip"),
        _Frontier(node_id="sibling", from_id="earlier"),
        _Frontier(node_id="also-from-tip", from_id="tip"),
    ]
    assert forward_items(items, "tip") == [
        _Frontier(node_id="from-tip", from_id="tip"),
        _Frontier(node_id="also-from-tip", from_id="tip"),
    ]
    assert len(items) == 3


def test_forward_frontier_drops_siblings_after_the_tip_moves() -> None:
    items = [
        _Frontier(node_id="old-child", from_id="earlier"),
        _Frontier(node_id="old-sibling", from_id="earlier"),
    ]
    assert forward_items(items, "tip") == []


def test_issued_actions_clamp_open_node_advertisements_to_at_most_three() -> None:
    assert bound_forward_actions(0) == 0
    assert bound_forward_actions(1) == 1
    assert bound_forward_actions(3) == 3
    assert bound_forward_actions(4) == 3
    assert bound_forward_actions(12) == 3


@dataclass(frozen=True)
class _Action:
    kind: RouteKind
    id: str | int | None = None


def test_issued_actions_keep_at_most_three_neighbour_actions() -> None:
    actions = [
        _Action(kind="neighbour", id="n1"),
        _Action(kind="neighbour", id="n2"),
        _Action(kind="facet", id="facet"),
        _Action(kind="neighbour", id="n3"),
        _Action(kind="neighbour", id="n4"),
        _Action(kind="temporal", id="time"),
        _Action(kind="fallback", id="stop"),
    ]
    issued = select_issued_actions(actions)
    neighbour_ids = [action.id for action in issued if action.kind == "neighbour"]
    assert neighbour_ids == ["n1", "n2", "n3"]
    assert [action.id for action in issued] == ["n1", "n2", "facet", "n3", "time", "stop"]
    assert issued[0] is actions[0]
    assert len(actions) == 7


def test_issued_actions_keep_a_fallback_and_stay_within_seven() -> None:
    kinds: tuple[RouteKind, ...] = (
        "facet",
        "facet",
        "temporal",
        "temporal",
        "source",
        "source",
        "facet",
        "fallback",
    )
    actions = [_Action(kind=kind, id=index) for index, kind in enumerate(kinds)]
    issued = select_issued_actions(actions)
    assert len(issued) == 7
    assert [action.kind for action in issued] == [
        "facet",
        "facet",
        "temporal",
        "temporal",
        "source",
        "source",
        "fallback",
    ]
    assert any(action.kind == "fallback" for action in issued)


def test_issued_actions_stay_between_three_and_seven_when_enough_candidates_exist() -> None:
    actions = [
        _Action(kind="neighbour"),
        _Action(kind="neighbour"),
        _Action(kind="neighbour"),
        _Action(kind="neighbour"),
        _Action(kind="facet"),
        _Action(kind="temporal"),
        _Action(kind="source"),
        _Action(kind="facet"),
        _Action(kind="fallback"),
    ]
    issued = select_issued_actions(actions)
    assert len([action for action in issued if action.kind == "neighbour"]) == 3
    assert len(issued) >= 3
    assert len(issued) <= 7
    assert any(action.kind == "fallback" for action in issued)
    assert [action.kind for action in issued] == [
        "neighbour",
        "neighbour",
        "neighbour",
        "facet",
        "temporal",
        "source",
        "fallback",
    ]


def test_issued_actions_leave_a_short_list_unchanged() -> None:
    actions = [_Action(kind="neighbour"), _Action(kind="fallback")]
    assert select_issued_actions(actions) == actions
