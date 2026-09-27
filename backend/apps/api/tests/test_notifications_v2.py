"""Unit tests for the C13 /v2/notifications surface (C12 in-app notifications).

Covers the auth guard, list (unread first + unread count), mark-read (owned vs
not-visible 404), read-all, and that every route writes an audit event. The DB
session and the notification store are stubbed so these stay infra-free.
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
from wellbe_api.routers import notifications_v2

_ACTOR = "11111111-1111-1111-1111-111111111111"
_AUTH = {"X-Wellbe-Actor-Id": _ACTOR}
_NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def _row(*, read: bool = False, title: str = "A follow-up is due: Ferritin") -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        patient_id=uuid.UUID(_ACTOR),
        kind="pending_item_due",
        title=title,
        body="If the result has come in, you can add it to the thread.",
        pending_item_id=uuid.uuid4(),
        thread_id=uuid.uuid4(),
        created_at=_NOW,
        read_at=_NOW if read else None,
    )


class _FakeStore:
    rows: list[Any] = []
    calls: list[tuple[str, Any]] = []

    def __init__(self, _session: Any) -> None: ...

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, limit: int = 20, unread_only: bool = False
    ) -> list[Any]:
        self.calls.append(("list", (patient_id, limit, unread_only)))
        rows = [r for r in self.rows if r.patient_id == patient_id]
        if unread_only:
            rows = [r for r in rows if r.read_at is None]
        return sorted(rows, key=lambda r: r.read_at is not None)[:limit]

    async def unread_count(self, patient_id: uuid.UUID) -> int:
        return sum(1 for r in self.rows if r.patient_id == patient_id and r.read_at is None)

    async def mark_read(self, patient_id: uuid.UUID, notification_id: uuid.UUID) -> Any:
        for r in self.rows:
            if r.id == notification_id and r.patient_id == patient_id:
                r.read_at = r.read_at or _NOW
                return r
        return None

    async def mark_all_read(self, patient_id: uuid.UUID) -> int:
        n = 0
        for r in self.rows:
            if r.patient_id == patient_id and r.read_at is None:
                r.read_at = _NOW
                n += 1
        return n


class _FakeSession:
    async def commit(self) -> None: ...


@pytest.fixture(autouse=True)
def _stubs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    audits: list[str] = []

    async def _fake_audit(*_: Any, event_type: str, **__: Any) -> None:
        audits.append(event_type)

    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    _FakeStore.rows = []
    _FakeStore.calls = []
    monkeypatch.setattr(notifications_v2, "audit_ref", _fake_audit)
    monkeypatch.setattr(notifications_v2, "NotificationStore", _FakeStore)
    app.dependency_overrides[get_session] = _fake_session
    yield audits
    app.dependency_overrides.pop(get_session, None)


def test_notifications_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/v2/notifications").status_code == 401
    assert client.post("/v2/notifications/read-all").status_code == 401


def test_list_returns_unread_first_with_count(_stubs: list[str]) -> None:
    read, unread = _row(read=True, title="Old"), _row(title="New")
    other_patient = _row()
    other_patient.patient_id = uuid.uuid4()
    _FakeStore.rows = [read, unread, other_patient]

    resp = TestClient(app).get("/v2/notifications?limit=5", headers=_AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["unread_count"] == 1
    assert [n["title"] for n in body["notifications"]] == ["New", "Old"]
    first = body["notifications"][0]
    assert first["read_at"] is None
    assert first["thread_id"] == str(unread.thread_id)
    assert _FakeStore.calls[0] == ("list", (uuid.UUID(_ACTOR), 5, False))
    assert _stubs == ["c13.notifications.read"]


def test_list_rejects_out_of_range_limit() -> None:
    assert TestClient(app).get("/v2/notifications?limit=0", headers=_AUTH).status_code == 422


def test_mark_read_sets_read_at_and_is_audited(_stubs: list[str]) -> None:
    row = _row()
    _FakeStore.rows = [row]
    resp = TestClient(app).post(f"/v2/notifications/{row.id}/read", headers=_AUTH)
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None
    assert _stubs == ["c13.notification.marked_read"]


def test_mark_read_of_someone_elses_notification_is_404(_stubs: list[str]) -> None:
    row = _row()
    row.patient_id = uuid.uuid4()
    _FakeStore.rows = [row]
    resp = TestClient(app).post(f"/v2/notifications/{row.id}/read", headers=_AUTH)
    assert resp.status_code == 404
    assert _stubs == []


def test_read_all_marks_every_unread(_stubs: list[str]) -> None:
    _FakeStore.rows = [_row(), _row(), _row(read=True)]
    resp = TestClient(app).post("/v2/notifications/read-all", headers=_AUTH)
    assert resp.status_code == 200
    assert resp.json()["marked_read"] == 2
    assert resp.json()["unread_count"] == 0
    assert all(r.read_at is not None for r in _FakeStore.rows)
    assert _stubs == ["c13.notifications.marked_all_read"]
