"""Unit tests for the C13 /v1/capture write path (WEL-155).

Covers the no-DB guard paths (auth, idempotency-key, payload validation), the
type-specific envelope mapping, and a fully-stubbed happy path (DB session and
ingestion forward replaced) asserting the 201 contract.
"""

from __future__ import annotations

import base64
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import capture_v1

_ACTOR = "11111111-1111-1111-1111-111111111111"
_AUTH = {"X-Wellbe-Actor-Id": _ACTOR}
_IDEM = {"Idempotency-Key": "idem-abc-123"}


def _client() -> TestClient:
    return TestClient(app)


def test_capture_requires_authentication() -> None:
    resp = _client().post("/v1/capture", json={"capture_type": "note", "payload": {"text": "hi"}})
    assert resp.status_code == 401


def test_capture_requires_idempotency_key() -> None:
    resp = _client().post(
        "/v1/capture",
        headers=_AUTH,
        json={"capture_type": "note", "payload": {"text": "remember this"}},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "provenance_missing"


def test_capture_rejects_empty_symptom() -> None:
    resp = _client().post(
        "/v1/capture",
        headers={**_AUTH, **_IDEM},
        json={"capture_type": "symptom", "payload": {"description": "   "}},
    )
    assert resp.status_code == 422


def test_capture_rejects_bad_document_base64() -> None:
    resp = _client().post(
        "/v1/capture",
        headers={**_AUTH, **_IDEM},
        json={"capture_type": "document", "payload": {"content_base64": "not base64!!"}},
    )
    assert resp.status_code == 422


# --- envelope mapping (pure function) ---


def test_build_ingest_symptom() -> None:
    body = capture_v1.CaptureRequestV1(
        capture_type="symptom", payload={"description": "dull ache", "severity": "Moderate"}
    )
    source_type, raw, meta = capture_v1._build_ingest(body, "corr")
    assert source_type == "manual_text"
    assert raw == b"dull ache"
    assert meta["capture_type"] == "symptom"
    assert meta["severity"] == "Moderate"


def test_build_ingest_lab_summary() -> None:
    body = capture_v1.CaptureRequestV1(
        capture_type="lab",
        payload={
            "test_name": "Vitamin D",
            "value": "32",
            "unit": "ng/mL",
            "reference_range": "30-100",
        },
    )
    source_type, raw, meta = capture_v1._build_ingest(body, "corr")
    assert source_type == "manual_text"
    assert raw == b"Vitamin D: 32 ng/mL (ref 30-100)"
    assert meta["test_name"] == "Vitamin D"


def test_build_ingest_document() -> None:
    content = base64.b64encode(b"%PDF-1.4 fake").decode()
    body = capture_v1.CaptureRequestV1(
        capture_type="document",
        payload={"content_base64": content, "mime_type": "application/pdf", "filename": "labs.pdf"},
    )
    source_type, raw, meta = capture_v1._build_ingest(body, "corr")
    assert source_type == "pdf"
    assert raw == b"%PDF-1.4 fake"
    assert meta["mime_type"] == "application/pdf"
    assert "original_filename_hash" in meta


# --- stubbed happy path ---


class _FakeResponse:
    status_code = 200

    def json(self) -> dict[str, Any]:
        return {"event_id": "99999999-9999-9999-9999-999999999999"}

    @property
    def text(self) -> str:
        return ""


class _FakeAsyncClient:
    def __init__(self, *_: Any, **__: Any) -> None: ...

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_: Any) -> None: ...

    async def post(self, _path: str, json: dict[str, Any]) -> _FakeResponse:
        # The forwarded payload must carry the client idempotency key + capture_type.
        assert json["idempotency_key"] == "idem-abc-123"
        assert json["metadata"]["capture_type"] == "note"
        return _FakeResponse()


class _FakeSession:
    async def commit(self) -> None: ...


@pytest.fixture
def stub_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture_v1.httpx, "AsyncClient", _FakeAsyncClient)

    async def _fake_audit(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(capture_v1, "audit_ref", _fake_audit)

    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    app.dependency_overrides[get_session] = _fake_session
    yield
    app.dependency_overrides.pop(get_session, None)


def test_capture_happy_path_returns_201(stub_pipeline: None) -> None:
    resp = _client().post(
        "/v1/capture",
        headers={**_AUTH, **_IDEM},
        json={"capture_type": "note", "payload": {"text": "ask about my knee"}},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["capture_id"] == "99999999-9999-9999-9999-999999999999"
    assert body["status"] == "captured"
    assert body["processing"] == "pending"
