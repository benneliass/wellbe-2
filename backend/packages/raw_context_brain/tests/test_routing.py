"""Route revisions, pending interest, selection caps, referrals, and retry."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from wellbe_raw_context_brain.routing.interest import (
    InterestBudgets,
    PendingBegin,
    RejectedBegin,
    SatisfiedBegin,
    SemanticInterest,
    create_pending_interest_table,
)
from wellbe_raw_context_brain.routing.retry import (
    AttemptInput,
    StopDecision,
    WaitDecision,
    schedule_attempt,
)
from wellbe_raw_context_brain.routing.route_sets import (
    DiscoverySource,
    RouteProvenance,
    RoutePublication,
    RouteSetsSnapshot,
    RouteTransition,
    create_route_sets,
)
from wellbe_raw_context_brain.routing.selection import (
    JudgedCandidate,
    NeighborRef,
    RankedCandidate,
    ReferralRoundInput,
    SelectionInput,
    apply_referral_round,
    apply_selection,
)
from wellbe_raw_context_brain.types import PruneRecord

_PERSON = "person-1"


def _provenance(
    discovery: DiscoverySource,
    rank: int,
    prune_reason: str | None,
    export_handle: str | None = None,
) -> RouteProvenance:
    return RouteProvenance(
        discovery=discovery,
        rank=rank,
        prune_reason=prune_reason,
        export_handle=export_handle,
    )


def _interest(**overrides: Any) -> SemanticInterest:
    base = SemanticInterest(
        person_id=_PERSON,
        purpose="inspect",
        authorization_epoch=1,
        snapshot_revision=4,
        snapshot_digest="digest-a",
        budgets=InterestBudgets(deadline_ms=50, max_in_flight=2),
        operation="open",
        nonce="nonce-1",
    )
    return replace(base, **overrides)


def _candidate(
    id: str,
    *,
    lineage: str | None = None,
    source_type: str | None = None,
    facet: str | None = None,
    reason: str | None = None,
    captured_at: str = "2024-06-01",
    relevance: float = 0,
    neighbors: tuple[NeighborRef, ...] = (),
) -> RankedCandidate:
    return RankedCandidate(
        id=id,
        lineage=id if lineage is None else lineage,
        source_type=id if source_type is None else source_type,
        facet=id if facet is None else facet,
        reason=id if reason is None else reason,
        captured_at=captured_at,
        relevance=relevance,
        neighbors=neighbors,
    )


def test_route_set_revisions_append_and_keep_the_earlier_publication() -> None:
    log = create_route_sets()
    first = log.publish(
        RoutePublication(
            person_id=_PERSON,
            sets=RouteSetsSnapshot(
                candidate=("a", "b", "c", "e"),
                selected=("a", "b"),
                export=("a",),
            ),
            provenance={
                "a": _provenance("exact", 0, None, "rh_a"),
                "b": _provenance("neighbor", 1, None),
                "e": _provenance("exact", 2, "lineage_cap"),
                "c": _provenance("hnsw", 3, "facet_cap"),
            },
        )
    )

    assert first.revision == 1
    assert first.transitions == (
        RouteTransition(
            revision=1,
            from_="candidate",
            to="selected",
            entered=("a", "b"),
            left=(),
        ),
        RouteTransition(
            revision=1,
            from_="selected",
            to="export",
            entered=("a",),
            left=(),
        ),
    )
    assert log.prune_audit(1) == [
        PruneRecord(id="e", reason="lineage_cap"),
        PruneRecord(id="c", reason="facet_cap"),
    ]

    second = log.publish(
        RoutePublication(
            person_id=_PERSON,
            sets=RouteSetsSnapshot(
                candidate=("a", "d"),
                selected=("d",),
                export=("d",),
            ),
            provenance={
                "a": _provenance("exact", 1, "reason_cap"),
                "d": _provenance("referral", 0, None, "rh_d"),
            },
        )
    )

    assert second.revision == 2
    assert second.transitions == (
        RouteTransition(
            revision=2,
            from_="candidate",
            to="selected",
            entered=("d",),
            left=("a", "b"),
        ),
        RouteTransition(
            revision=2,
            from_="selected",
            to="export",
            entered=("d",),
            left=("a",),
        ),
    )
    assert [row.revision for row in log.history(_PERSON)] == [1, 2]
    assert log.history(_PERSON)[0] == first
    assert log.latest(_PERSON) == second
    assert log.prune_audit(2) == [PruneRecord(id="a", reason="reason_cap")]

    third = log.publish(
        RoutePublication(
            person_id=_PERSON,
            sets=second.sets,
            provenance=second.provenance,
        )
    )
    assert third.revision == 3
    assert third.transitions == (
        RouteTransition(revision=3, from_="candidate", to="selected", entered=(), left=()),
        RouteTransition(revision=3, from_="selected", to="export", entered=(), left=()),
    )
    assert log.history(_PERSON)[1] == second
    latest = log.latest(_PERSON)
    assert latest is not None
    assert latest.revision == 3

    other = log.publish(
        RoutePublication(
            person_id="person-2",
            sets=RouteSetsSnapshot(candidate=("x",), selected=("x",), export=()),
            provenance={"x": _provenance("exact", 0, None)},
        )
    )
    assert other.transitions[0] == RouteTransition(
        revision=other.revision,
        from_="candidate",
        to="selected",
        entered=("x",),
        left=(),
    )
    assert len(log.history(_PERSON)) == 3
    latest_other = log.latest("person-2")
    assert latest_other is not None
    assert latest_other.sets.candidate == ("x",)
    assert len(log.history("person-2")) == 1


async def test_pending_interest_coalesces_replays_and_rejects_a_different_purpose() -> None:
    table = create_pending_interest_table()
    first = _interest()
    opened = table.begin(first, "anchor-a")
    assert isinstance(opened, PendingBegin)
    assert opened.state == "pending"
    assert opened.nonce == "nonce-1"
    assert opened.joined is False

    joined = table.begin(_interest(nonce="nonce-2"), "anchor-a")
    assert isinstance(joined, PendingBegin)
    assert joined.state == "pending"
    assert joined.nonce == "nonce-1"
    assert joined.joined is True
    assert joined.done is opened.done

    other_snapshot = table.begin(_interest(nonce="nonce-3", snapshot_revision=9), "anchor-a")
    assert isinstance(other_snapshot, PendingBegin)
    assert other_snapshot.state == "pending"
    assert other_snapshot.nonce == "nonce-3"
    assert other_snapshot.joined is False

    assert table.begin(_interest(purpose="share"), "anchor-a") == RejectedBegin(
        state="rejected",
        reason="wrong_purpose",
    )
    replay = table.begin(first, "anchor-a")
    assert isinstance(replay, PendingBegin)
    assert replay.state == "pending"
    assert replay.nonce == "nonce-1"
    assert replay.joined is False

    table.satisfy("nonce-1", {"page": 1})
    assert await opened.done == {"page": 1}
    table.satisfy("nonce-1", {"page": 2})

    assert table.begin(first, "other-key") == SatisfiedBegin(
        state="satisfied",
        nonce="nonce-1",
        result={"page": 1},
    )

    again = table.begin(_interest(nonce="nonce-4"), "anchor-a")
    assert isinstance(again, PendingBegin)
    assert again.state == "pending"
    assert again.nonce == "nonce-4"
    assert again.joined is False

    table.clear()
    reopened = table.begin(first, "anchor-a")
    assert isinstance(reopened, PendingBegin)
    assert reopened.state == "pending"
    assert reopened.nonce == "nonce-1"
    assert reopened.joined is False


def test_selection_reserves_one_earlier_and_one_later_and_caps_a_facet_at_two() -> None:
    result = apply_selection(
        SelectionInput(
            captured_at="2024-06-01",
            candidates=(
                _candidate(
                    "same-1",
                    lineage="l1",
                    source_type="note",
                    facet="sleep",
                    reason="r1",
                    relevance=0.9,
                ),
                _candidate(
                    "same-2",
                    lineage="l2",
                    source_type="lab",
                    facet="sleep",
                    reason="r2",
                    relevance=0.8,
                    neighbors=(
                        NeighborRef(id="closer-a", relevance=0.95),
                        NeighborRef(id="weaker", relevance=0.2),
                    ),
                ),
                _candidate(
                    "earlier",
                    lineage="l3",
                    source_type="pdf",
                    facet="sleep",
                    reason="r3",
                    captured_at="2024-01-01",
                    relevance=0.5,
                ),
                _candidate(
                    "later",
                    lineage="l4",
                    source_type="image",
                    facet="knee",
                    reason="r4",
                    captured_at="2024-08-01",
                    relevance=0.45,
                ),
                _candidate(
                    "fourth-sleep",
                    lineage="l5",
                    source_type="letter",
                    facet="sleep",
                    reason="r5",
                    captured_at="2024-03-01",
                    relevance=0.3,
                    neighbors=(NeighborRef(id="closer-b", relevance=0.7),),
                ),
            ),
        )
    )

    assert result.kept == ("earlier", "later", "same-1")
    assert result.pruned == (
        PruneRecord(id="same-2", reason="facet_cap"),
        PruneRecord(id="fourth-sleep", reason="facet_cap"),
    )
    assert result.referrals == ("closer-a", "closer-b")


def test_referral_round_proposes_one_round_of_closer_neighbors_after_a_no_link() -> None:
    no_link = apply_referral_round(
        ReferralRoundInput(
            judged=(
                JudgedCandidate(
                    id="a",
                    judgment="no_link",
                    relevance=0.4,
                    neighbors=(
                        NeighborRef(id="seen", relevance=0.95),
                        NeighborRef(id="b", relevance=0.7),
                        NeighborRef(id="low", relevance=0.4),
                        NeighborRef(id="c", relevance=0.8),
                        NeighborRef(id="d", relevance=0.9),
                    ),
                ),
                JudgedCandidate(
                    id="linked",
                    judgment="link",
                    relevance=0.1,
                    neighbors=(NeighborRef(id="not-proposed", relevance=1),),
                ),
            ),
            tried=("a", "linked", "seen"),
        )
    )
    assert no_link.referrals == ("b", "c")

    uncertain = apply_referral_round(
        ReferralRoundInput(
            judged=(
                JudgedCandidate(
                    id="u",
                    judgment="uncertain",
                    relevance=0.2,
                    neighbors=(
                        NeighborRef(id="n", relevance=0.5),
                        NeighborRef(id="m", relevance=0.4),
                    ),
                ),
            ),
            tried=("u",),
        )
    )
    assert uncertain.referrals == ("n", "m")


def test_retry_schedule_stops_on_the_deadline_and_on_overload() -> None:
    base = AttemptInput(
        attempt=0,
        now=1_000,
        started_at=1_000,
        deadline_ms=50,
        base_ms=10,
        in_flight=0,
        max_in_flight=2,
        seed=4,
    )

    assert schedule_attempt(replace(base, now=1_050)) == WaitDecision(action="wait", delay_ms=11)
    assert schedule_attempt(replace(base, now=1_051)) == StopDecision(
        action="stop",
        reason="dependency_unavailable",
    )
    assert schedule_attempt(replace(base, in_flight=2)) == StopDecision(
        action="stop",
        reason="dependency_unavailable",
    )
    assert schedule_attempt(replace(base, attempt=1)) == WaitDecision(action="wait", delay_ms=22)
    assert schedule_attempt(replace(base, attempt=2)) == WaitDecision(action="wait", delay_ms=40)
    assert schedule_attempt(replace(base, attempt=3)) == StopDecision(
        action="stop",
        reason="dependency_unavailable",
    )
