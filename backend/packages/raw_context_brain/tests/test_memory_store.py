"""Memory graph snapshot and session store."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from wellbe_raw_context_brain.persist.graph_store import (
    DurableSnapshot,
    LinkAcknowledgement,
    empty_durable_snapshot,
    snapshot_from_json,
    snapshot_to_json,
)
from wellbe_raw_context_brain.persist.memory_store import MemoryGraphStore
from wellbe_raw_context_brain.persist.session_store import MemorySessionStore
from wellbe_raw_context_brain.types import LinkAdvertisement, PointerNode, VaultEvent


def _sample() -> DurableSnapshot:
    return DurableSnapshot(
        events=(
            VaultEvent(
                id="e1",
                person_id="p1",
                captured_at="2024-01-02T00:00:00.000Z",
                source_type="note",
                text="short sleep",
                content_hash="h1",
                lineage_id="sleep",
                document_id=None,
            ),
        ),
        advertisements=(
            LinkAdvertisement(
                id="ad-1",
                person_id="p1",
                sequence=1,
                origin="model",
                digest="d1",
                model_version=None,
                prompt_version=None,
                policy_version="lab-policy-1",
                evidence_ids=("e1",),
                from_id="b",
                to_id="a",
                judgment="link",
                reason_code="shared_terms",
                relation="possible_semantic_association",
                proposed_confidence=0.4,
                confidence=0.4,
                created_at="2024-01-02T00:00:00.000Z",
                supersedes_id=None,
                withdrawn=False,
            ),
        ),
        nodes=(
            PointerNode(
                id="e1",
                kind="event",
                vault_event_id="e1",
                member_event_ids=(),
                person_id="p1",
            ),
        ),
        acknowledgements=(
            LinkAcknowledgement(
                person_id="p1",
                endpoint_ids=("b", "a"),
                acknowledged=True,
                updated_at="2024-01-03T00:00:00.000Z",
            ),
        ),
    )


def _stored() -> DurableSnapshot:
    snapshot = _sample()
    acknowledgement = snapshot.acknowledgements[0]
    return replace(
        snapshot,
        acknowledgements=(replace(acknowledgement, endpoint_ids=("a", "b")),),
    )


def test_round_trips_events_advertisements_nodes_and_acknowledgements() -> None:
    expected = _stored()
    memory = MemoryGraphStore()
    memory.save(_sample())
    assert memory.load() == expected

    second = MemoryGraphStore()
    second.replace(memory.snapshot())
    memory.save(empty_durable_snapshot())
    assert second.load() == expected

    assert MemoryGraphStore().load() == empty_durable_snapshot()
    encoded = snapshot_to_json(_sample())
    encoded = snapshot_to_json(expected)
    assert snapshot_from_json(encoded) == expected
    assert encoded
    parsed = json.loads(encoded)
    assert sorted(parsed) == ["acknowledgements", "advertisements", "events", "nodes"]
    assert "sessions" not in parsed


def test_stores_acknowledgement_endpoint_ids_in_canonical_order() -> None:
    raw = _sample()
    memory = MemoryGraphStore()
    memory.save(raw)
    assert raw.acknowledgements[0].endpoint_ids == ("b", "a")
    assert memory.snapshot().acknowledgements[0].endpoint_ids == ("a", "b")

    parsed = json.loads(snapshot_to_json(_sample()))
    assert parsed["acknowledgements"][0]["endpoint_ids"] == ["a", "b"]
    assert snapshot_from_json(snapshot_to_json(_sample())).acknowledgements[0].endpoint_ids == (
        "a",
        "b",
    )


def test_clears_sessions_without_changing_the_graph_snapshot() -> None:
    memory = MemoryGraphStore()
    memory.save(_sample())
    before = memory.snapshot()
    sessions = MemorySessionStore()
    sessions.put("rh_abc", {"person_id": "p1", "purpose": "look", "session": "exploration"})
    assert sessions.get("rh_abc") == {
        "person_id": "p1",
        "purpose": "look",
        "session": "exploration",
    }
    assert sessions.get("rh_missing") is None
    sessions.delete("rh_abc")
    assert sessions.get("rh_abc") is None
    sessions.put("rh_abc", {"person_id": "p1", "purpose": "look"})
    sessions.clear()
    assert sessions.get("rh_abc") is None
    assert memory.snapshot() == before
    assert memory.load() == _stored()


def test_raises_when_the_snapshot_json_is_corrupt_and_does_not_return_a_partial_graph() -> None:
    loaded: DurableSnapshot | None = None
    with pytest.raises(ValueError, match="graph store snapshot is unreadable"):
        loaded = snapshot_from_json("{")
    assert loaded is None

    encoded = json.loads(snapshot_to_json(_sample()))
    partial = {"events": encoded["events"], "advertisements": []}
    with pytest.raises(ValueError, match="graph store snapshot is unreadable"):
        snapshot_from_json(json.dumps(partial))


def test_round_trips_optional_projection_revision_and_digest() -> None:
    pinned = replace(_stored(), projection_revision=0, projection_digest="d0")
    memory = MemoryGraphStore()
    memory.save(pinned)
    assert memory.load() == pinned
    parsed = json.loads(snapshot_to_json(pinned))
    assert parsed["projection_revision"] == 0
    assert parsed["projection_digest"] == "d0"
