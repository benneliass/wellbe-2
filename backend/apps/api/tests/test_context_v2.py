"""The signed-in person explores their own raw context. A grant does not."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from wellbe_api.main import app
from wellbe_raw_context_brain.persist.sql_store import (
    SqlGraphStore,
    SqlSessionStore,
    person_map,
    walk,
)
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import ExploreInput, VaultEvent

_PERSON = "11111111-1111-1111-1111-111111111111"
_OTHER = "22222222-2222-2222-2222-222222222222"
_AUTH = {"X-Wellbe-Actor-Id": _PERSON}


def _client() -> TestClient:
    return TestClient(app)


def _events() -> list[VaultEvent]:
    return [
        VaultEvent(
            id=event_id,
            person_id=_PERSON,
            captured_at="2024-02-01T00:00:00.000Z",
            source_type="note",
            text=note,
            content_hash=event_id,
            lineage_id=event_id,
            document_id=None,
        )
        for event_id, note in (("a", "alpha"), ("b", "beta"), ("c", "gamma"))
    ]


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE graph_snapshot ("
                "person_id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, updated_at TEXT)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE exploration_session ("
                "token TEXT PRIMARY KEY, person_id TEXT NOT NULL, "
                "body TEXT NOT NULL, updated_at TEXT)"
            )
        )
    return sessionmaker(bind=engine)


def _install(monkeypatch: pytest.MonkeyPatch, factory: sessionmaker[Session]) -> None:
    async def _load(_session: object, person_id: str) -> list[VaultEvent]:
        return [event for event in _events() if event.person_id == person_id]

    async def _map(_session: object, person_id: str, bound: list[VaultEvent]) -> object:
        with factory() as session:
            return person_map(session, person_id, bound, table_prefix="")

    async def _walk(
        _session: object,
        person_id: str,
        bound: list[VaultEvent],
        explore_input: ExploreInput,
    ) -> object:
        with factory() as session:
            page = walk(session, person_id, bound, explore_input, table_prefix="")
            session.commit()
            return page

    monkeypatch.setattr("wellbe_api.routers.context_v2.load_person_events", _load)
    monkeypatch.setattr("wellbe_api.routers.context_v2.run_map", _map)
    monkeypatch.setattr("wellbe_api.routers.context_v2.run_walk", _walk)


def test_explore_requires_authentication() -> None:
    response = _client().post(
        "/v2/context/explore",
        json={"purpose": "look", "request_id": "r1", "anchor_id": "a"},
    )
    assert response.status_code == 401


def test_a_grant_cannot_start_the_walk() -> None:
    response = _client().post(
        "/v2/context/explore",
        headers={"X-Wellbe-Actor-Id": _OTHER, "X-Wellbe-Patient-Id": _PERSON},
        json={"purpose": "look", "request_id": "r1", "anchor_id": "a"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "grant_required"


def test_the_map_names_circles_without_returning_the_note(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _factory()
    events = _events()
    with factory() as session:
        lab = RawContextLab(
            LabOptions(
                graph_store=SqlGraphStore(session, _PERSON, table_prefix=""),
                session_store=SqlSessionStore(session, _PERSON, table_prefix=""),
                pointer_only=True,
            )
        )
        lab.bind_vault_events(events)
        lab.link_structural("a", "b")
        session.commit()
    _install(monkeypatch, factory)
    response = _client().get("/v2/context/map", headers=_AUTH)
    assert response.status_code == 200
    body = response.json()
    labels = {node["id"]: node["label"] for node in body["nodes"]}
    assert labels["a"] == "Alpha"
    assert "alpha" not in response.text
    assert body["links"] == [{"source": "a", "target": "b", "reason": "may relate"}]


def test_a_grant_cannot_open_the_map() -> None:
    response = _client().get(
        "/v2/context/map",
        headers={"X-Wellbe-Actor-Id": _OTHER, "X-Wellbe-Patient-Id": _PERSON},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "grant_required"


def test_filter_stays_on_the_current_note(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _factory()
    events = _events()
    with factory() as session:
        lab = RawContextLab(
            LabOptions(
                graph_store=SqlGraphStore(session, _PERSON, table_prefix=""),
                session_store=SqlSessionStore(session, _PERSON, table_prefix=""),
                pointer_only=True,
            )
        )
        lab.bind_vault_events(events)
        lab.link_structural("a", "b")
        lab.link_structural("a", "c")
        session.commit()
    _install(monkeypatch, factory)
    opened = _client().post(
        "/v2/context/explore",
        headers=_AUTH,
        json={
            "purpose": "look",
            "request_id": "open-a",
            "anchor_id": "a",
            "hold_at_anchor": True,
        },
    )
    assert opened.status_code == 200
    body = opened.json()
    only_notes = next(route for route in body["next_routes"] if route["kind"] == "facet")
    assert only_notes["label"] == "Only notes"
    filtered = _client().post(
        "/v2/context/explore",
        headers=_AUTH,
        json={
            "purpose": "look",
            "request_id": "filter-notes",
            "route_handle": body["route_handle"],
            "route_id": only_notes["route_id"],
            "operation": "continue",
        },
    )
    assert filtered.status_code == 200
    page = filtered.json()
    assert page["route_handle"] == body["route_handle"]
    assert page["opened"] == []
    with factory() as session:
        saved = session.execute(
            text("SELECT body FROM exploration_session WHERE token = :token"),
            {"token": page["route_handle"]},
        ).scalar_one()
    assert json.loads(saved)["visited_nodes"] == ["a"]
    opens = [route["label"] for route in page["next_routes"] if route["kind"] == "neighbour"]
    assert opens == ["Open b", "Open c"]


def test_another_person_cannot_continue_the_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _factory()
    _install(monkeypatch, factory)
    opened = _client().post(
        "/v2/context/explore",
        headers=_AUTH,
        json={"purpose": "look", "request_id": "open-a", "anchor_id": "a", "hold_at_anchor": True},
    )
    handle = opened.json()["route_handle"]
    stolen = _client().post(
        "/v2/context/explore",
        headers={"X-Wellbe-Actor-Id": _OTHER},
        json={
            "purpose": "look",
            "request_id": "steal",
            "route_handle": handle,
            "operation": "continue",
        },
    )
    assert stolen.status_code == 200
    assert stolen.json()["route_handle"] is None
    assert stolen.json()["terminal_reason"] == "policy_blocked"
