"""A restarted lab reads the vault again and keeps the walk. Note text is not stored."""

from __future__ import annotations

import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from wellbe_raw_context_brain.persist.sql_store import SqlGraphStore, SqlSessionStore, walk
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import ExploreInput, VaultEvent

_PERSON = "11111111-1111-1111-1111-111111111111"


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
        for event_id, note in (("a", "alpha fever"), ("b", "beta fever"), ("c", "gamma fever"))
    ]


def _engine() -> sessionmaker[Session]:
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


def _lab(session: Session) -> RawContextLab:
    return RawContextLab(
        LabOptions(
            graph_store=SqlGraphStore(session, _PERSON, table_prefix=""),
            session_store=SqlSessionStore(session, _PERSON, table_prefix=""),
            pointer_only=True,
        )
    )


def test_restart_keeps_the_walk_and_drops_the_note_text() -> None:
    factory = _engine()
    events = _events()
    with factory() as first:
        lab = _lab(first)
        lab.bind_vault_events(events)
        lab.link_structural("a", "b")
        lab.link_structural("a", "c")
        opened = lab.explore(
            ExploreInput(
                person_id=_PERSON,
                purpose="look",
                request_id="open-a",
                anchor_id="a",
                hold_at_anchor=True,
            )
        )
        only_notes = next(
            route for route in lab.local_routes(opened.route_handle or "") if route.kind == "facet"
        )
        first.commit()
    assert opened.route_handle is not None

    with factory() as second:
        stored = second.execute(
            text("SELECT snapshot FROM graph_snapshot WHERE person_id = :person_id"),
            {"person_id": _PERSON},
        ).scalar_one()
        assert "alpha fever" not in stored
        assert "beta fever" not in stored
    with factory() as third:
        filtered = walk(
            third,
            _PERSON,
            events,
            ExploreInput(
                person_id=_PERSON,
                purpose="look",
                request_id="filter-notes",
                route_handle=opened.route_handle,
                route_id=only_notes.route_id,
                operation="continue",
            ),
            table_prefix="",
        )
        third.commit()
        assert filtered.route_handle == opened.route_handle
        assert filtered.items == ()
        with factory() as check:
            saved = check.execute(
                text("SELECT body FROM exploration_session WHERE token = :token"),
                {"token": filtered.route_handle},
            ).scalar_one()
        assert json.loads(saved)["visited_nodes"] == ["a"]
