"""Records that arrived together share one hub. A lone record does not."""

from __future__ import annotations

from dataclasses import replace

from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import (
    IngestInput,
    JudgeDecision,
    JudgeRequest,
    VaultEvent,
    source_group_id,
)


class _Linking:
    async def judge(self, request: JudgeRequest) -> list[JudgeDecision]:
        return [
            JudgeDecision(
                handle=candidate.handle,
                judgment="link",
                reason_code="recorded_association",
                confidence=0.8,
            )
            for candidate in request.candidates
        ]


def _input(text: str, *, group: str | None, category: str | None = "Lab") -> IngestInput:
    return IngestInput(
        person_id="p1",
        text=text,
        source_type="pdf_extract",
        captured_at="2024-06-01T00:00:00.000Z",
        lineage_id=text,
        idempotency_key=text,
        document_id=group,
        category=category,
    )


def _bound(event_id: str, text: str, group: str | None) -> VaultEvent:
    return VaultEvent(
        id=event_id,
        person_id="p1",
        captured_at="2024-06-01T00:00:00.000Z",
        source_type="pdf_extract",
        text=text,
        content_hash=event_id,
        lineage_id=event_id,
        document_id=group,
    )


def test_a_blank_intake_group_is_unset() -> None:
    assert source_group_id(None) is None
    assert source_group_id({}) is None
    assert source_group_id({"source_group_id": "  "}) is None
    assert source_group_id({"source_group_id": 12}) is None
    assert source_group_id({"source_group_id": " visit-9 "}) == "visit-9"


async def test_two_grouped_records_share_one_hub_and_two_same_record_lines() -> None:
    lab = RawContextLab()
    await lab.ingest(_input("page one of the visit", group="visit-9", category=None))
    await lab.ingest(_input("page two of the visit", group="visit-9", category=None))

    hub_id = "hub_p1_visit-9"
    hub = lab.pointer(hub_id)
    assert hub is not None
    assert hub.kind == "pseudonode"
    assert hub.vault_event_id is None
    members = [event for event in lab.vault.list() if event.document_id == "visit-9"]
    assert [event.id for event in members] == list(hub.member_event_ids)
    same_record = [
        edge for edge in lab.projection.accepted() if edge.relation == "same_record_group"
    ]
    assert len(same_record) == 2
    assert {edge.reason_code for edge in same_record} == {"membership"}
    assert lab.view("p1").links
    assert {link.reason for link in lab.view("p1").links} == {"same_record_group"}


async def test_one_record_saved_alone_produces_no_hub() -> None:
    lab = RawContextLab()
    await lab.ingest(_input("the only page", group="visit-9"))
    await lab.ingest(_input("a note with no group", group=None, category="note"))

    assert lab.pointer("hub_p1_visit-9") is None
    assert all(node.kind == "event" for node in lab._nodes.values())  # noqa: SLF001
    assert lab.projection.edge_count == 0


async def test_placing_the_same_member_again_does_not_add_a_line() -> None:
    lab = RawContextLab()
    first = _bound("a", "page one", "visit-9")
    second = _bound("b", "page two", "visit-9")
    lab.bind_vault_events([first, second])
    await lab.place_bound_event(second)
    edges = lab.projection.edge_count
    ads = len(lab.log.ads)
    await lab.place_bound_event(second)
    assert lab.projection.edge_count == edges
    assert len(lab.log.ads) == ads
    assert edges == 2


async def test_a_hub_is_not_selected_as_the_comparison_anchor() -> None:
    judge = _Linking()
    lab = RawContextLab(LabOptions(judge=judge))
    await lab.ingest(_input("zephyrquartz alpha marker", group="visit-9"))
    await lab.ingest(_input("zephyrquartz alpha sibling", group="visit-9"))
    saved = await lab.ingest(_input("zephyrquartz alpha marker again", group=None))

    hub_id = "hub_p1_visit-9"
    routes = lab.route_sets("p1")
    assert routes is not None
    assert hub_id not in routes.candidate_ids
    assert hub_id not in routes.selected_ids
    assert saved.candidate_count == 2
    assert lab.projection.edge_between(saved.event_id, hub_id) is None


async def test_a_copy_reference_does_not_open_a_same_record_line() -> None:
    lab = RawContextLab()
    original = _bound("orig", "original letter", None)
    copied = replace(_bound("copy", "copied letter", None), copied_from_id="orig")
    lab.bind_vault_events([original, copied])
    await lab.place_bound_event(copied)

    assert all(node.kind == "event" for node in lab._nodes.values())  # noqa: SLF001
    assert all(edge.relation != "same_record_group" for edge in lab.projection.accepted())
