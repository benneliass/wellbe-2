"""Unit tests for the C13 /v1/things-noticed surface (genesis candidates).

Covers the auth guard, the list/dismiss/confirm happy paths, ownership isolation
(another user's candidate is 404, never leaked), and the not-pending guard (a
second confirm cannot spawn a duplicate thread). The DB session and the genesis /
thread services are fully stubbed so these stay infra-free unit tests.
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
from wellbe_api.routers import things_noticed_v1
from wellbe_contracts.genesis import CandidateStatus, ConcernType, ThreadCandidate

_ACTOR = "11111111-1111-1111-1111-111111111111"
_AUTH = {"X-Wellbe-Actor-Id": _ACTOR}
_CANDIDATE_ID = "22222222-2222-2222-2222-222222222222"


def _client() -> TestClient:
    return TestClient(app)


def _candidate(
    *, candidate_id: str = _CANDIDATE_ID, status: CandidateStatus = CandidateStatus.PENDING
) -> ThreadCandidate:
    now = datetime.now(UTC)
    return ThreadCandidate(
        candidate_id=uuid.UUID(candidate_id),
        user_id=uuid.UUID(_ACTOR),
        concern_key={"concern_type": "symptom"},
        episode_bucket="2026-W25",
        display_title="Knee pain",
        candidate_type=ConcernType.SYMPTOM,
        status=status,
        confidence=0.6,
        reason_code="default_candidate_pending_classification",
        first_seen_at=now,
        last_seen_at=now,
        seen_count=2,
        created_at=now,
        updated_at=now,
    )


class _FakeSession:
    async def commit(self) -> None: ...


def _override_session() -> None:
    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    app.dependency_overrides[get_session] = _fake_session


@pytest.fixture(autouse=True)
def _no_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_audit(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(things_noticed_v1, "audit_ref", _fake_audit)
    yield
    app.dependency_overrides.pop(get_session, None)


def test_things_noticed_requires_authentication() -> None:
    resp = _client().get("/v1/things-noticed")
    assert resp.status_code == 401


def test_list_things_noticed_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeService:
        def __init__(self, _session: Any) -> None: ...

        async def list_things_noticed(self, _user_id: uuid.UUID) -> list[ThreadCandidate]:
            return [_candidate()]

    monkeypatch.setattr(things_noticed_v1, "GenesisCandidateService", _FakeService)
    _override_session()

    resp = _client().get("/v1/things-noticed", headers=_AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["candidate_id"] == _CANDIDATE_ID
    assert body[0]["title"] == "Knee pain"
    assert body[0]["status"] == "pending"
    assert body[0]["seen_count"] == 2


def test_dismiss_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeRepo:
        def __init__(self, _session: Any) -> None: ...

        async def get(self, _cid: uuid.UUID) -> Any:
            return SimpleNamespace(
                user_id=uuid.UUID(_ACTOR),
                status="pending",
                display_title="Knee pain",
                concern_key={"concern_type": "symptom"},
            )

    class _FakeService:
        def __init__(self, _session: Any) -> None: ...

        async def dismiss(self, _cid: uuid.UUID) -> ThreadCandidate:
            return _candidate(status=CandidateStatus.DISMISSED)

    monkeypatch.setattr(things_noticed_v1, "CandidateRepository", _FakeRepo)
    monkeypatch.setattr(things_noticed_v1, "GenesisCandidateService", _FakeService)
    _override_session()

    resp = _client().post(f"/v1/things-noticed/{_CANDIDATE_ID}/dismiss", headers=_AUTH)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "dismissed"


def test_dismiss_not_owned_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeRepo:
        def __init__(self, _session: Any) -> None: ...

        async def get(self, _cid: uuid.UUID) -> Any:
            return SimpleNamespace(
                user_id=uuid.uuid4(),  # someone else's candidate
                status="pending",
                display_title="x",
                concern_key={},
            )

    monkeypatch.setattr(things_noticed_v1, "CandidateRepository", _FakeRepo)
    _override_session()

    resp = _client().post(f"/v1/things-noticed/{_CANDIDATE_ID}/dismiss", headers=_AUTH)
    assert resp.status_code == 404
    assert resp.json()["code"] == "grant_required"


def test_dismiss_not_pending_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeRepo:
        def __init__(self, _session: Any) -> None: ...

        async def get(self, _cid: uuid.UUID) -> Any:
            return SimpleNamespace(
                user_id=uuid.UUID(_ACTOR),
                status="promoted",
                display_title="x",
                concern_key={},
            )

    monkeypatch.setattr(things_noticed_v1, "CandidateRepository", _FakeRepo)
    _override_session()

    resp = _client().post(f"/v1/things-noticed/{_CANDIDATE_ID}/dismiss", headers=_AUTH)
    assert resp.status_code == 409


def test_confirm_happy_path_creates_thread_and_promotes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    thread_id = uuid.uuid4()
    captured: dict[str, Any] = {}

    class _FakeRepo:
        def __init__(self, _session: Any) -> None: ...

        async def get(self, _cid: uuid.UUID) -> Any:
            return SimpleNamespace(
                user_id=uuid.UUID(_ACTOR),
                status="pending",
                display_title="Knee pain",
                concern_key={"concern_type": "symptom"},
            )

    class _FakeThreadService:
        def __init__(self, _session: Any) -> None: ...

        async def create_thread(self, **kwargs: Any) -> uuid.UUID:
            captured.update(kwargs)
            return thread_id

    class _FakeCandidateService:
        def __init__(self, _session: Any) -> None: ...

        async def promote(self, _cid: uuid.UUID, *, thread_id: uuid.UUID) -> ThreadCandidate:
            captured["promoted_to"] = thread_id
            return _candidate(status=CandidateStatus.PROMOTED)

    monkeypatch.setattr(things_noticed_v1, "CandidateRepository", _FakeRepo)
    monkeypatch.setattr(things_noticed_v1, "ThreadService", _FakeThreadService)
    monkeypatch.setattr(things_noticed_v1, "GenesisCandidateService", _FakeCandidateService)
    _override_session()

    resp = _client().post(f"/v1/things-noticed/{_CANDIDATE_ID}/confirm", headers=_AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["thread_id"] == str(thread_id)
    assert body["status"] == "promoted"
    # User-initiated thread carries the candidate's concern_key forward.
    assert captured["title"] == "Knee pain"
    assert captured["concern_key"] == {"concern_type": "symptom"}
    assert captured["promoted_to"] == thread_id
