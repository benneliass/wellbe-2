"""Category decides which earlier records placement may compare."""

from __future__ import annotations

import json
from dataclasses import asdict

from wellbe_raw_context_brain.persist.graph_store import (
    DurableSnapshot,
    snapshot_from_json,
    snapshot_to_json,
)
from wellbe_raw_context_brain.persist.memory_store import MemoryGraphStore
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.text import token_vector
from wellbe_raw_context_brain.types import IngestInput, JudgeDecision, JudgeRequest, VaultEvent


class _Linking:
    def __init__(self) -> None:
        self.requests: list[JudgeRequest] = []

    async def judge(self, request: JudgeRequest) -> list[JudgeDecision]:
        self.requests.append(request)
        return [
            JudgeDecision(
                handle=candidate.handle,
                judgment="link",
                reason_code="recorded_association",
                confidence=0.8,
            )
            for candidate in request.candidates
        ]


def _event(text: str, *, category: str | None, document_id: str | None = None) -> IngestInput:
    return IngestInput(
        person_id="p1",
        text=text,
        source_type="note",
        captured_at="2024-06-01T00:00:00.000Z",
        lineage_id="line",
        idempotency_key=text,
        document_id=document_id,
        category=category,
    )


def _by_text(lab: RawContextLab, text: str) -> VaultEvent:
    return next(event for event in lab.vault.list() if event.text == text)


async def test_only_the_same_category_is_eligible_and_a_hub_is_not() -> None:
    judge = _Linking()
    lab = RawContextLab(LabOptions(judge=judge))
    await lab.ingest(
        _event("zephyrquartz alpha marker", category="Lab", document_id="bundle")
    )
    await lab.ingest(_event("zephyrquartz alpha panel", category="lab result"))
    saved = await lab.ingest(_event("zephyrquartz alpha marker again", category="Lab"))

    earlier = _by_text(lab, "zephyrquartz alpha marker")
    other = _by_text(lab, "zephyrquartz alpha panel")
    new = _by_text(lab, "zephyrquartz alpha marker again")
    hub_id = "hub_p1_bundle"
    routes = lab.route_sets("p1")
    assert routes is not None
    assert earlier.id in routes.candidate_ids
    assert other.id not in routes.candidate_ids
    assert other.id not in routes.selected_ids
    assert hub_id not in routes.candidate_ids
    assert hub_id not in routes.selected_ids
    request = judge.requests[-1]
    assert [candidate.excerpt for candidate in request.candidates] == [earlier.text]
    payload = json.dumps(asdict(request))
    assert "Lab" not in payload
    assert "lab result" not in payload
    assert lab.projection.edge_between(new.id, earlier.id) is not None
    assert lab.projection.edge_between(new.id, other.id) is None
    assert lab.pointer(hub_id) is not None
    assert lab.pointer(hub_id).kind == "pseudonode"  # type: ignore[union-attr]
    assert saved.candidate_count == 1


async def test_a_record_with_no_category_is_placed_and_stays_unlinked() -> None:
    store = MemoryGraphStore()
    judge = _Linking()
    lab = RawContextLab(LabOptions(judge=judge, graph_store=store))
    await lab.ingest(_event("zephyrquartz alpha marker", category="Lab"))
    saved = await lab.ingest(_event("zephyrquartz alpha marker again", category=None))

    new = _by_text(lab, "zephyrquartz alpha marker again")
    earlier = _by_text(lab, "zephyrquartz alpha marker")
    pointer = lab.pointer(new.id)
    assert pointer is not None
    assert pointer.kind == "event"
    assert saved.event_id == new.id
    assert saved.candidate_count == 0
    assert saved.judgments == ()
    assert judge.requests[-1].candidates == ()
    assert lab.projection.edge_between(new.id, earlier.id) is None
    routes = lab.route_sets("p1")
    assert routes is not None
    assert routes.candidate_ids == []
    assert routes.selected_ids == []

    stored = store.load()
    stored_new = next(event for event in stored.events if event.id == new.id)
    stored_earlier = next(event for event in stored.events if event.id == earlier.id)
    assert stored_new.category is None
    assert stored_earlier.category == "Lab"

    encoded = json.loads(snapshot_to_json(stored))
    del encoded["events"][0]["category"]
    restored = snapshot_from_json(json.dumps(encoded))
    assert restored.events[0].category is None


async def test_the_approximate_index_cannot_offer_another_category() -> None:
    judge = _Linking()
    lab = RawContextLab(LabOptions(judge=judge))
    await lab.ingest(_event("hemoglobin panel", category="lab result"))
    saved = await lab.ingest(_event("zephyrquartz marker", category="Lab"))

    other = _by_text(lab, "hemoglobin panel")
    new = _by_text(lab, "zephyrquartz marker")
    hits = lab._indexes["p1"].search(token_vector(new.text), 16)  # noqa: SLF001
    assert other.id in {hit.id for hit in hits}
    routes = lab.route_sets("p1")
    assert routes is not None
    assert routes.candidate_ids == []
    assert routes.selected_ids == []
    assert saved.candidate_count == 0
    assert lab.projection.edge_between(new.id, other.id) is None


def test_a_snapshot_without_category_loads_as_missing() -> None:
    event = VaultEvent(
        id="e1",
        person_id="p1",
        captured_at="2024-01-01T00:00:00.000Z",
        source_type="note",
        text="zephyrquartz",
        content_hash="h",
        lineage_id="line",
        document_id=None,
        category="Lab",
    )
    snapshot = DurableSnapshot(events=(event,), advertisements=(), nodes=(), acknowledgements=())
    encoded = json.loads(snapshot_to_json(snapshot))
    assert encoded["events"][0]["category"] == "Lab"
    del encoded["events"][0]["category"]
    restored = snapshot_from_json(json.dumps(encoded))
    assert restored.events[0].category is None
    assert restored.events[0] == VaultEvent(
        id="e1",
        person_id="p1",
        captured_at="2024-01-01T00:00:00.000Z",
        source_type="note",
        text="zephyrquartz",
        content_hash="h",
        lineage_id="line",
        document_id=None,
    )
