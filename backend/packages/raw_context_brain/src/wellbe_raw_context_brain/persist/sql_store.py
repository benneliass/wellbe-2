"""Server stores for one person's pointers and exploration sessions.

Note text is never written. A new process loads the snapshot, then binds
excerpts read from the vault for that request.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

from sqlalchemy import text
from sqlalchemy.orm import Session

from wellbe_raw_context_brain.persist.graph_store import (
    DurableSnapshot,
    empty_durable_snapshot,
    snapshot_from_json,
    snapshot_to_json,
)
from wellbe_raw_context_brain.persist.session_store import SessionJson
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import ExploreInput, SemanticData, VaultEvent


def strip_event_text(snapshot: DurableSnapshot) -> DurableSnapshot:
    return replace(
        snapshot,
        events=tuple(replace(event, text="") for event in snapshot.events),
    )


class SqlGraphStore:
    def __init__(
        self, session: Session, person_id: str, *, table_prefix: str = "context_brain."
    ) -> None:
        self._session = session
        self._person_id = person_id
        self._table = f"{table_prefix}graph_snapshot"

    def load(self) -> DurableSnapshot:
        row = self._session.execute(
            text(f"SELECT snapshot FROM {self._table} WHERE person_id = :person_id"),
            {"person_id": self._person_id},
        ).scalar_one_or_none()
        if row is None:
            return empty_durable_snapshot()
        raw = row if isinstance(row, str) else str(row)
        snapshot = strip_event_text(snapshot_from_json(raw))
        if any(event.text for event in snapshot.events):
            raise ValueError("graph snapshot must not store note text")
        return snapshot

    def save(self, snapshot: DurableSnapshot) -> None:
        stored = strip_event_text(snapshot)
        if any(event.text for event in stored.events):
            raise ValueError("graph snapshot must not store note text")
        payload = snapshot_to_json(stored)
        self._session.execute(
            text(
                f"INSERT INTO {self._table} (person_id, snapshot, updated_at) "
                "VALUES (:person_id, :snapshot, CURRENT_TIMESTAMP) "
                "ON CONFLICT (person_id) DO UPDATE SET "
                "snapshot = excluded.snapshot, updated_at = CURRENT_TIMESTAMP"
            ),
            {"person_id": self._person_id, "snapshot": payload},
        )
        self._session.flush()


class SqlSessionStore:
    def __init__(
        self, session: Session, person_id: str, *, table_prefix: str = "context_brain."
    ) -> None:
        self._session = session
        self._person_id = person_id
        self._table = f"{table_prefix}exploration_session"

    def put(self, token: str, session: SessionJson) -> None:
        import json

        self._session.execute(
            text(
                f"INSERT INTO {self._table} (token, person_id, body, updated_at) "
                "VALUES (:token, :person_id, :body, CURRENT_TIMESTAMP) "
                "ON CONFLICT (token) DO UPDATE SET "
                "body = excluded.body, person_id = excluded.person_id, "
                "updated_at = CURRENT_TIMESTAMP"
            ),
            {"token": token, "person_id": self._person_id, "body": json.dumps(session)},
        )
        self._session.flush()

    def get(self, token: str) -> SessionJson | None:
        import json

        row = self._session.execute(
            text(
                f"SELECT person_id, body FROM {self._table} WHERE token = :token"
            ),
            {"token": token},
        ).one_or_none()
        if row is None or str(row.person_id) != self._person_id:
            return None
        parsed = json.loads(row.body)
        if not isinstance(parsed, dict):
            raise ValueError("session must be a JSON object")
        return parsed

    def delete(self, token: str) -> None:
        self._session.execute(
            text(f"DELETE FROM {self._table} WHERE token = :token AND person_id = :person_id"),
            {"token": token, "person_id": self._person_id},
        )
        self._session.flush()

    def clear(self) -> None:
        self._session.execute(
            text(f"DELETE FROM {self._table} WHERE person_id = :person_id"),
            {"person_id": self._person_id},
        )
        self._session.flush()


def walk(
    session: Session,
    person_id: str,
    events: list[VaultEvent],
    explore_input: ExploreInput,
    *,
    table_prefix: str = "context_brain.",
) -> SemanticData:
    """Open a lab on the server stores, bind vault excerpts, and take one step."""
    lab = RawContextLab(
        LabOptions(
            graph_store=SqlGraphStore(session, person_id, table_prefix=table_prefix),
            session_store=SqlSessionStore(session, person_id, table_prefix=table_prefix),
            pointer_only=True,
        )
    )
    lab.bind_vault_events(events)
    return lab.explore(explore_input)


def place_captured(
    session: Session,
    person_id: str,
    events: list[VaultEvent],
    event_id: str,
    *,
    table_prefix: str = "context_brain.",
) -> None:
    """Place one stored vault record and judge its links. A repeat does not add more."""
    lab = RawContextLab(
        LabOptions(
            graph_store=SqlGraphStore(session, person_id, table_prefix=table_prefix),
            session_store=SqlSessionStore(session, person_id, table_prefix=table_prefix),
            pointer_only=True,
        )
    )
    if lab.was_placed(event_id):
        return
    lab.bind_vault_events(events)
    target = lab.vault.get(event_id)
    if target is None:
        raise ValueError("unknown event")
    result = asyncio.run(lab.place_bound_event(target))
    if result.terminal_reason == "dependency_unavailable":
        raise RuntimeError(result.detail or "context brain judge unavailable")


def bounded_neighbours(
    session: Session,
    person_id: str,
    event_id: str,
    *,
    table_prefix: str = "context_brain.",
) -> list[str]:
    """Accepted neighbours of one stored record. Empty when nothing has been placed."""
    lab = RawContextLab(
        LabOptions(
            graph_store=SqlGraphStore(session, person_id, table_prefix=table_prefix),
            session_store=SqlSessionStore(session, person_id, table_prefix=table_prefix),
            pointer_only=True,
        )
    )
    return lab.accepted_neighbour_ids(event_id)
