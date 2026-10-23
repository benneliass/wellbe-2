"""Bounded selection for one person's ranked candidates.

LAB_CAP of 2 is a lab stand-in for lineage, source type, facet, and route reason.
These caps are not the open product parameters.
A referral is an id already on a neighbor list. There is no second hop.
The caller judges. This module only proposes the next controller-checked ids.
Same-person checks stay with the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Protocol

from wellbe_raw_context_brain.types import Judgment, PruneRecord

# Lab stand-in. Not a product X, Y, or keyword floor.
LAB_CAP = 2

_CAPS = (
    ("lineage", "lineage_cap"),
    ("source_type", "source_type_cap"),
    ("facet", "facet_cap"),
    ("reason", "reason_cap"),
)


@dataclass(frozen=True)
class NeighborRef:
    id: str
    relevance: float


@dataclass(frozen=True)
class RankedCandidate:
    id: str
    lineage: str
    source_type: str
    facet: str
    reason: str
    captured_at: str
    relevance: float
    neighbors: tuple[NeighborRef, ...]


@dataclass(frozen=True)
class SelectionInput:
    """Already ranked. Earlier array position is the higher rank.

    captured_at is subject time. When present, reserve at most one earlier and one later
    candidate.
    """

    candidates: tuple[RankedCandidate, ...]
    captured_at: str | None = None


@dataclass(frozen=True)
class SelectionResult:
    kept: tuple[str, ...]
    pruned: tuple[PruneRecord, ...]
    referrals: tuple[str, ...]


@dataclass(frozen=True)
class JudgedCandidate:
    id: str
    judgment: Judgment
    relevance: float
    neighbors: tuple[NeighborRef, ...]


@dataclass(frozen=True)
class ReferralRoundInput:
    judged: tuple[JudgedCandidate, ...]
    tried: tuple[str, ...]


@dataclass(frozen=True)
class ReferralRound:
    referrals: tuple[str, ...]


class _ReferralSource(Protocol):
    @property
    def relevance(self) -> float: ...

    @property
    def neighbors(self) -> tuple[NeighborRef, ...]: ...


def apply_selection(selection: SelectionInput) -> SelectionResult:
    counts = _empty_counts()
    kept: set[str] = set()
    kept_order: list[str] = []
    if selection.captured_at:
        _reserve(selection.candidates, selection.captured_at, "earlier", kept, kept_order, counts)
        _reserve(selection.candidates, selection.captured_at, "later", kept, kept_order, counts)

    pruned: list[PruneRecord] = []
    for candidate in selection.candidates:
        if candidate.id in kept:
            continue
        reason = _cap_reason(candidate, counts)
        if reason is not None:
            pruned.append(PruneRecord(id=candidate.id, reason=reason))
            continue
        _remember(candidate, kept, kept_order, counts)

    pruned_ids = {row.id for row in pruned}
    sources = tuple(candidate for candidate in selection.candidates if candidate.id in pruned_ids)
    return SelectionResult(
        kept=tuple(kept_order),
        pruned=tuple(pruned),
        referrals=tuple(_propose_referrals(sources, kept)),
    )


def apply_referral_round(round_input: ReferralRoundInput) -> ReferralRound:
    """After judgment. Non-link judgments may propose untried neighbors.

    Judged ids count as tried. A link judgment proposes nothing.
    """
    tried = set(round_input.tried)
    for item in round_input.judged:
        tried.add(item.id)
    sources = tuple(item for item in round_input.judged if item.judgment != "link")
    return ReferralRound(referrals=tuple(_propose_referrals(sources, tried)))


def _reserve(
    candidates: Sequence[RankedCandidate],
    subject: str,
    direction: str,
    kept: set[str],
    kept_order: list[str],
    counts: dict[str, dict[str, int]],
) -> None:
    for candidate in candidates:
        if not candidate.captured_at:
            continue
        earlier = candidate.captured_at < subject
        later = candidate.captured_at > subject
        if direction == "earlier" and not earlier:
            continue
        if direction == "later" and not later:
            continue
        if candidate.id in kept:
            return
        if _cap_reason(candidate, counts) is not None:
            continue
        _remember(candidate, kept, kept_order, counts)
        return


def _propose_referrals(sources: Sequence[_ReferralSource], blocked: AbstractSet[str]) -> list[str]:
    referrals: list[str] = []
    taken = set(blocked)
    for source in sources:
        for neighbor in source.neighbors:
            if len(referrals) >= LAB_CAP:
                return referrals
            if neighbor.id in taken:
                continue
            if neighbor.relevance <= source.relevance:
                continue
            referrals.append(neighbor.id)
            taken.add(neighbor.id)
    return referrals


def _remember(
    candidate: RankedCandidate,
    kept: set[str],
    kept_order: list[str],
    counts: dict[str, dict[str, int]],
) -> None:
    kept.add(candidate.id)
    kept_order.append(candidate.id)
    for name, _reason in _CAPS:
        value = _cap_value(candidate, name)
        counts[name][value] = counts[name].get(value, 0) + 1


def _cap_reason(candidate: RankedCandidate, counts: dict[str, dict[str, int]]) -> str | None:
    for name, reason in _CAPS:
        if counts[name].get(_cap_value(candidate, name), 0) >= LAB_CAP:
            return reason
    return None


def _cap_value(candidate: RankedCandidate, name: str) -> str:
    if name == "lineage":
        return candidate.lineage
    if name == "source_type":
        return candidate.source_type
    if name == "facet":
        return candidate.facet
    if name == "reason":
        return candidate.reason
    raise AssertionError(name)


def _empty_counts() -> dict[str, dict[str, int]]:
    return {"lineage": {}, "source_type": {}, "facet": {}, "reason": {}}
