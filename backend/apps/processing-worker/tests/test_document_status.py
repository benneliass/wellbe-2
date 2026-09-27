"""Stored document status transitions in the raw_context.received handler."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from wellbe_contracts.c4_processing import DocumentProcessingStatus as S
from wellbe_processing_worker import main, ocr, tasks
from wellbe_processing_worker.document_status import is_document

_EVENT = uuid.uuid4()
_PATIENT = uuid.uuid4()


class _Tracker:
    def __init__(self, facts: int = 0) -> None:
        self.calls: list[tuple[S, str | None, bool]] = []
        self.facts = facts

    async def mark(
        self,
        event_id: uuid.UUID,
        patient_id: uuid.UUID,
        status: S,
        *,
        detail: str | None = None,
        new_attempt: bool = False,
    ) -> None:
        assert (event_id, patient_id) == (_EVENT, _PATIENT)
        self.calls.append((status, detail, new_attempt))

    async def finish(
        self, event_id: uuid.UUID, patient_id: uuid.UUID, *, detail_if_empty: str
    ) -> S:
        status = S.PROCESSED if self.facts else S.NEEDS_OCR
        await self.mark(
            event_id, patient_id, status, detail=None if self.facts else detail_if_empty
        )
        return status


def _vault(event: dict[str, Any], content: bytes = b"%PDF-1.4") -> httpx.AsyncClient:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/content"):
            return httpx.Response(200, content=content)
        return httpx.Response(200, json=event)

    return httpx.AsyncClient(base_url="http://vault", transport=httpx.MockTransport(respond))


def _doc_event(**overrides: Any) -> dict[str, Any]:
    return {
        "id": str(_EVENT),
        "patient_id": str(_PATIENT),
        "source_type": "pdf",
        "mime_type": "application/pdf",
        "source_metadata": {"capture_type": "document"},
        **overrides,
    }


@pytest.fixture
def extracted(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    async def fake_extract(event_json: str) -> None:
        calls.append(event_json)

    monkeypatch.setattr(tasks, "_extract_facts", fake_extract)
    return calls


def _text(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    async def fake(content: bytes, event_id: object = None) -> ocr.DocumentText:
        return ocr.DocumentText(text)

    monkeypatch.setattr(ocr, "extract_document_text", fake)


async def _handle(tracker: _Tracker, event: dict[str, Any]) -> str | None:
    handler = main._make_raw_context_handler(_vault(event), tracker)
    return await handler(None, {"event_id": event["id"]}, uuid.uuid4())  # type: ignore[arg-type]


async def test_readable_document_moves_processing_then_processed(
    monkeypatch: pytest.MonkeyPatch, extracted: list[str]
) -> None:
    _text(monkeypatch, "LDL 120 mg/dL")
    tracker = _Tracker(facts=3)
    assert await _handle(tracker, _doc_event()) == "dispatched"
    assert tracker.calls == [(S.PROCESSING, None, True), (S.PROCESSED, None, False)]
    assert len(extracted) == 1


async def test_document_without_text_needs_ocr(
    monkeypatch: pytest.MonkeyPatch, extracted: list[str]
) -> None:
    _text(monkeypatch, "")
    monkeypatch.setattr(ocr, "tesseract_version", lambda: None)
    tracker = _Tracker()
    await _handle(tracker, _doc_event())
    assert tracker.calls[-1] == (S.NEEDS_OCR, "ocr_unavailable", False)

    monkeypatch.setattr(ocr, "tesseract_version", lambda: "5.3.0")
    tracker = _Tracker()
    await _handle(tracker, _doc_event())
    assert tracker.calls[-1] == (S.NEEDS_OCR, "no_readable_text", False)


async def test_text_but_no_facts_is_needs_ocr(
    monkeypatch: pytest.MonkeyPatch, extracted: list[str]
) -> None:
    _text(monkeypatch, "some text")
    tracker = _Tracker(facts=0)
    await _handle(tracker, _doc_event())
    assert tracker.calls[-1] == (S.NEEDS_OCR, "no_facts_found", False)


async def test_failure_marks_failed_and_reraises_for_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _text(monkeypatch, "text")

    async def boom(event_json: str) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(tasks, "_extract_facts", boom)
    tracker = _Tracker()
    with pytest.raises(RuntimeError):
        await _handle(tracker, _doc_event())
    assert tracker.calls == [(S.PROCESSING, None, True), (S.FAILED, "RuntimeError", False)]


async def test_non_documents_are_untracked(extracted: list[str]) -> None:
    tracker = _Tracker()
    event = _doc_event(source_type="manual_text", mime_type="text/plain", source_metadata={})
    event["source_metadata"] = {"text": "tired today"}
    await _handle(tracker, event)
    assert tracker.calls == []
    assert len(extracted) == 1


def test_is_document() -> None:
    assert is_document({"source_type": "pdf"})
    assert is_document({"source_type": "photo"})
    assert is_document(
        {"source_type": "manual_text", "source_metadata": {"capture_type": "document"}}
    )
    assert not is_document({"source_type": "manual_text", "source_metadata": {}})
