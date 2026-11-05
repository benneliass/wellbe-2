"""Placement keeps the link the map caller accepted, and opens only that one record."""

from __future__ import annotations

import json

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from wellbe_agent_caller import Binding
from wellbe_agent_caller.types import HttpResponse
from wellbe_processing_worker.ocr import DocumentText
from wellbe_processing_worker.vault_reader import VaultReader
from wellbe_raw_context_brain.persist.sql_store import bounded_neighbours, place_captured
from wellbe_raw_context_brain.types import VaultEvent

_PERSON = "11111111-1111-1111-1111-111111111111"
_ANCHOR = "anchor"
_NEW = "new"
_WORDS = ("sleep", "morning", "rest", "quiet", "water")
_NEW_NOTE = "new-note-secret"
_ANCHOR_NOTE = "anchor-vault-secret"


class _Transport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> HttpResponse:
        self.calls.append({"payload": payload})
        return self.responses.pop(0)


class _VaultContent:
    """The worker's vault reader, limited to the one event the map asked to open."""

    def __init__(self, reader: VaultReader) -> None:
        self._reader = reader

    async def read(self, event_id: str) -> str:
        loaded: DocumentText = await self._reader.read(event_id)
        return loaded.text


def _response(content: str) -> HttpResponse:
    return HttpResponse(
        status=200,
        body={"model": "map-test-model", "choices": [{"message": {"content": content}}]},
    )


def _engine() -> sessionmaker:
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


def test_the_accepted_neighbor_is_the_anchor_from_the_mini_map() -> None:
    seen: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path != f"/vault/events/{_ANCHOR}":
            return httpx.Response(404)
        return httpx.Response(
            200,
            json={
                "id": _ANCHOR,
                "source_type": "manual_text",
                "source_metadata": {"text": _ANCHOR_NOTE},
            },
        )

    client = httpx.AsyncClient(base_url="http://vault", transport=httpx.MockTransport(respond))
    transport = _Transport(
        [
            _response(json.dumps({"keywords": list(_WORDS)})),
            _response(
                json.dumps(
                    {
                        "action": "open_content",
                        "handle": "ih_1",
                        "reasonCode": "shared_context",
                        "confidence": 0.4,
                    }
                )
            ),
            _response(
                json.dumps(
                    {
                        "action": "link",
                        "handle": "ih_1",
                        "reasonCode": "shared_context",
                        "confidence": 0.8,
                    }
                )
            ),
        ]
    )
    events = [
        VaultEvent(
            id=_ANCHOR,
            person_id=_PERSON,
            captured_at="2024-02-01T00:00:00.000Z",
            source_type="note",
            text=_ANCHOR_NOTE,
            content_hash=_ANCHOR,
            lineage_id=_ANCHOR,
            document_id=None,
            category="note",
            keywords=_WORDS,
        ),
        VaultEvent(
            id=_NEW,
            person_id=_PERSON,
            captured_at="2024-02-02T00:00:00.000Z",
            source_type="note",
            text=_NEW_NOTE,
            content_hash=_NEW,
            lineage_id=_NEW,
            document_id=None,
            category="note",
        ),
    ]
    factory = _engine()
    with factory() as session:
        place_captured(
            session,
            _PERSON,
            events,
            _NEW,
            table_prefix="",
            keyword_binding=Binding(
                name="map-test",
                base_url="https://map.example/v1",
                api_key="sk-worker-map-secret",
                model="map-test-model",
            ),
            keyword_transport=transport,
            content_reader=_VaultContent(VaultReader(client)),
        )
        session.commit()
        assert bounded_neighbours(session, _PERSON, _NEW, table_prefix="") == [_ANCHOR]
        stored = session.execute(
            text("SELECT snapshot FROM graph_snapshot WHERE person_id = :person_id"),
            {"person_id": _PERSON},
        ).scalar_one()
    assert seen == [f"/vault/events/{_ANCHOR}"]
    assert _NEW_NOTE not in stored
    assert _ANCHOR_NOTE not in stored
    assert '"judgment":"link"' in stored
    sent = [json.dumps(call["payload"]) for call in transport.calls]
    assert _ANCHOR_NOTE not in sent[0]
    assert _ANCHOR_NOTE not in sent[1]
    assert _ANCHOR_NOTE in sent[2]
