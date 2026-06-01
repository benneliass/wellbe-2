"""Live C8 Six Memories test against the kind cluster Postgres.

Skipped unless WELLBE_DATABASE_URL is set. Verifies the hybrid store invariants:
- a derived (clinical) entry cannot be visible without a C5 evidence link
  (app gate + deferred DB trigger);
- a Story (authored) entry is visible from the user's own words without a
  clinician-sourced record;
- a correction to a referenced C4 fact changes the C8 READ (via the shared C11
  resolver) WITHOUT mutating the C8 row.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c8_memories.errors import VisibleWithoutEvidenceError
from wellbe_c8_memories.service import MemoryService
from wellbe_c11_correction.service import CorrectionService
from wellbe_contracts.c8_memory import (
    LinkRole,
    MemorySourceRef,
    MemoryType,
    SourceRefType,
)
from wellbe_contracts.c11_correction import (
    ActorAuthority,
    CorrectionTargetKind,
    CorrectionTargetRef,
    CorrectionType,
)
from wellbe_db import create_engine, create_session_factory

DATABASE_URL = os.environ.get("WELLBE_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="WELLBE_DATABASE_URL not set; live test skipped"
)


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def _insert_raw_event(s, patient_id: uuid.UUID) -> uuid.UUID:
    event_id = uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)
    await s.execute(
        text(
            """
            INSERT INTO vault.raw_context_events (
              id, patient_id, actor_id, source_type, idempotency_key,
              captured_at, received_at, ingested_at, content_hash, byte_size,
              mime_type, adapter_name, adapter_version, consent_snapshot_id,
              encryption_key_id, correlation_id, trace_id, created_at
            ) VALUES (
              :id, :p, :p, 'manual_text', :idem, :now, :now, :now, :hash, 12,
              'text/plain', 'c8-test', '0.1.0', :consent, 'key-1', :corr, 'tr', :now
            )
            """
        ),
        {
            "id": event_id,
            "p": patient_id,
            "idem": f"c8-raw-{event_id}",
            "now": now,
            "hash": f"hash-{event_id}",
            "consent": uuid.uuid4(),
            "corr": f"c8-live-{patient_id}",
        },
    )
    return event_id


async def _cleanup(session_factory, patient_id, corr):
    async with session_factory() as s, s.begin():
        await s.execute(
            text("DELETE FROM evidence.evidence_links WHERE patient_id = :p"),
            {"p": patient_id},
        )
        for tbl in (
            "c8.memory_source_refs",
            "c8.pattern_memory_refs",
            "c8.responsibility_memory_refs",
            "c8.memory_entries",
        ):
            await s.execute(
                text(f"DELETE FROM {tbl} WHERE patient_id = :p"), {"p": patient_id}
            )
        c11_tables = (
            "c11.correction_resolution_events",
            "c11.correction_targets",
            "c11.corrections",
        )
        for tbl in c11_tables:
            await s.execute(
                text(f"DELETE FROM {tbl} WHERE patient_id = :p"), {"p": patient_id}
            )
        await s.execute(
            text("DELETE FROM events.outbox_events WHERE correlation_id = :c"),
            {"c": corr},
        )


@pytest.mark.asyncio
async def test_live_memory_hybrid_store_and_read_resolution(session_factory):
    patient_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    fact_id = uuid.uuid4()
    corr = f"c8-live-{patient_id}"
    try:
        # 1. Derived clinical entry cannot be visible without C5 evidence.
        #    Use a session without auto-commit and roll back so the rejected
        #    draft is not persisted.
        async with session_factory() as s:
            svc = MemoryService(s)
            with pytest.raises(VisibleWithoutEvidenceError):
                await svc.create_entry(
                    patient_id=patient_id,
                    thread_id=thread_id,
                    memory_type=MemoryType.CLINICAL,
                    source_refs=[
                        MemorySourceRef(
                            source_ref_id=fact_id,
                            source_ref_type=SourceRefType.C4_EXTRACTED_FACT,
                            link_role=LinkRole.PRIMARY,
                            field_path="value",
                        )
                    ],
                    created_by_actor={"role": "system"},
                    title="HbA1c 6.1%",
                    make_visible=True,
                    evidence_raw_event_ids=[],  # no provenance -> rejected
                    correlation_id=corr,
                )
            await s.rollback()

        # 2. With C5 evidence, the derived clinical entry becomes visible.
        async with session_factory() as s, s.begin():
            raw_event = await _insert_raw_event(s, patient_id)
            clinical = await MemoryService(s).create_entry(
                patient_id=patient_id,
                thread_id=thread_id,
                memory_type=MemoryType.CLINICAL,
                source_refs=[
                    MemorySourceRef(
                        source_ref_id=fact_id,
                        source_ref_type=SourceRefType.C4_EXTRACTED_FACT,
                        link_role=LinkRole.PRIMARY,
                        field_path="value",
                    )
                ],
                created_by_actor={"role": "system"},
                title="HbA1c 6.1%",
                make_visible=True,
                evidence_raw_event_ids=[raw_event],
                correlation_id=corr,
            )
        clinical_id = clinical.memory_entry_id

        async with session_factory() as s:
            state = (
                await s.execute(
                    text(
                        "SELECT lifecycle_state FROM c8.memory_entries "
                        "WHERE memory_entry_id = :m"
                    ),
                    {"m": clinical_id},
                )
            ).scalar_one()
            assert state == "visible"
            link_n = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM evidence.evidence_links "
                        "WHERE source_type = 'memory_entry' AND source_id = :m"
                    ),
                    {"m": clinical_id},
                )
            ).scalar_one()
            assert link_n == 1

        # 3. A Story entry is visible from the user's own words (no derived gate).
        async with session_factory() as s, s.begin():
            story_raw = await _insert_raw_event(s, patient_id)
            await MemoryService(s).create_entry(
                patient_id=patient_id,
                thread_id=thread_id,
                memory_type=MemoryType.STORY,
                source_refs=[
                    MemorySourceRef(
                        source_ref_id=story_raw,
                        source_ref_type=SourceRefType.C2_RAW_EVENT,
                        link_role=LinkRole.PRIMARY,
                    )
                ],
                created_by_actor={"role": "controller"},
                title="I've felt exhausted every afternoon for a month",
                make_visible=True,
                correlation_id=corr,
            )

        # 4. A controller correction to the referenced fact changes the C8 READ
        #    (via the shared C11 resolver) without mutating the C8 row.
        async with session_factory() as s, s.begin():
            corr_raw = await _insert_raw_event(s, patient_id)
            await CorrectionService(s).request_correction(
                patient_id=patient_id,
                correction_type=CorrectionType.REPLACE_VALUE,
                target=CorrectionTargetRef(
                    target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                    target_id=fact_id,
                    field_path="value",
                ),
                raw_correction_event_id=corr_raw,
                actor_ref={"role": "controller"},
                actor_authority=ActorAuthority.CONTROLLER,
                proposed_payload={"value": "5.9%"},
                correlation_id=corr,
            )

        async with session_factory() as s:
            resolved = await MemoryService(s).read_thread_memory(
                patient_id=patient_id,
                thread_id=thread_id,
                memory_type=MemoryType.CLINICAL,
            )
            assert len(resolved) == 1
            entry = resolved[0]
            assert entry.projection_stale is True
            assert len(entry.resolved_overlays) == 1
            assert entry.resolved_overlays[0]["resolved_value"] == {"value": "5.9%"}

            # The C8 row payload/title was NOT mutated by the correction.
            title = (
                await s.execute(
                    text("SELECT title FROM c8.memory_entries WHERE memory_entry_id = :m"),
                    {"m": clinical_id},
                )
            ).scalar_one()
            assert title == "HbA1c 6.1%"
    finally:
        await _cleanup(session_factory, patient_id, corr)
