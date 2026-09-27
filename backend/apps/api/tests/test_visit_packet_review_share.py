"""Unit tests for visit-packet review edits and the owner share-link list.

The DB session and repository are replaced with in-memory fakes so the tests
exercise the route contracts: rewording is limited to the user's own prep
statements, and the share-link list never leaks tokens and derives ``expired``.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import visit_packets_v2
from wellbe_api.visit_packet.models import PacketRow, ShareLinkRow, StatementRow

_PATIENT = uuid.UUID("de7a0000-0000-4000-8000-000000000001")
_OTHER = uuid.UUID("de7a0000-0000-4000-8000-000000000002")
_AUTH = {
    "X-Wellbe-Actor-Id": str(_PATIENT),
    "X-Wellbe-Patient-Id": str(_PATIENT),
    "X-Wellbe-Actor-Type": "controller",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _Store:
    def __init__(self) -> None:
        self.packet = PacketRow(
            id=uuid.uuid4(),
            patient_id=_PATIENT,
            title="Knee visit",
            status="draft",
            thread_ids=[],
            created_at=_now(),
            updated_at=_now(),
        )
        self.prep = self._stmt("patient_prep", "question", "Is it a tear?", "patient_reported")
        self.summary = self._stmt("summary", "concern", "Knee pain since May", "direct_source_fact")
        self.links: list[ShareLinkRow] = []

    def _stmt(self, layer: str, section: str, text: str, cls: str) -> StatementRow:
        return StatementRow(
            id=uuid.uuid4(),
            packet_id=self.packet.id,
            patient_id=_PATIENT,
            layer=layer,
            section=section,
            ordinal=0 if layer == "patient_prep" else 1,
            text=text,
            classification=cls,
            source_refs=[{"ref_type": "fact", "source_id": "f-1", "label": "Your note"}],
            absent=False,
            absence_reason=None,
            included=True,
        )

    def link(self, *, status: str = "active", expires_in: timedelta, owner: uuid.UUID = _PATIENT,
             passcode: bool = False, created_offset: int = 0) -> ShareLinkRow:
        row = ShareLinkRow(
            id=uuid.uuid4(),
            packet_id=self.packet.id,
            patient_id=owner,
            grant_id=uuid.uuid4(),
            token_hash=f"hash-{len(self.links)}",
            passcode_hash="p" if passcode else None,
            recipient_name="Dr. Lee",
            purpose="clinician_visit",
            info_scope="selected_threads",
            status=status,
            expires_at=_now() + expires_in,
            created_at=_now() + timedelta(seconds=created_offset),
            revoked_at=_now() if status == "revoked" else None,
        )
        self.links.append(row)
        return row


class _FakeRepo:
    store: _Store

    def __init__(self, _session: Any) -> None: ...

    async def get_packet(self, packet_id: uuid.UUID) -> PacketRow | None:
        return self.store.packet if packet_id == self.store.packet.id else None

    async def get_statement(self, statement_id: uuid.UUID) -> StatementRow | None:
        for s in (self.store.prep, self.store.summary):
            if s.id == statement_id:
                return s
        return None

    async def statements_for_packet(self, _packet_id: uuid.UUID) -> list[StatementRow]:
        return [self.store.prep, self.store.summary]

    async def share_links_for_patient(
        self, patient_id: uuid.UUID, packet_id: uuid.UUID | None = None
    ) -> list[tuple[ShareLinkRow, str]]:
        rows = [
            link
            for link in self.store.links
            if link.patient_id == patient_id and (packet_id is None or link.packet_id == packet_id)
        ]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return [(r, self.store.packet.title) for r in rows]


class _FakeSession:
    async def flush(self) -> None: ...

    async def commit(self) -> None: ...


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Store]:
    s = _Store()
    _FakeRepo.store = s
    monkeypatch.setattr(visit_packets_v2, "VisitPacketRepository", _FakeRepo)

    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    app.dependency_overrides[get_session] = _fake_session
    yield s
    app.dependency_overrides.pop(get_session, None)


def _client() -> TestClient:
    return TestClient(app)


def _patch(store: _Store, body: dict[str, Any]) -> Any:
    return _client().patch(f"/v2/visit-packets/{store.packet.id}", headers=_AUTH, json=body)


def test_edit_rewords_patient_prep_statement(store: _Store) -> None:
    resp = _patch(
        store, {"edits": [{"statement_id": str(store.prep.id), "text": "  Could it be a tear?  "}]}
    )
    assert resp.status_code == 200, resp.text
    texts = {s["statement_id"]: s["text"] for s in resp.json()["statements"]}
    assert texts[str(store.prep.id)] == "Could it be a tear?"
    assert texts[str(store.summary.id)] == "Knee pain since May"


def test_edit_refuses_source_backed_summary_statement(store: _Store) -> None:
    resp = _patch(
        store, {"edits": [{"statement_id": str(store.summary.id), "text": "No knee pain"}]}
    )
    assert resp.status_code == 422
    assert store.summary.text == "Knee pain since May"


def test_edit_unknown_statement_is_404(store: _Store) -> None:
    resp = _patch(store, {"edits": [{"statement_id": str(uuid.uuid4()), "text": "x"}]})
    assert resp.status_code == 404


def test_edit_rejects_empty_text(store: _Store) -> None:
    resp = _patch(store, {"edits": [{"statement_id": str(store.prep.id), "text": ""}]})
    assert resp.status_code == 422


def test_inclusions_still_work_alongside_edits(store: _Store) -> None:
    resp = _patch(
        store,
        {
            "inclusions": [{"statement_id": str(store.summary.id), "included": False}],
            "edits": [{"statement_id": str(store.prep.id), "text": "New question"}],
        },
    )
    assert resp.status_code == 200
    assert store.summary.included is False
    assert store.prep.text == "New question"


def test_share_links_list_derives_status_and_hides_secrets(store: _Store) -> None:
    active = store.link(expires_in=timedelta(days=7), passcode=True, created_offset=3)
    expired = store.link(expires_in=timedelta(hours=-1), created_offset=2)
    revoked = store.link(status="revoked", expires_in=timedelta(days=1), created_offset=1)
    store.link(expires_in=timedelta(days=7), owner=_OTHER)

    resp = _client().get("/v2/share-links", headers=_AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [b["share_link_id"] for b in body] == [str(active.id), str(expired.id), str(revoked.id)]
    by_id = {b["share_link_id"]: b for b in body}
    assert by_id[str(active.id)]["status"] == "active"
    assert by_id[str(active.id)]["passcode_required"] is True
    assert by_id[str(expired.id)]["status"] == "expired"
    assert by_id[str(revoked.id)]["status"] == "revoked"
    assert by_id[str(revoked.id)]["revoked_at"] is not None
    assert by_id[str(active.id)]["packet_title"] == "Knee visit"
    for b in body:
        assert "share_token" not in b
        assert "token_hash" not in b
        assert "passcode_hash" not in b


def test_share_links_list_filters_by_packet(store: _Store) -> None:
    store.link(expires_in=timedelta(days=7))
    resp = _client().get(
        "/v2/share-links", headers=_AUTH, params={"packet_id": str(uuid.uuid4())}
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_share_links_requires_authentication() -> None:
    assert _client().get("/v2/share-links").status_code == 401
