"""Bounded navigation."""

from __future__ import annotations

import re
from dataclasses import replace

from wellbe_raw_context_brain.generate import generate_topology
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import (
    ExploreInput,
    JudgeDecision,
    JudgeRequest,
    SemanticData,
    TerminalReason,
    VaultEvent,
)

_REASONS: tuple[TerminalReason, ...] = (
    "supported_leaf",
    "approximate_frontier_exhausted",
    "budget_exhausted",
    "policy_blocked",
    "authorization_changed",
    "stale_snapshot",
    "dependency_unavailable",
    "insufficient_independent_evidence",
)


def _event(event_id: str, text: str) -> VaultEvent:
    return VaultEvent(
        id=event_id,
        person_id="p1",
        captured_at="2024-02-01T00:00:00.000Z",
        source_type="note",
        text=text,
        content_hash=event_id,
        lineage_id=event_id,
        document_id=None,
    )


def _explore(lab: RawContextLab, **kwargs: object) -> SemanticData:
    request_id = kwargs.pop("request_id", "")
    if not isinstance(request_id, str):
        request_id = ""
    return lab.explore(
        ExploreInput(
            person_id=str(kwargs.pop("person_id")),
            purpose=str(kwargs.pop("purpose")),
            request_id=request_id,
            anchor_id=_optional_str(kwargs.pop("anchor_id", None)),
            route_handle=_optional_str(kwargs.pop("route_handle", None)),
            route_id=_optional_str(kwargs.pop("route_id", None)),
            focus_id=_optional_str(kwargs.pop("focus_id", None)),
            operation=_operation(kwargs.pop("operation", "open")),
            rewind_to_id=_optional_str(kwargs.pop("rewind_to_id", None)),
            hold_at_anchor=bool(kwargs.pop("hold_at_anchor", False)),
        )
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _operation(value: object) -> str:
    if value in {"open", "continue", "rewind", "assess_link"}:
        return str(value)
    return "open"


class _EmptyJudge:
    async def judge(self, _request: JudgeRequest) -> list[JudgeDecision]:
        return []


def test_continues_a_saved_frontier_without_a_new_candidate_search() -> None:
    lab = generate_topology(count=20, kind="sparse", seed=4, page_size=3, hop_limit=12)
    searches_before = lab.hnsw_search_count
    first = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n0")
    assert first.route_handle
    assert len(first.items) <= 5
    assert len(first.items) > 0
    assert len(first.next_routes) >= 2
    assert len(first.next_routes) <= 7
    assert any(route.kind == "fallback" for route in first.next_routes)
    searches_after = lab.hnsw_search_count
    second = _explore(
        lab,
        person_id="synthetic-1",
        purpose="nav",
        route_handle=first.route_handle or "",
    )
    assert lab.hnsw_search_count == searches_after
    assert searches_after == searches_before
    first_handles = {item.excerpt for item in first.items}
    assert all(item.excerpt not in first_handles for item in second.items)
    assert "no relevant context" not in second.detail.lower()


def test_stops_a_cycle_instead_of_walking_it_again() -> None:
    lab = generate_topology(count=12, kind="cyclic", seed=5, page_size=6, hop_limit=30)
    response = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n0")
    for _step in range(12):
        if not response.route_handle or response.terminal_reason:
            break
        response = _explore(
            lab,
            person_id="synthetic-1",
            purpose="nav",
            route_handle=response.route_handle,
        )
    assert response.terminal_reason is not None
    assert response.terminal_reason in _REASONS
    assert response.cycle_count > 0


def test_refuses_a_guessed_continuation_id() -> None:
    lab = generate_topology(count=8, kind="sparse", seed=6, page_size=3, hop_limit=20)
    first = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n0")
    handle = first.route_handle or ""
    assert re.fullmatch(r"rh_[0-9a-f]{32}", handle)
    flipped = f"{handle[:-1]}{'b' if handle.endswith('a') else 'a'}"
    guesses = ["rh_0", "rh_1", "rh_2", f"rh_{'0' * 32}", flipped]
    for guess in guesses:
        denied = _explore(lab, person_id="synthetic-1", purpose="nav", route_handle=guess)
        assert denied.terminal_reason == "policy_blocked"
        assert "not recognized" in denied.detail
        assert denied.items == ()
    frontier = None if lab.local_overlay(handle) is None else lab.local_overlay(handle).frontier
    other_person = _explore(lab, person_id="someone-else", purpose="nav", route_handle=handle)
    assert other_person.terminal_reason == "policy_blocked"
    overlay = lab.local_overlay(handle)
    assert overlay is not None
    assert overlay.frontier == frontier


def test_invalidates_a_handle_when_the_snapshot_or_authorization_changes() -> None:
    lab = generate_topology(count=8, kind="sparse", seed=6, page_size=3, hop_limit=20)
    first = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n0")
    handle = first.route_handle or ""
    ad = lab.log.ads[0]
    assert ad
    lab.withdraw(ad.id)
    stale = _explore(lab, person_id="synthetic-1", purpose="nav", route_handle=handle)
    assert stale.terminal_reason == "stale_snapshot"
    assert stale.items == ()
    assert lab.metrics.cache_clears > 0

    fresh = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n1")
    lab.set_authorization_epoch(2)
    denied = _explore(
        lab,
        person_id="synthetic-1",
        purpose="nav",
        route_handle=fresh.route_handle or "",
    )
    assert denied.terminal_reason == "authorization_changed"


def test_expires_a_handle_and_enforces_the_use_limit() -> None:
    now = {"value": 1_000}

    def clock() -> int:
        return now["value"]

    lab = RawContextLab(
        LabOptions(now=clock, handle_ttl_ms=500, max_handle_uses=1, hop_limit=10, page_size=1)
    )
    lab.add_fixture(_event("a", "alpha"))
    lab.add_fixture(_event("b", "beta"))
    lab.add_fixture(_event("c", "gamma"))
    lab.add_fixture(_event("d", "delta"))
    lab.link_structural("a", "b")
    lab.link_structural("b", "c")
    lab.link_structural("c", "d")
    first = _explore(lab, person_id="p1", purpose="nav", anchor_id="a")
    now["value"] = 2_000
    expired = _explore(lab, person_id="p1", purpose="nav", route_handle=first.route_handle or "")
    assert expired.terminal_reason == "policy_blocked"
    assert "expired" in expired.detail

    now["value"] = 1_000
    live = RawContextLab(
        LabOptions(now=clock, handle_ttl_ms=50_000, max_handle_uses=1, hop_limit=10, page_size=1)
    )
    live.add_fixture(_event("a", "alpha"))
    live.add_fixture(_event("b", "beta"))
    live.add_fixture(_event("c", "gamma"))
    live.add_fixture(_event("d", "delta"))
    live.link_structural("a", "b")
    live.link_structural("b", "c")
    live.link_structural("c", "d")
    started = _explore(live, person_id="p1", purpose="nav", anchor_id="a")
    _explore(live, person_id="p1", purpose="nav", route_handle=started.route_handle or "")
    limited = _explore(live, person_id="p1", purpose="nav", route_handle=started.route_handle or "")
    assert "use limit" in limited.detail


def test_names_an_exact_leaf_without_calling_it_missing_context() -> None:
    lab = RawContextLab()
    lab.add_fixture(_event("alone", "lentil soup"))
    response = _explore(lab, person_id="p1", purpose="nav", anchor_id="alone")
    assert response.terminal_reason == "supported_leaf"
    assert response.exhaustion == "exact"
    assert "no relevant context" not in response.detail.lower()


def test_follows_an_advertised_route_and_can_stop_on_the_fallback() -> None:
    lab = generate_topology(count=10, kind="sparse", seed=8, page_size=3, hop_limit=20)
    first = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n0")
    fallback = next((route for route in first.next_routes if route.kind == "fallback"), None)
    assert fallback is not None
    stopped = _explore(
        lab,
        person_id="synthetic-1",
        purpose="nav",
        route_handle=first.route_handle or "",
        route_id=fallback.route_id,
    )
    assert stopped.terminal_reason == "supported_leaf"


def test_replays_a_request_id_without_advancing_the_frontier() -> None:
    lab = generate_topology(count=12, kind="sparse", seed=4, page_size=3, hop_limit=12)
    first = _explore(
        lab,
        person_id="synthetic-1",
        purpose="nav",
        anchor_id="n0",
        request_id="page-1",
    )
    replay = _explore(
        lab,
        person_id="synthetic-1",
        purpose="nav",
        route_handle=first.route_handle or "",
        request_id="page-1",
    )
    assert [item.excerpt for item in replay.items] == [item.excerpt for item in first.items]
    assert replay.hop_depth == first.hop_depth
    nxt = _explore(
        lab,
        person_id="synthetic-1",
        purpose="nav",
        route_handle=first.route_handle or "",
        request_id="page-2",
    )
    assert nxt.hop_depth > first.hop_depth


def test_stops_a_hub_expand_when_the_expansion_budget_is_spent() -> None:
    lab = generate_topology(
        count=40,
        kind="hub",
        seed=3,
        page_size=10,
        hop_limit=20,
        expansion_budget=5,
    )
    response = _explore(lab, person_id="synthetic-1", purpose="nav", anchor_id="n0")
    assert response.terminal_reason == "budget_exhausted"
    assert len(response.items) < 10


def test_unions_an_exact_token_and_a_graph_neighbor_with_the_index() -> None:
    lab = RawContextLab()
    lab.add_fixture(_event("a", "zephyrquartz alpha only"))
    lab.add_fixture(_event("b", "broom closet"))
    lab.add_fixture(_event("c", "unrelated shelf"))
    lab.link_structural("a", "b")
    split = lab.candidate_split("p1", "zephyrquartz alpha", "a")
    assert "b" in split.exact
    by_text = lab.candidate_split("p1", "zephyrquartz alpha only", "")
    assert "a" in by_text.exact


def test_describes_an_opened_trail_with_the_same_counts_as_an_exploration() -> None:
    lab = RawContextLab(LabOptions(seed=1, page_size=1))
    lab.add_fixture(_event("a", "alpha fever"))
    lab.add_fixture(_event("b", "beta crp"))
    lab.add_fixture(_event("c", "gamma esr"))
    lab.link_structural("a", "b", "recorded_association")
    lab.link_structural("b", "c", "temporal_neighbour")
    opened = lab.describe_trail("p1", ["a", "b", "c"])
    assert opened.page.hop_depth == 2
    assert opened.counts.explored_count == 3
    assert opened.counts.reachable_count == 3
    assert opened.page.direct_link_count == 1
    assert len(opened.page.breadcrumb) == 3
    assert "no relevant context" not in opened.page.detail.lower()
    stopped = lab.describe_trail("p1", ["a", "c"])
    assert stopped.page.hop_depth == 0
    assert stopped.counts.explored_count == 1


def test_steps_only_the_advertised_note_named_by_a_click() -> None:
    lab = RawContextLab(LabOptions(page_size=5, hop_limit=8))
    lab.add_fixture(_event("a", "alpha fever"))
    lab.add_fixture(_event("b", "beta crp"))
    lab.add_fixture(_event("c", "gamma esr"))
    lab.link_structural("a", "b")
    lab.link_structural("a", "c")
    opened = _explore(lab, person_id="p1", purpose="look", anchor_id="a", hold_at_anchor=True)
    handle = opened.route_handle or ""
    to_beta = next(
        (
            route
            for route in lab.local_routes(handle)
            if len(route.node_ids) == 1 and route.node_ids[0] == "b"
        ),
        None,
    )
    assert to_beta is not None
    assert to_beta.kind == "neighbour"
    searches = lab.hnsw_search_count
    stepped = _explore(
        lab,
        person_id="p1",
        purpose="look",
        route_handle=handle,
        route_id=to_beta.route_id,
        focus_id="b",
    )
    assert lab.hnsw_search_count == searches
    assert stepped.hop_depth == 1
    assert len(stepped.items) == 1
    assert "beta" in stepped.items[0].excerpt
    overlay = lab.local_overlay(stepped.route_handle or "")
    assert overlay is not None
    assert overlay.visited == ["a", "b"]
    assert "c" in overlay.frontier
    assert all(not hasattr(route, "node_ids") for route in stepped.next_routes)


def test_refuses_a_note_that_is_not_on_the_advertised_route() -> None:
    lab = RawContextLab(LabOptions(page_size=1, hop_limit=8))
    lab.add_fixture(_event("a", "alpha fever"))
    lab.add_fixture(_event("b", "beta crp"))
    lab.add_fixture(_event("c", "gamma esr"))
    lab.link_structural("a", "b")
    lab.link_structural("a", "c")
    opened = _explore(lab, person_id="p1", purpose="look", anchor_id="a", hold_at_anchor=True)
    handle = opened.route_handle or ""
    before = lab.local_overlay(handle)
    assert before is not None
    frontier = list(before.frontier)
    neighbour = next(
        (route for route in lab.local_routes(handle) if route.kind == "neighbour"),
        None,
    )
    assert neighbour is not None
    missing = _explore(
        lab,
        person_id="p1",
        purpose="look",
        route_handle=handle,
        route_id=neighbour.route_id,
        focus_id="not-on-the-route",
    )
    assert missing.terminal_reason == "policy_blocked"
    after_missing = lab.local_overlay(handle)
    assert after_missing is not None
    assert after_missing.frontier == frontier
    bare = _explore(lab, person_id="p1", purpose="look", route_handle=handle, focus_id="b")
    assert bare.terminal_reason == "policy_blocked"
    after_bare = lab.local_overlay(handle)
    assert after_bare is not None
    assert after_bare.frontier == frontier


def test_does_not_link_a_copied_note_until_an_advertisement_says_so() -> None:
    lab = RawContextLab()
    lab.add_fixture(replace(_event("orig", "original letter"), lineage_id="letter"))
    lab.add_fixture(
        replace(
            _event("copy", "copied letter"),
            lineage_id="letter-copy",
            copied_from_id="orig",
            source_arrival="copied",
        )
    )
    assert lab.projection.edge_between("copy", "orig") is None


def test_advertises_the_original_record_when_that_note_is_already_on_the_frontier() -> None:
    lab = RawContextLab(LabOptions(page_size=1, hop_limit=8))
    lab.add_fixture(replace(_event("orig", "original letter"), lineage_id="letter"))
    lab.add_fixture(
        replace(
            _event("copy", "copied letter"),
            lineage_id="letter-copy",
            copied_from_id="orig",
            source_arrival="copied",
        )
    )
    lab.link_structural("copy", "orig", "derived_or_copied")
    opened = _explore(lab, person_id="p1", purpose="look", anchor_id="copy", hold_at_anchor=True)
    source = next(
        (route for route in lab.local_routes(opened.route_handle or "") if route.kind == "source"),
        None,
    )
    assert source is not None
    assert source.label == "Original record"
    assert source.node_ids == ["orig"]
    assert any(route.kind == "source" for route in opened.next_routes)
    assert any(route.kind == "fallback" for route in opened.next_routes)


async def test_advertises_a_document_hub_as_the_original_record() -> None:
    lab = RawContextLab(LabOptions(page_size=1, hop_limit=8, judge=_EmptyJudge()))
    from wellbe_raw_context_brain.types import IngestInput

    saved = await lab.ingest(
        IngestInput(
            person_id="p1",
            text="page one of the letter",
            source_type="pdf_extract",
            captured_at="2024-03-01T00:00:00.000Z",
            lineage_id="letter",
            independence="source_family",
            source_arrival="imported",
            idempotency_key="letter-1",
            document_id="letter",
        )
    )
    opened = _explore(
        lab,
        person_id="p1",
        purpose="look",
        anchor_id=saved.event_id,
        hold_at_anchor=True,
    )
    source = next(
        (route for route in lab.local_routes(opened.route_handle or "") if route.kind == "source"),
        None,
    )
    assert source is not None
    assert re.fullmatch(r"hub_p1_letter", source.node_ids[0])


def test_stops_when_further_neighbors_would_only_repeat_the_same_lineage() -> None:
    lab = RawContextLab(LabOptions(page_size=5, hop_limit=10))
    for event_id in ("a", "b", "c", "d"):
        lab.add_fixture(replace(_event(event_id, f"{event_id} note"), lineage_id="same-family"))
    lab.link_structural("a", "b")
    lab.link_structural("a", "c")
    lab.link_structural("a", "d")
    response = _explore(lab, person_id="p1", purpose="nav", anchor_id="a")
    assert response.terminal_reason == "insufficient_independent_evidence"
    assert "no relevant context" not in response.detail.lower()
    assert response.route_handle is None


def test_keeps_a_record_kind_filter_on_the_current_note() -> None:
    lab = RawContextLab(LabOptions(page_size=5, hop_limit=8))
    lab.add_fixture(_event("a", "alpha"))
    lab.add_fixture(_event("b", "beta"))
    lab.add_fixture(_event("c", "gamma"))
    lab.add_fixture(_event("d", "delta"))
    lab.link_structural("a", "b")
    lab.link_structural("a", "c")
    lab.link_structural("a", "d")
    opened = _explore(lab, person_id="p1", purpose="look", anchor_id="a", hold_at_anchor=True)
    only_notes = next(
        (route for route in lab.local_routes(opened.route_handle or "") if route.kind == "facet"),
        None,
    )
    assert only_notes is not None
    assert only_notes.label == "Only notes"
    assert only_notes.node_ids == ["b", "c", "d"]
    filtered = _explore(
        lab,
        person_id="p1",
        purpose="look",
        route_handle=opened.route_handle or "",
        route_id=only_notes.route_id,
        operation="continue",
    )
    assert filtered.route_handle == opened.route_handle
    assert filtered.items == ()
    overlay = lab.local_overlay(filtered.route_handle or "")
    assert overlay is not None
    assert overlay.visited == ["a"]
    opens = [route.label for route in filtered.next_routes if route.kind == "neighbour"]
    assert opens == ["Open b", "Open c", "Open d"]
