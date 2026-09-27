"""GET /v2/threads/{id}/memories: read-time dedupe + created_at on each entry.

Thread linkage writes one pointer memory per extracted fact, so the same concept
captured twice reads as two identical rows. The API collapses same-type,
same-title entries (newest kept, source refs merged) and exposes created_at.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import phase5
from wellbe_api.routers.phase5 import dedupe_memories
from wellbe_contracts.c8_memory import (
    MemoryLifecycleState,
    MemorySourceRef,
    MemoryType,
    ResolvedMemoryEntry,
    SourceRefType,
)
from wellbe_contracts.c13_api import MemoryEntryV2

PATIENT = uuid.UUID("11111111-1111-1111-1111-111111111111")
AUTH = {"X-Wellbe-Actor-Id": str(PATIENT)}
THREAD = uuid.uuid4()
NODE = uuid.uuid4()


def _v2(
    title: str, day: int | None, *refs: dict[str, Any], mtype: str = "clinical"
) -> MemoryEntryV2:
    return MemoryEntryV2(
        memory_entry_id=str(uuid.uuid4()), memory_type=mtype, lifecycle_state="visible",
        title=title, thread_id=str(THREAD), source_refs=list(refs),
        created_at=datetime(2026, 9, day, tzinfo=UTC) if day else None,
    )


def _ref(kind: str, rid: uuid.UUID | str) -> dict[str, Any]:
    return {"source_ref_type": kind, "source_ref_id": str(rid), "field_path": None}


def test_duplicates_collapse_to_newest_with_merged_refs() -> None:
    fact_a, fact_b = uuid.uuid4(), uuid.uuid4()
    old = _v2("pain", 1, _ref("c4_extracted_fact", fact_a), _ref("c6_kg_node", NODE))
    new = _v2("Pain ", 5, _ref("c4_extracted_fact", fact_b), _ref("c6_kg_node", NODE))
    other = _v2("Headache", 3)

    out = dedupe_memories([old, other, new])

    assert [m.title for m in out] == ["Pain ", "Headache"]
    merged = out[0]
    assert merged.memory_entry_id == new.memory_entry_id
    ids = [r["source_ref_id"] for r in merged.source_refs]
    assert sorted(ids) == sorted([str(fact_a), str(fact_b), str(NODE)])
    # Inputs are not mutated.
    assert len(new.source_refs) == 2


def test_different_types_and_untitled_entries_are_not_merged() -> None:
    out = dedupe_memories([
        _v2("pain", 1), _v2("pain", 2, mtype="story"), _v2("", 3), _v2("  ", 4),
    ])
    assert len(out) == 4


def test_entries_without_timestamps_sort_last() -> None:
    out = dedupe_memories([_v2("pain", None), _v2("pain", 2)])
    assert len(out) == 1
    assert out[0].created_at == datetime(2026, 9, 2, tzinfo=UTC)


class _Session:
    async def commit(self) -> None: ...


@pytest.fixture
def memories(monkeypatch: pytest.MonkeyPatch) -> list[ResolvedMemoryEntry]:
    rows: list[ResolvedMemoryEntry] = []

    class FakeMemoryService:
        def __init__(self, _s: Any) -> None: ...

        async def read_thread_memory(self, *, patient_id, thread_id):
            return rows

    async def allow(*_a: Any, **_k: Any) -> None:
        return None

    async def fake_session() -> AsyncGenerator[_Session]:
        yield _Session()

    monkeypatch.setattr(phase5, "MemoryService", FakeMemoryService)
    monkeypatch.setattr(phase5, "require_access", allow)
    app.dependency_overrides[get_session] = fake_session
    yield rows
    app.dependency_overrides.pop(get_session, None)


def _resolved(title: str, created: datetime) -> ResolvedMemoryEntry:
    return ResolvedMemoryEntry(
        memory_entry_id=uuid.uuid4(), memory_type=MemoryType.CLINICAL,
        lifecycle_state=MemoryLifecycleState.VISIBLE, title=title,
        source_refs=[
            MemorySourceRef(
                source_ref_id=uuid.uuid4(), source_ref_type=SourceRefType.C4_EXTRACTED_FACT
            )
        ],
        created_at=created,
    )


def test_route_dedupes_and_exposes_created_at(memories) -> None:
    memories += [
        _resolved("pain", datetime(2026, 9, 1, 8, tzinfo=UTC)),
        _resolved("pain", datetime(2026, 9, 4, 8, tzinfo=UTC)),
    ]
    resp = TestClient(app).get(f"/v2/threads/{THREAD}/memories", headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["created_at"].startswith("2026-09-04")
    assert len(body[0]["source_refs"]) == 2
