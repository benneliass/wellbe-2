"""Finished lab contracts."""

from __future__ import annotations

import pytest
from wellbe_raw_context_brain.persist.memory_store import MemoryGraphStore
from wellbe_raw_context_brain.persist.session_store import MemorySessionStore
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import (
    ExploreInput,
    IngestInput,
    JudgeDecision,
    JudgeRequest,
    SemanticData,
    VaultEvent,
)


def _fixture(event_id: str, text: str, **overrides: object) -> VaultEvent:
    captured_at = overrides.get("captured_at", "2024-01-01T00:00:00.000Z")
    lineage_id = overrides.get("lineage_id", event_id)
    return VaultEvent(
        id=event_id,
        person_id="p1",
        captured_at=str(captured_at),
        source_type="note",
        text=text,
        content_hash="hash",
        lineage_id=str(lineage_id),
        document_id=None,
    )


def _explore(lab: RawContextLab, **kwargs: object) -> SemanticData:
    operation = kwargs.get("operation", "open")
    if operation not in {"open", "continue", "rewind", "assess_link"}:
        operation = "open"
    request_id = kwargs.get("request_id", "")
    return lab.explore(
        ExploreInput(
            person_id=str(kwargs["person_id"]),
            purpose=str(kwargs["purpose"]),
            request_id=str(request_id),
            anchor_id=None if kwargs.get("anchor_id") is None else str(kwargs["anchor_id"]),
            route_handle=(
                None if kwargs.get("route_handle") is None else str(kwargs["route_handle"])
            ),
            operation=operation,  # type: ignore[arg-type]
            rewind_to_id=(
                None if kwargs.get("rewind_to_id") is None else str(kwargs["rewind_to_id"])
            ),
            hold_at_anchor=bool(kwargs.get("hold_at_anchor", False)),
        )
    )


def test_keeps_an_exact_leaf_rewindable_on_the_same_handle() -> None:
    lab = RawContextLab()
    lab.add_fixture(_fixture("a", "alpha fever"))
    lab.add_fixture(_fixture("b", "beta crp"))
    lab.link_structural("a", "b")
    opened = _explore(lab, person_id="p1", purpose="look", anchor_id="a", hold_at_anchor=True)
    rewound = _explore(
        lab,
        person_id="p1",
        purpose="look",
        route_handle=opened.route_handle or "",
        operation="rewind",
        rewind_to_id="a",
    )
    assert rewound.route_handle == opened.route_handle
    overlay = lab.local_overlay(rewound.route_handle or "")
    assert overlay is not None
    assert overlay.visited == ["a"]
    alone = RawContextLab()
    alone.add_fixture(_fixture("only", "lentil soup"))
    leaf = _explore(alone, person_id="p1", purpose="look", anchor_id="only")
    assert leaf.terminal_reason == "supported_leaf"
    assert leaf.route_handle
    back = _explore(
        alone,
        person_id="p1",
        purpose="look",
        route_handle=leaf.route_handle or "",
        operation="rewind",
        rewind_to_id="only",
    )
    assert back.route_handle == leaf.route_handle


async def test_records_route_set_history_and_prune_rows_on_the_save_result() -> None:
    lab = RawContextLab(LabOptions(max_candidates=1))
    lab.add_fixture(_fixture("early", "alpha fever", captured_at="2020-01-01T00:00:00.000Z"))
    lab.add_fixture(_fixture("late", "alpha fever later", captured_at="2025-01-01T00:00:00.000Z"))
    saved = await lab.ingest(
        IngestInput(
            person_id="p1",
            text="alpha fever today",
            source_type="note",
            captured_at="2024-01-01T00:00:00.000Z",
            lineage_id="fever",
            idempotency_key="save-1",
        )
    )
    assert saved.route_revision is not None
    assert saved.route_revision > 0
    assert len(saved.pruned) > 0
    again = await lab.ingest(
        IngestInput(
            person_id="p1",
            text="alpha fever tomorrow",
            source_type="note",
            captured_at="2024-02-01T00:00:00.000Z",
            lineage_id="fever-2",
            idempotency_key="save-2",
        )
    )
    assert lab.route_history("p1") == [saved.route_revision, again.route_revision]


async def test_judges_a_closer_neighbor_after_a_non_link() -> None:
    requests: list[JudgeRequest] = []

    class _Judge:
        async def judge(self, request: JudgeRequest) -> list[JudgeDecision]:
            requests.append(request)
            if len(requests) == 1:
                return [
                    JudgeDecision(
                        handle=candidate.handle,
                        judgment="no_link",
                        reason_code="recorded_association",
                        confidence=0.2,
                    )
                    for candidate in request.candidates
                ]
            return [
                JudgeDecision(
                    handle=candidate.handle,
                    judgment="link",
                    reason_code="recorded_association",
                    confidence=0.6,
                )
                for candidate in request.candidates
            ]

    lab = RawContextLab(LabOptions(judge=_Judge()))
    lab.add_fixture(_fixture("weak", "alpha", captured_at="2020-01-01T00:00:00.000Z"))
    lab.add_fixture(_fixture("filler", "marker", captured_at="2025-01-01T00:00:00.000Z"))
    lab.add_fixture(
        _fixture("closer", "alpha fever marker", captured_at="2024-06-01T00:00:00.000Z")
    )
    lab.link_structural("weak", "closer")
    saved = await lab.ingest(
        IngestInput(
            person_id="p1",
            text="alpha fever marker",
            source_type="note",
            captured_at="2024-06-01T00:00:00.000Z",
            lineage_id="new",
            idempotency_key="refer",
        )
    )
    assert len(requests) == 2
    assert any(row.judgment == "link" for row in saved.judgments)


async def test_stops_a_judge_that_is_past_its_deadline() -> None:
    clock = {"value": 0}

    class _Slow:
        async def judge(self, _request: JudgeRequest) -> list[JudgeDecision]:
            clock["value"] = 10
            raise RuntimeError("slow")

    lab = RawContextLab(LabOptions(now=lambda: clock["value"], judge_deadline_ms=5, judge=_Slow()))
    saved = await lab.ingest(
        IngestInput(
            person_id="p1",
            text="a lone note",
            source_type="note",
            captured_at="2024-01-01T00:00:00.000Z",
            lineage_id="lone",
            idempotency_key="deadline",
        )
    )
    assert saved.terminal_reason == "dependency_unavailable"


def test_restores_the_graph_in_a_second_lab_and_expires_the_walk() -> None:
    graph_store = MemoryGraphStore()
    session_store = MemorySessionStore()
    first = RawContextLab(LabOptions(graph_store=graph_store, session_store=session_store))
    first.add_fixture(_fixture("a", "alpha fever"))
    first.add_fixture(_fixture("b", "beta crp"))
    link = first.link_structural("a", "b")
    opened = _explore(first, person_id="p1", purpose="look", anchor_id="a")
    second = RawContextLab(LabOptions(graph_store=graph_store, session_store=session_store))
    restored = second.vault.get("a")
    assert restored is not None
    assert restored.text == "alpha fever"
    edge = second.projection.edge_between("a", "b")
    assert edge is not None
    assert edge.ad_id == link.id
    continued = _explore(
        second,
        person_id="p1",
        purpose="look",
        route_handle=opened.route_handle or "",
        operation="continue",
    )
    assert continued.terminal_reason != "policy_blocked"
    second.expire_exploration()
    expired = _explore(
        second,
        person_id="p1",
        purpose="look",
        route_handle=opened.route_handle or "",
    )
    assert expired.terminal_reason == "policy_blocked"
    still = second.vault.get("a")
    assert still is not None
    assert still.text == "alpha fever"


def test_rejects_a_same_record_link_that_is_not_hub_membership_on_rebuild() -> None:
    lab = RawContextLab()
    lab.add_fixture(_fixture("a", "alpha"))
    lab.add_fixture(_fixture("b", "beta"))
    ordinary = lab.link_structural("a", "b")
    assert ordinary.relation == "possible_semantic_association"
    lab.finish_rebuild()
    lab.link_structural("a", "b", "membership")
    with pytest.raises(ValueError, match="source-group membership"):
        lab.finish_rebuild()
