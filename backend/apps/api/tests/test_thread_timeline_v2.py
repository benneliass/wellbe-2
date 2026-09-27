"""GET /v2/threads/{id}/timeline: status history, chronological events, source index.

The builder is pure over stored rows, so it is tested with plain stand-ins; the
route is tested with the loader and thread lookup swapped out.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import thread_timeline_v2 as tl
from wellbe_api.routers.thread_timeline_v2 import TimelineInputs, build_timeline, status_history

PATIENT = uuid.UUID("11111111-1111-1111-1111-111111111111")
AUTH = {"X-Wellbe-Actor-Id": str(PATIENT)}
THREAD = uuid.uuid4()


def _at(day: int, hour: int = 9) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=UTC)


def _thread(status: str = "waiting_for_result", created_by: str = "user") -> Any:
    return SimpleNamespace(
        id=THREAD, patient_id=PATIENT, status=status, created_at=_at(1), created_by=created_by
    )


def _transition(seq: int, frm: str, to: str, day: int, actor: str = "system") -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(), transition_seq=seq, from_status=frm, to_status=to,
        created_at=_at(day), actor_type=actor,
    )


def _capture(day: int, capture_type: str = "symptom", **extra: Any) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(), captured_at=_at(day), source_type="manual_text",
        source_metadata={"capture_type": capture_type, **extra}, mime_type="text/plain",
    )


def _fact(capture: Any, label: str, fact_type: str = "symptom", conf: float = 0.82) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(), raw_context_event_id=capture.id, entity_label=label,
        fact_type=fact_type, captured_at=capture.captured_at, extraction_confidence=conf,
    )


def _pending(day: int, due_day: int | None = None) -> Any:
    return SimpleNamespace(
        pending_item_id=uuid.uuid4(), created_at=_at(day), title="Waiting for a result: Cough",
        item_type="result_pending", status="scheduled",
        due_at=_at(due_day) if due_day else None,
    )


def test_status_history_follows_real_transitions_only() -> None:
    transitions = [
        _transition(2, "active_unresolved", "waiting_for_result", 3),
        _transition(1, "draft", "active_unresolved", 2),
    ]
    assert status_history(_thread(), transitions) == [
        "draft", "active_unresolved", "waiting_for_result",
    ]


def test_status_history_without_transitions_is_just_the_current_status() -> None:
    assert status_history(_thread("active_unresolved"), []) == ["active_unresolved"]


def test_events_are_chronological_and_cover_each_kind() -> None:
    cap = _capture(4)
    facts = [_fact(cap, "cough"), _fact(cap, "Cough"), _fact(cap, "fatigue")]
    out = build_timeline(
        TimelineInputs(
            thread=_thread(),
            transitions=[_transition(1, "draft", "active_unresolved", 2)],
            captures={cap.id: cap},
            facts={f.id: f for f in facts},
            pending=[_pending(5, due_day=12)],
            memory_refs=[("c4_extracted_fact", facts[0].id)],
        )
    )
    assert [e.kind for e in out.events] == [
        "thread_started", "status_changed", "capture", "open_loop",
    ]
    started, changed, captured, loop = out.events
    assert started.title == "You started this thread"
    assert (changed.from_status, changed.to_status, changed.actor) == (
        "draft", "active_unresolved", "wellbe",
    )
    assert captured.title == "You described how you feel"
    # Duplicate labels collapse case-insensitively; no values are copied.
    assert captured.detail == "Picked out: cough, fatigue"
    assert captured.source_ref_ids == [str(cap.id)]
    assert loop.due_at == _at(12)
    assert loop.item_status == "scheduled"


def test_sources_resolve_memory_refs_to_labels_with_confidence_and_review() -> None:
    cap = _capture(4, capture_type="lab")
    fact = _fact(cap, "Vitamin D (25-OH)", fact_type="lab_result", conf=0.9)
    node = SimpleNamespace(id=uuid.uuid4(), display_label="headache", first_seen_at=_at(3))
    missing = uuid.uuid4()
    out = build_timeline(
        TimelineInputs(
            thread=_thread(created_by="system"),
            captures={cap.id: cap},
            facts={fact.id: fact},
            nodes={node.id: node},
            memory_refs=[
                ("c4_extracted_fact", fact.id),
                ("c6_kg_node", node.id),
                ("c4_extracted_fact", missing),
            ],
        )
    )
    by_id = {s.source_ref_id: s for s in out.sources}
    assert str(missing) not in by_id
    f = by_id[str(fact.id)]
    assert (f.display_label, f.component, f.kind, f.confidence) == (
        "Vitamin D (25-OH)", "c5", "lab", 0.9,
    )
    assert f.review_marker == "patient-entered"
    assert f.capture_id == str(cap.id)
    n = by_id[str(node.id)]
    assert (n.display_label, n.review_marker) == ("headache", "AI-summarized")
    c = by_id[str(cap.id)]
    assert (c.component, c.display_label) == ("c2", "Entered by you")
    assert out.events[0].title == "WellBe started this thread from what you added"


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return self._rows


class _RecordingSession:
    """Answers each query from a queue and keeps the SQL compiled for Postgres."""

    def __init__(self, answers: list[list[Any]]) -> None:
        self.answers = answers
        self.sql: list[str] = []

    async def execute(self, stmt: Any) -> _Result:
        from sqlalchemy.dialects import postgresql

        self.sql.append(str(stmt.compile(dialect=postgresql.dialect())))
        return _Result(self.answers.pop(0) if self.answers else [])


async def test_loader_queries_compile_for_postgres_and_are_patient_scoped() -> None:
    fact_id, node_id = uuid.uuid4(), uuid.uuid4()
    cap = _capture(4)
    fact = SimpleNamespace(**{**vars(_fact(cap, "cough")), "id": fact_id})
    node = SimpleNamespace(id=node_id, display_label="cough", first_seen_at=_at(4))
    session = _RecordingSession([
        [_transition(1, "draft", "active_unresolved", 2)],
        [("c4_extracted_fact", fact_id), ("c6_kg_node", node_id)],
        [fact],
        [node],
        [cap],
        [_pending(5)],
    ])

    inputs = await tl.load_timeline_inputs(session, patient_id=PATIENT, thread=_thread())

    assert len(session.sql) == 6
    transitions_sql, *scoped = session.sql
    assert "thread_state_transitions.thread_id" in transitions_sql
    for sql in scoped:
        assert "patient_id" in sql, sql
    assert "source_metadata ->> " in session.sql[4]
    assert set(inputs.facts) == {fact_id}
    assert set(inputs.nodes) == {node_id}
    assert set(inputs.captures) == {cap.id}
    assert len(inputs.pending) == 1


class _Session:
    async def commit(self) -> None: ...


@pytest.fixture
def route(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"thread": _thread("active_unresolved")}

    async def allow(*_a: Any, **_k: Any) -> None:
        return None

    async def fake_thread(_s: Any, _tid: uuid.UUID) -> Any:
        return state["thread"]

    async def fake_inputs(_s: Any, *, patient_id: uuid.UUID, thread: Any) -> TimelineInputs:
        return TimelineInputs(thread=thread)

    async def fake_audit(*_a: Any, **_k: Any) -> None:
        return None

    async def fake_session() -> AsyncGenerator[_Session]:
        yield _Session()

    monkeypatch.setattr(tl, "require_access", allow)
    monkeypatch.setattr(tl, "_load_thread", fake_thread)
    monkeypatch.setattr(tl, "load_timeline_inputs", fake_inputs)
    monkeypatch.setattr(tl, "audit_ref", fake_audit)
    app.dependency_overrides[get_session] = fake_session
    yield state
    app.dependency_overrides.pop(get_session, None)


def test_route_returns_timeline(route: dict[str, Any]) -> None:
    resp = TestClient(app).get(f"/v2/threads/{THREAD}/timeline", headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "c13.thread_timeline.v2"
    assert body["status_history"] == ["active_unresolved"]
    assert [e["kind"] for e in body["events"]] == ["thread_started"]


def test_route_hides_other_patients_threads(route: dict[str, Any]) -> None:
    route["thread"] = SimpleNamespace(**{**vars(_thread()), "patient_id": uuid.uuid4()})
    resp = TestClient(app).get(f"/v2/threads/{THREAD}/timeline", headers=AUTH)
    assert resp.status_code == 404
