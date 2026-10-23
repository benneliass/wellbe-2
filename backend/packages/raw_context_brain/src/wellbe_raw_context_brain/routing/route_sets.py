"""Three policy route sets for one person: candidate, selected, and export.

These are policy objects, not Links and not a network protocol.
Each publication appends a revision. A revision is never overwritten.
Revision numbers belong to this log. They are never reused.
Nothing here joins one person's ids with another person's ids.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from wellbe_raw_context_brain.types import PruneRecord

ROUTE_SET_NAMES = ("candidate", "selected", "export")
RouteSetName = Literal["candidate", "selected", "export"]

DISCOVERY_SOURCES = ("exact", "neighbor", "hnsw", "referral")
DiscoverySource = Literal["exact", "neighbor", "hnsw", "referral"]

_HOPS: tuple[tuple[RouteSetName, RouteSetName], ...] = (
    ("candidate", "selected"),
    ("selected", "export"),
)


@dataclass(frozen=True)
class RouteProvenance:
    """Per-id derivation recorded with the revision that published it."""

    discovery: DiscoverySource
    rank: int
    prune_reason: str | None
    export_handle: str | None = None


@dataclass(frozen=True)
class RouteSetsSnapshot:
    candidate: tuple[str, ...]
    selected: tuple[str, ...]
    export: tuple[str, ...]


@dataclass(frozen=True)
class RouteTransition:
    """One hop in this revision.

    entered and left are ids that entered or left the destination set since the previous
    revision for this person. The first revision compares with an empty destination.
    from_ is the lab field `from`.
    """

    revision: int
    from_: RouteSetName
    to: RouteSetName
    entered: tuple[str, ...]
    left: tuple[str, ...]


@dataclass(frozen=True)
class RouteRevision:
    person_id: str
    revision: int
    sets: RouteSetsSnapshot
    provenance: dict[str, RouteProvenance]
    transitions: tuple[RouteTransition, ...]


@dataclass(frozen=True)
class RoutePublication:
    person_id: str
    sets: RouteSetsSnapshot
    provenance: Mapping[str, RouteProvenance]


_EMPTY_SETS = RouteSetsSnapshot(candidate=(), selected=(), export=())


class RouteSetLog:
    def __init__(self) -> None:
        self._by_person: dict[str, list[RouteRevision]] = {}
        self._by_revision: dict[int, RouteRevision] = {}
        self._next_revision = 1

    def publish(self, publication: RoutePublication) -> RouteRevision:
        revision = self._next_revision
        self._next_revision += 1
        history = self._by_person.get(publication.person_id)
        previous = history[-1] if history else None
        previous_sets = None if previous is None else previous.sets
        stored = RouteRevision(
            person_id=publication.person_id,
            revision=revision,
            sets=_copy_sets(publication.sets),
            provenance=_copy_provenance(publication.provenance),
            transitions=_transitions_for(revision, previous_sets, publication.sets),
        )
        if history is None:
            history = []
            self._by_person[publication.person_id] = history
        history.append(stored)
        self._by_revision[revision] = stored
        return _copy_revision(stored)

    def latest(self, person_id: str) -> RouteRevision | None:
        history = self._by_person.get(person_id)
        if not history:
            return None
        return _copy_revision(history[-1])

    def history(self, person_id: str) -> list[RouteRevision]:
        return [_copy_revision(row) for row in self._by_person.get(person_id, ())]

    def prune_audit(self, revision: int) -> list[PruneRecord]:
        found = self._by_revision.get(revision)
        if found is None:
            return []
        ranked: list[tuple[int, str, str]] = []
        for record_id, row in found.provenance.items():
            reason = row.prune_reason
            if reason is None:
                continue
            ranked.append((row.rank, record_id, reason))
        ranked.sort(key=lambda item: (item[0], item[1]))
        return [PruneRecord(id=record_id, reason=reason) for _rank, record_id, reason in ranked]


def create_route_sets() -> RouteSetLog:
    return RouteSetLog()


def _transitions_for(
    revision: int,
    previous: RouteSetsSnapshot | None,
    nxt: RouteSetsSnapshot,
) -> tuple[RouteTransition, ...]:
    before = _EMPTY_SETS if previous is None else previous
    rows: list[RouteTransition] = []
    for source, destination in _HOPS:
        entered, left = _membership_change(_ids(before, destination), _ids(nxt, destination))
        rows.append(
            RouteTransition(
                revision=revision,
                from_=source,
                to=destination,
                entered=entered,
                left=left,
            )
        )
    return tuple(rows)


def _ids(sets: RouteSetsSnapshot, name: RouteSetName) -> tuple[str, ...]:
    if name == "candidate":
        return sets.candidate
    if name == "selected":
        return sets.selected
    return sets.export


def _membership_change(
    before: Sequence[str],
    after: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    before_ids = set(before)
    after_ids = set(after)
    entered = tuple(record_id for record_id in after if record_id not in before_ids)
    left = tuple(record_id for record_id in before if record_id not in after_ids)
    return entered, left


def _copy_sets(sets: RouteSetsSnapshot) -> RouteSetsSnapshot:
    return RouteSetsSnapshot(
        candidate=tuple(sets.candidate),
        selected=tuple(sets.selected),
        export=tuple(sets.export),
    )


def _copy_provenance(provenance: Mapping[str, RouteProvenance]) -> dict[str, RouteProvenance]:
    return {
        record_id: RouteProvenance(
            discovery=row.discovery,
            rank=row.rank,
            prune_reason=row.prune_reason,
            export_handle=row.export_handle,
        )
        for record_id, row in provenance.items()
    }


def _copy_revision(revision: RouteRevision) -> RouteRevision:
    return RouteRevision(
        person_id=revision.person_id,
        revision=revision.revision,
        sets=_copy_sets(revision.sets),
        provenance=_copy_provenance(revision.provenance),
        transitions=tuple(
            RouteTransition(
                revision=transition.revision,
                from_=transition.from_,
                to=transition.to,
                entered=tuple(transition.entered),
                left=tuple(transition.left),
            )
            for transition in revision.transitions
        ),
    )
