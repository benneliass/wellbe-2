"""Live C11 Correction Service test against the kind cluster Postgres.

Skipped unless WELLBE_DATABASE_URL is set. Verifies the append-only, source-linked
overlay model and the shared deterministic resolver:
- a controller correction creates a C2-provenance-linked overlay (C5 evidence link
  with correction_id) WITHOUT mutating the target;
- the resolver overlays the corrected value;
- an explicit supersession beats recency deterministically;
- a clinician proposal stays out of the resolved view until controller acceptance;
- applied corrections emit c11.correction.applied (+ compatibility alias).
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c11_correction.service import CorrectionService
from wellbe_contracts.c11_correction import (
    C11_CORRECTION_APPLIED,
    CORRECTION_APPLIED_COMPAT,
    ActorAuthority,
    CorrectionStatus,
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


async def _insert_raw_correction_event(s, patient_id: uuid.UUID) -> uuid.UUID:
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
              :id, :p, :p, 'manual_text', :idem,
              :now, :now, :now, :hash, 12,
              'text/plain', 'c11-test', '0.1.0', :consent,
              'key-1', :corr, 'trace-1', :now
            )
            """
        ),
        {
            "id": event_id,
            "p": patient_id,
            "idem": f"c11-raw-{event_id}",
            "now": now,
            "hash": f"hash-{event_id}",
            "consent": uuid.uuid4(),
            "corr": f"c11-live-{patient_id}",
        },
    )
    return event_id


async def _cleanup(session_factory, patient_id: uuid.UUID, fact_id: uuid.UUID, corr: str):
    async with session_factory() as s, s.begin():
        await s.execute(
            text("DELETE FROM evidence.evidence_links WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM c11.correction_resolution_events WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM c11.correction_targets WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM c11.corrections WHERE patient_id = :p"),
            {"p": patient_id},
        )
        # vault.raw_context_events is append-only (immutability enforced); test
        # raw events are isolated by a random patient_id and intentionally left.
        await s.execute(
            text("DELETE FROM events.outbox_events WHERE correlation_id = :c"),
            {"c": corr},
        )


@pytest.mark.asyncio
async def test_live_correction_overlay_and_resolution(session_factory):
    patient_id = uuid.uuid4()
    fact_id = uuid.uuid4()
    corr = f"c11-live-{patient_id}"
    try:
        # 1. Controller correction: replace a lab value on an extracted fact.
        async with session_factory() as s, s.begin():
            raw_event = await _insert_raw_correction_event(s, patient_id)
            svc = CorrectionService(s)
            result = await svc.request_correction(
                patient_id=patient_id,
                correction_type=CorrectionType.REPLACE_VALUE,
                target=CorrectionTargetRef(
                    target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                    target_id=fact_id,
                    field_path="value",
                    semantic_rank=50,
                ),
                raw_correction_event_id=raw_event,
                actor_ref={"actor_id": str(patient_id), "role": "controller"},
                proposed_payload={"value": "5.2 mmol/L"},
                rationale="Lab report transcription error",
                correlation_id=corr,
                trace_id="x",
            )
        first_correction = result.correction_id
        assert result.status == CorrectionStatus.APPLIED
        # A C5 evidence link was created with the correction hook (write through C5).
        assert len(result.evidence_link_ids) == 1

        async with session_factory() as s:
            link = (
                await s.execute(
                    text(
                        "SELECT linked_by, confidence_basis, correction_id, link_type "
                        "FROM evidence.evidence_links WHERE source_id = :f"
                    ),
                    {"f": fact_id},
                )
            ).mappings().one()
            assert link["linked_by"] == "correction_service"
            assert link["confidence_basis"] == "correction_service"
            assert link["correction_id"] == first_correction
            assert link["link_type"] == "contradicting"

            # applied + compatibility alias events emitted.
            applied_n = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM events.outbox_events "
                        "WHERE correlation_id = :c AND event_type = :et"
                    ),
                    {"c": corr, "et": C11_CORRECTION_APPLIED},
                )
            ).scalar_one()
            compat_n = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM events.outbox_events "
                        "WHERE correlation_id = :c AND event_type = :et"
                    ),
                    {"c": corr, "et": CORRECTION_APPLIED_COMPAT},
                )
            ).scalar_one()
            assert applied_n == 1
            assert compat_n == 1

        # 2. Resolver overlays the corrected value.
        async with session_factory() as s:
            overlay = await CorrectionService(s).resolve_target(
                patient_id=patient_id,
                target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                target_id=fact_id,
                field_path="value",
            )
            assert overlay.resolved_state == "overlaid"
            assert overlay.active_correction_id == first_correction
            assert overlay.resolved_value == {"value": "5.2 mmol/L"}

        # 3. A second controller correction that supersedes the first wins.
        async with session_factory() as s, s.begin():
            raw_event2 = await _insert_raw_correction_event(s, patient_id)
            result2 = await CorrectionService(s).request_correction(
                patient_id=patient_id,
                correction_type=CorrectionType.REPLACE_VALUE,
                target=CorrectionTargetRef(
                    target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                    target_id=fact_id,
                    field_path="value",
                    semantic_rank=50,
                ),
                raw_correction_event_id=raw_event2,
                actor_ref={"actor_id": str(patient_id), "role": "controller"},
                proposed_payload={"value": "5.5 mmol/L"},
                supersedes_correction_id=first_correction,
                correlation_id=corr,
                trace_id="x",
            )
        second_correction = result2.correction_id

        async with session_factory() as s:
            overlay = await CorrectionService(s).resolve_target(
                patient_id=patient_id,
                target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                target_id=fact_id,
                field_path="value",
            )
            assert overlay.active_correction_id == second_correction
            assert first_correction in overlay.inactive_correction_ids
            assert overlay.resolved_value == {"value": "5.5 mmol/L"}

        # 4. A clinician proposal stays out of the resolved view until acceptance.
        async with session_factory() as s, s.begin():
            raw_event3 = await _insert_raw_correction_event(s, patient_id)
            proposal = await CorrectionService(s).request_correction(
                patient_id=patient_id,
                correction_type=CorrectionType.ADD_MISSING_CONTEXT,
                target=CorrectionTargetRef(
                    target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                    target_id=fact_id,
                    field_path="note",
                    semantic_rank=50,
                ),
                raw_correction_event_id=raw_event3,
                actor_ref={"actor_id": str(uuid.uuid4()), "role": "clinician"},
                actor_authority=ActorAuthority.ROLE_PROPOSED,
                proposed_payload={"note": "Fasting unclear"},
                correlation_id=corr,
                trace_id="x",
            )
        proposal_id = proposal.correction_id
        assert proposal.status == CorrectionStatus.PENDING_CONTROLLER_ACCEPTANCE

        async with session_factory() as s:
            overlay = await CorrectionService(s).resolve_target(
                patient_id=patient_id,
                target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                target_id=fact_id,
                field_path="note",
            )
            assert overlay.resolved_state == "base"  # proposal excluded

        # 5. Controller accepts -> proposal participates in the resolved view.
        async with session_factory() as s, s.begin():
            await CorrectionService(s).accept_proposal(
                correction_id=proposal_id,
                controller_actor={"actor_id": str(patient_id), "role": "controller"},
                correlation_id=corr,
                trace_id="x",
            )
        async with session_factory() as s:
            overlay = await CorrectionService(s).resolve_target(
                patient_id=patient_id,
                target_kind=CorrectionTargetKind.C4_EXTRACTED_FACT,
                target_id=fact_id,
                field_path="note",
            )
            assert overlay.active_correction_id == proposal_id
            assert overlay.resolved_state == "augmented"
    finally:
        await _cleanup(session_factory, patient_id, fact_id, corr)
