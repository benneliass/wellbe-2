"""Pure exploration-session policy for one pinned walk.

A null terminal and supported_leaf keep the session inspectable and rewindable.
policy_blocked, authorization_changed, stale_snapshot, and dependency_unavailable release it.
budget_exhausted and insufficient_independent_evidence release it: the design leaves them closed.
approximate_frontier_exhausted releases it.
Rewind cuts an on-path node to the tip. Forward items are frontier rows expanded from that tip.
Open advertisements stay at three. Issued actions stay within seven and keep a fallback when one
was present.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from wellbe_raw_context_brain.types import RouteKind, TerminalReason

_OPEN_NODE_CAP = 3
_ISSUED_TOTAL_CAP = 7


@dataclass(frozen=True)
class TruncatedPath:
    visited: tuple[str, ...]


@dataclass(frozen=True)
class RewindTargetError:
    error: Literal["rewind_target"]


class FrontierRef(Protocol):
    @property
    def node_id(self) -> str: ...

    @property
    def from_id(self) -> str: ...


class IssuedAction(Protocol):
    @property
    def kind(self) -> RouteKind: ...


def retains_session(terminal: TerminalReason | None) -> bool:
    """True while the session stays inspectable.

    supported_leaf has no eligible forward node and remains rewindable.
    A null terminal means the walk can continue.
    """
    match terminal:
        case None | "supported_leaf":
            return True
        case (
            "approximate_frontier_exhausted"
            | "budget_exhausted"
            | "policy_blocked"
            | "authorization_changed"
            | "stale_snapshot"
            | "dependency_unavailable"
            | "insufficient_independent_evidence"
        ):
            return False


def truncate_path(visited: Sequence[str], target_id: str) -> TruncatedPath | RewindTargetError:
    """Cuts visited so target_id is the new tip.

    A target that is already the tip returns the same path.
    A target absent from the path returns rewind_target and leaves the input path unchanged.
    """
    if visited and visited[-1] == target_id:
        return TruncatedPath(visited=tuple(visited))
    try:
        index = visited.index(target_id)
    except ValueError:
        return RewindTargetError(error="rewind_target")
    return TruncatedPath(visited=tuple(visited[: index + 1]))


def forward_items[F: FrontierRef](items: Sequence[F], tip_id: str) -> list[F]:
    """Frontier rows whose from_id is the current tip.

    Earlier expansions stay off the forward set.
    """
    return [item for item in items if item.from_id == tip_id]


def bound_forward_actions(count: float) -> int:
    """Open-node advertisements, clamped to at most three."""
    if not math.isfinite(count) or count < 1:
        return 0
    return min(_OPEN_NODE_CAP, math.floor(count))


def select_issued_actions[A: IssuedAction](actions: Sequence[A]) -> list[A]:
    """The same list, limited to three neighbour actions and seven actions in total.

    When a fallback is present it stays in the result.
    With enough candidates the issued length sits between three and seven.
    """
    neighbour_count = sum(1 for action in actions if action.kind == "neighbour")
    open_budget = bound_forward_actions(neighbour_count)
    fallback_at = _fallback_index(actions)
    selected: list[A] = []
    opens = 0
    for index, action in enumerate(actions):
        if action.kind == "neighbour" and opens >= open_budget:
            continue
        reserve_fallback = fallback_at > index
        limit = _ISSUED_TOTAL_CAP - 1 if reserve_fallback else _ISSUED_TOTAL_CAP
        if len(selected) >= limit:
            continue
        if action.kind == "neighbour":
            opens += 1
        selected.append(action)
    return selected


def _fallback_index(actions: Sequence[IssuedAction]) -> int:
    for index, action in enumerate(actions):
        if action.kind == "fallback":
            return index
    return -1
