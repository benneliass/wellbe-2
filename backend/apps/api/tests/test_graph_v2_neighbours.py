"""Thread graph read: bounded 1-hop neighbourhood (GET /v2/graph/threads/{id}).

The controller reading their own thread also sees their own nodes one edge away
(marked ``in_thread = false``) plus the connecting edges, capped so the read
stays cheap. A grant-based principal keeps the approved structural omission of
out-of-thread adjacency. Graph + thread repositories are stubbed.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import graph_v2
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow

PATIENT = uuid.UUID("11111111-1111-1111-1111-111111111111")
AUTH = {"X-Wellbe-Actor-Id": str(PATIENT)}
GRANTEE = {
    "X-Wellbe-Actor-Id": "22222222-2222-2222-2222-222222222222",
    "X-Wellbe-Patient-Id": str(PATIENT),
    "X-Wellbe-Actor-Type": "user",
}
THREAD = uuid.uuid4()
NOW = datetime(2026, 9, 1, 12)


def _node(label: str, *, in_thread: bool, node_type: str = "Symptom") -> KgNodeRow:
    return KgNodeRow(
        id=uuid.uuid4(), patient_id=PATIENT, node_type=node_type,
        normalized_key=label.lower(), display_label=label, status="active",
        thread_ids=[THREAD] if in_thread else [], first_seen_at=NOW, last_seen_at=NOW,
        schema_version=1, created_at=NOW, updated_at=NOW,
    )


def _edge(a: KgNodeRow, b: KgNodeRow, score: float = 0.5) -> KgEdgeRow:
    return KgEdgeRow(
        id=uuid.uuid4(), from_node_id=a.id, to_node_id=b.id, edge_type="co_occurs_with",
        potential_score=score, score_version=1, score_inputs={}, needs_rescore=False,
        thread_ids=[], patient_id=PATIENT, schema_version=1, created_at=NOW, updated_at=NOW,
    )


class _Session:
    async def commit(self) -> None: ...


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    state = SimpleNamespace(nodes=[], edges=[], calls=[])

    class FakeThreadRepo:
        def __init__(self, _s: Any) -> None: ...

        async def get(self, tid: uuid.UUID) -> Any:
            return SimpleNamespace(patient_id=PATIENT) if tid == THREAD else None

    class FakeGraphRepo:
        def __init__(self, _s: Any) -> None: ...

        async def nodes_for_thread(self, *, patient_id, thread_id, node_types, limit):
            rows = [n for n in state.nodes if thread_id in n.thread_ids]
            return rows[:limit]

        async def edges_among_nodes(self, *, patient_id, thread_id, node_ids, edge_types, limit):
            ids = set(node_ids)
            return [e for e in state.edges if e.from_node_id in ids and e.to_node_id in ids]

        async def edges_touching_nodes(self, *, patient_id, node_ids, edge_types, limit):
            state.calls.append(("touching", limit))
            ids = set(node_ids)
            rows = [e for e in state.edges if e.from_node_id in ids or e.to_node_id in ids]
            return sorted(rows, key=lambda e: -e.potential_score)[:limit]

        async def nodes_by_ids(self, *, patient_id, node_ids):
            return {n.id: n for n in state.nodes if n.id in set(node_ids)}

    async def allow(*_a: Any, **_k: Any) -> None:
        return None

    async def fake_audit(*_a: Any, **_k: Any) -> None:
        return None

    async def fake_session() -> AsyncGenerator[_Session]:
        yield _Session()

    monkeypatch.setattr(graph_v2, "ThreadRepository", FakeThreadRepo)
    monkeypatch.setattr(graph_v2, "GraphRepository", FakeGraphRepo)
    monkeypatch.setattr(graph_v2, "require_access", allow)
    monkeypatch.setattr(graph_v2, "audit_ref", fake_audit)
    app.dependency_overrides[get_session] = fake_session
    yield state
    app.dependency_overrides.pop(get_session, None)


def _get(headers: dict[str, str] = AUTH, **params: Any) -> dict[str, Any]:
    resp = TestClient(app).get(f"/v2/graph/threads/{THREAD}", headers=headers, params=params)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_controller_sees_one_hop_neighbours_and_their_edges(graph) -> None:
    headache = _node("Headache", in_thread=True)
    screen = _node("Screen time", in_thread=False)
    sleep = _node("Poor sleep", in_thread=False)
    far = _node("Two hops away", in_thread=False)
    graph.nodes = [headache, screen, sleep, far]
    graph.edges = [_edge(headache, screen), _edge(sleep, headache), _edge(screen, far)]

    body = _get()
    by_label = {n["label"]: n for n in body["nodes"]}
    assert set(by_label) == {"Headache", "Screen time", "Poor sleep"}
    assert by_label["Headache"]["attributes"]["in_thread"] is True
    assert by_label["Screen time"]["attributes"]["in_thread"] is False
    # Only edges whose both endpoints are in the view travel; 2-hop is never reached.
    ids = {n["id"] for n in body["nodes"]}
    assert len(body["edges"]) == 2
    assert all(e["source"] in ids and e["target"] in ids for e in body["edges"])
    assert body["page_info"]["truncated"] is False


def test_neighbours_are_capped_by_the_node_budget(graph) -> None:
    hub = _node("Hub", in_thread=True)
    spokes = [_node(f"Spoke {i}", in_thread=False) for i in range(80)]
    graph.nodes = [hub, *spokes]
    graph.edges = [_edge(hub, s, score=1 - i / 100) for i, s in enumerate(spokes)]

    body = _get()
    assert len(body["nodes"]) == graph_v2._NEIGHBOUR_NODE_BUDGET
    # Strongest connections win the budget.
    assert "Spoke 0" in {n["label"] for n in body["nodes"]}
    assert "Spoke 79" not in {n["label"] for n in body["nodes"]}
    assert body["page_info"]["truncated"] is True
    assert graph.calls == [("touching", graph_v2._NEIGHBOUR_EDGE_SCAN)]


def test_neighbours_can_be_turned_off(graph) -> None:
    headache = _node("Headache", in_thread=True)
    screen = _node("Screen time", in_thread=False)
    graph.nodes = [headache, screen]
    graph.edges = [_edge(headache, screen)]

    body = _get(include_neighbors="false")
    assert [n["label"] for n in body["nodes"]] == ["Headache"]
    assert body["edges"] == []


def test_grantee_never_sees_out_of_thread_adjacency(graph) -> None:
    headache = _node("Headache", in_thread=True)
    screen = _node("Screen time", in_thread=False)
    graph.nodes = [headache, screen]
    graph.edges = [_edge(headache, screen)]

    body = _get(headers=GRANTEE)
    assert [n["label"] for n in body["nodes"]] == ["Headache"]
    assert body["edges"] == []
    assert graph.calls == []


def test_node_type_filter_applies_to_neighbours(graph) -> None:
    headache = _node("Headache", in_thread=True)
    med = _node("Ibuprofen", in_thread=False, node_type="Medication")
    graph.nodes = [headache, med]
    graph.edges = [_edge(headache, med)]

    body = _get(node_types="Symptom")
    assert [n["label"] for n in body["nodes"]] == ["Headache"]
