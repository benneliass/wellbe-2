"""One vault event is read at a time. Placement does not fetch the others."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from wellbe_agent_caller import Binding
from wellbe_agent_caller.types import HttpResponse
from wellbe_processing_worker import main, ocr, vision_cache
from wellbe_processing_worker.vault_reader import ReadKind, VaultFetchError, VaultReader

_NEW = uuid.uuid4()
_OLDER = uuid.uuid4()
_PERSON = uuid.uuid4()


def _client(routes: dict[str, httpx.Response], seen: list[str]) -> httpx.AsyncClient:
    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return routes.get(request.url.path, httpx.Response(404))

    return httpx.AsyncClient(base_url="http://vault", transport=httpx.MockTransport(respond))


def _event(**overrides: Any) -> dict[str, Any]:
    return {
        "id": str(_NEW),
        "patient_id": str(_PERSON),
        "source_type": "manual_text",
        "mime_type": "text/plain",
        "source_metadata": {},
        **overrides,
    }


async def test_typed_note_uses_stored_text_and_does_not_fetch_bytes() -> None:
    seen: list[str] = []
    client = _client({}, seen)
    result = await VaultReader(client).read(_event(source_metadata={"text": "arm pain"}))
    assert result.text == "arm pain"
    assert seen == []


async def test_typed_note_without_stored_text_fetches_that_event_only() -> None:
    seen: list[str] = []
    client = _client(
        {f"/vault/events/{_NEW}/content": httpx.Response(200, content=b"arm pain")},
        seen,
    )
    result = await VaultReader(client).read(_event())
    assert result.text == "arm pain"
    assert seen == [f"/vault/events/{_NEW}/content"]


async def test_pdf_and_photo_use_the_document_reader_for_that_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bytes] = []

    async def fake(content: bytes, event_id: object = None) -> ocr.DocumentText:
        calls.append(content)
        assert event_id == str(_NEW)
        return ocr.DocumentText(text="LDL 120")

    monkeypatch.setattr(ocr, "extract_document_text", fake)
    seen: list[str] = []
    content = {f"/vault/events/{_NEW}/content": httpx.Response(200, content=b"%PDF-1.4")}
    pdf = await VaultReader(_client(content, seen)).read(
        _event(source_type="pdf", mime_type="application/pdf")
    )
    photo = await VaultReader(_client(content, seen)).read(
        _event(source_type="photo", mime_type="image/jpeg")
    )
    assert pdf.text == photo.text == "LDL 120"
    assert calls == [b"%PDF-1.4", b"%PDF-1.4"]
    assert seen == [f"/vault/events/{_NEW}/content", f"/vault/events/{_NEW}/content"]


async def test_unreadable_file_returns_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(content: bytes, event_id: object = None) -> ocr.DocumentText:
        return ocr.DocumentText(text="")

    monkeypatch.setattr(ocr, "extract_document_text", fake)
    client = _client(
        {f"/vault/events/{_NEW}/content": httpx.Response(200, content=b"\xff")},
        [],
    )
    result = await VaultReader(client).read(_event(source_type="pdf", mime_type="application/pdf"))
    assert result.text == ""


async def test_named_request_fetches_that_event_and_not_its_neighbor() -> None:
    seen: list[str] = []
    client = _client(
        {
            f"/vault/events/{_NEW}": httpx.Response(
                200,
                json=_event(source_metadata={"text": "the new note"}),
            ),
            f"/vault/events/{_OLDER}/content": httpx.Response(200, content=b"older note"),
        },
        seen,
    )
    result = await VaultReader(client).read(str(_NEW))
    assert result.text == "the new note"
    assert seen == [f"/vault/events/{_NEW}"]


async def test_text_is_the_default_kind() -> None:
    client = _client({}, [])
    event = _event(source_metadata={"text": "arm pain"})
    result = await VaultReader(client).read(event, kind=ReadKind.TEXT)
    assert result.text == "arm pain"
    with pytest.raises(ValueError):
        await VaultReader(client).read(event, kind="bytes")


async def test_vault_failure_is_retryable() -> None:
    client = _client({}, [])
    with pytest.raises(VaultFetchError):
        await VaultReader(client).read(str(_NEW))


class _Row:
    def __init__(
        self,
        event_id: uuid.UUID,
        source_type: str,
        source_metadata: dict[str, object] | None = None,
    ) -> None:
        self.id = event_id
        self.patient_id = _PERSON
        self.source_type = source_type
        self.captured_at = datetime(2024, 2, 1, tzinfo=UTC)
        self.content_hash = str(event_id)
        self.source_metadata = source_metadata


class _Session:
    async def run_sync(self, fn: Any) -> None:
        fn(object())


async def test_placement_does_not_fetch_neighbor_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    class _Repo:
        def __init__(self, _session: object) -> None:
            pass

        async def list_events(self, _person_id: uuid.UUID) -> list[_Row]:
            return [_Row(_OLDER, "pdf"), _Row(_NEW, "pdf")]

    def _place(_session: object, person_id: str, events: list[Any], event_id: str) -> None:
        seen.append((person_id, event_id, [(item.id, item.text) for item in events]))

    monkeypatch.setattr("wellbe_c2_vault.repository.VaultRepository", _Repo)
    monkeypatch.setattr("wellbe_raw_context_brain.persist.sql_store.place_captured", _place)
    fetched: list[str] = []
    client = _client(
        {f"/vault/events/{_OLDER}/content": httpx.Response(200, content=b"older pdf")},
        fetched,
    )
    await main._place_context(  # type: ignore[arg-type]
        _Session(),
        client,
        _event(source_type="pdf", mime_type="application/pdf"),
        "the new pdf",
    )
    assert fetched == []
    assert seen == [
        (
            str(_PERSON),
            str(_NEW),
            [(str(_OLDER), ""), (str(_NEW), "the new pdf")],
        )
    ]


async def test_shared_intake_passes_the_group_id(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Any] = []

    class _Repo:
        def __init__(self, _session: object) -> None:
            pass

        async def list_events(self, _person_id: uuid.UUID) -> list[_Row]:
            return [_Row(_OLDER, "pdf", {"source_group_id": " visit-9 "})]

    def _place(_session: object, person_id: str, events: list[Any], event_id: str) -> None:
        seen.append((person_id, event_id, [(item.id, item.document_id) for item in events]))

    monkeypatch.setattr("wellbe_c2_vault.repository.VaultRepository", _Repo)
    monkeypatch.setattr("wellbe_raw_context_brain.persist.sql_store.place_captured", _place)
    await main._place_context(  # type: ignore[arg-type]
        _Session(),
        _client({}, []),
        _event(source_metadata={"source_group_id": "visit-9"}),
        "the new pdf",
    )
    assert seen == [
        (
            str(_PERSON),
            str(_NEW),
            [(str(_OLDER), "visit-9"), (str(_NEW), "visit-9")],
        )
    ]


async def test_repeated_vault_read_uses_the_vision_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    vision_cache.clear()
    content = b"\x89PNG\r\n\x1a\nrepeated-page"
    reads = {"extract": 0}

    def local(_content: bytes, _event_id: object = None) -> ocr.DocumentText:
        return ocr.DocumentText("too short", ocr.OcrResult("too short", 1, 0.1, "test", 1))

    original = ocr.extract_document_text

    async def counted(raw: bytes, event_id: object = None) -> ocr.DocumentText:
        reads["extract"] += 1
        return await original(raw, event_id)

    class _Transport:
        def __init__(self) -> None:
            self.calls = 0

        async def post(
            self,
            url: str,
            payload: dict[str, object],
            headers: dict[str, str],
            timeout_s: float,
        ) -> HttpResponse:
            self.calls += 1
            return HttpResponse(
                status=200,
                body={
                    "model": "vision-test-model",
                    "choices": [
                        {
                            "message": {
                                "content": "cached vision transcription of the same page",
                            }
                        }
                    ],
                },
            )

    monkeypatch.setattr(ocr, "extract_document_text_sync", local)
    monkeypatch.setattr(ocr, "extract_document_text", counted)
    transport = _Transport()
    token = ocr.using_caller(
        ocr.CallerOverride(
            transport,
            Binding(
                name="vision-test",
                base_url="https://vision.example/v1",
                api_key="sk-vault-reader-test",
                model="vision-test-model",
            ),
        )
    )
    try:
        client = _client(
            {f"/vault/events/{_NEW}/content": httpx.Response(200, content=content)},
            [],
        )
        reader = VaultReader(client)
        event = _event(source_type="photo", mime_type="image/png")
        first = await reader.read(event)
        second = await reader.read(event)
    finally:
        ocr.reset_caller(token)
    assert first.text == second.text == "cached vision transcription of the same page"
    assert reads["extract"] == 1
    assert transport.calls == 1
