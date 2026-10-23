"""Opaque token to session JSON. clear() drops sessions and leaves the graph store alone."""

from __future__ import annotations

import json
from typing import Protocol, cast

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
SessionJson = dict[str, JsonValue]


class SessionStore(Protocol):
    def put(self, token: str, session: SessionJson) -> None: ...

    def get(self, token: str) -> SessionJson | None: ...

    def delete(self, token: str) -> None: ...

    def clear(self) -> None: ...


def _clone_session(session: SessionJson) -> SessionJson:
    cloned: object = json.loads(json.dumps(session))
    if not isinstance(cloned, dict):
        raise ValueError("session must be a JSON object")
    return cast(SessionJson, cloned)


class MemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionJson] = {}

    def put(self, token: str, session: SessionJson) -> None:
        self._sessions[token] = _clone_session(session)

    def get(self, token: str) -> SessionJson | None:
        session = self._sessions.get(token)
        if session is None:
            return None
        return _clone_session(session)

    def delete(self, token: str) -> None:
        self._sessions.pop(token, None)

    def clear(self) -> None:
        """Reload policy: exploration sessions expire. Durable graph state stays in GraphStore."""
        self._sessions.clear()
