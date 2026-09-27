"""Live test: user-authored theory evaluation against a migrated Postgres (025+).

Skipped unless WELLBE_DATABASE_URL is set. Exercises the real SQL paths: evidence
lookup across C2/C4/C6, compare-and-set on theories.version, the user row CHECK,
evidence-edge sync on the Theory node, and the outbox event.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from wellbe_c15_theory.errors import (
    TheoryEvidenceNotFoundError,
    TheoryEvidenceUnrelatedError,
    TheoryVersionConflictError,
)
from wellbe_c15_theory.repository import TheoryRepository
from wellbe_c15_theory.service import TheoryService
from wellbe_contracts.c15_theory import (
    TheoryAssessment,
    TheoryEvidenceRef,
    TheoryEvidenceRefKind,
    TheoryType,
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


async def _seed_fact(s, patient_id: uuid.UUID, key: str, label: str) -> uuid.UUID:
    now = datetime.now(UTC)
    event_id, fact_id = uuid.uuid4(), uuid.uuid4()
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
              'text/plain', 'c15-test', '0.1.0', :consent, 'key-1', 'corr', 'trace', :now
            )
            """
        ),
        {
            "id": event_id, "p": patient_id, "idem": f"c15-{event_id}", "now": now,
            "hash": f"h-{event_id}", "consent": uuid.uuid4(),
        },
    )
    await s.execute(
        text(
            """
            INSERT INTO processing.extracted_facts (
              id, patient_id, raw_context_event_id, fact_type, entity_label, normalized_key,
              extraction_confidence, extraction_model, model_version, pipeline_version,
              quality_flag, captured_at, extracted_at, correlation_id, trace_id
            ) VALUES (
              :id, :p, :e, 'symptom', :label, :key, 0.9, 'test', '1', '1',
              'clean', :now, :now, 'corr', 'trace'
            )
            """
        ),
        {"id": fact_id, "p": patient_id, "e": event_id, "label": label, "key": key, "now": now},
    )
    return fact_id


async def _seed_node(s, patient_id: uuid.UUID, key: str, thread_id: uuid.UUID) -> uuid.UUID:
    node_id = uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)
    await s.execute(
        text(
            "INSERT INTO graph.kg_nodes (id, patient_id, node_type, normalized_key, "
            "display_label, status, thread_ids, first_seen_at, last_seen_at, created_at, "
            "updated_at) VALUES (:id, :p, 'Symptom', :k, :k, 'active', ARRAY[:t]::uuid[], "
            ":now, :now, :now, :now)"
        ),
        {"id": node_id, "p": patient_id, "k": key, "t": thread_id, "now": now},
    )
    return node_id


async def _edges(s, theory_node_id: uuid.UUID) -> list[tuple[uuid.UUID, str, list[uuid.UUID]]]:
    rows = await s.execute(
        text(
            "SELECT from_node_id, edge_type, thread_ids FROM graph.kg_edges "
            "WHERE to_node_id = :n ORDER BY edge_type"
        ),
        {"n": theory_node_id},
    )
    return [(r[0], r[1], list(r[2])) for r in rows]


@pytest.mark.asyncio
async def test_user_evaluation_end_to_end(session_factory) -> None:
    patient, thread = uuid.uuid4(), uuid.uuid4()
    other_patient = uuid.uuid4()

    async with session_factory() as s, s.begin():
        fact = await _seed_fact(s, patient, f"symptom:headache:{patient}", "Headache")
        node = await _seed_node(s, patient, f"symptom:headache:{patient}", thread)
        stray = await _seed_fact(s, patient, f"symptom:knee:{patient}", "Knee pain")
        foreign = await _seed_fact(s, other_patient, f"symptom:headache:{other_patient}", "x")
        theory_id = await TheoryService(s).create_theory(
            patient_id=patient,
            theory_text="Maybe screen time relates to my headaches",
            theory_type=TheoryType.TRIGGER,
            correlation_id="corr",
            trace_id="trace",
        )

    def _kwargs(**over):
        base = dict(
            theory_id=theory_id, patient_id=patient, actor_id=patient,
            assessment=TheoryAssessment.WEAKENED,
            rationale="Headaches continued on screen-free days.",
            evidence_refs=[TheoryEvidenceRef(kind=TheoryEvidenceRefKind.FACT, id=fact)],
            expected_version=1, investigation_thread_ids=[thread],
            idempotency_key="k1", correlation_id="corr", trace_id="trace",
        )
        base.update(over)
        return base

    # Foreign-patient and out-of-thread refs are rejected with no write.
    for bad, err in (
        (foreign, TheoryEvidenceNotFoundError),
        (stray, TheoryEvidenceUnrelatedError),
    ):
        async with session_factory() as s, s.begin():
            with pytest.raises(err):
                await TheoryService(s).evaluate_by_user(
                    **_kwargs(
                        evidence_refs=[TheoryEvidenceRef(kind=TheoryEvidenceRefKind.FACT, id=bad)]
                    )
                )

    async with session_factory() as s, s.begin():
        outcome = await TheoryService(s).evaluate_by_user(**_kwargs())
    assert outcome.theory_version == 2
    assert outcome.evaluation.evidence_node_ids == [node]

    async with session_factory() as s:
        row = (
            await s.execute(
                text("SELECT status, version, projection_node_id FROM c15.theories WHERE id = :t"),
                {"t": theory_id},
            )
        ).one()
        assert row.status == "not_supported_by_current_data"
        assert row.version == 2
        theory_node = row.projection_node_id
        assert await _edges(s, theory_node) == [(node, "evidence_against", [thread])]
        meta = (
            await s.execute(
                text("SELECT metadata FROM graph.kg_nodes WHERE id = :n"), {"n": theory_node}
            )
        ).scalar_one()
        assert meta["user_assessment"] == "weakened"
        events = (
            await s.execute(
                text(
                    "SELECT payload FROM events.outbox_events "
                    "WHERE event_type = 'c15.theory.evaluated.v1' AND payload->>'theory_id' = :t"
                ),
                {"t": str(theory_id)},
            )
        ).scalars().all()
        assert len(events) == 1 and events[0]["assessment"] == "weakened"

    # Idempotent replay: same key -> same evaluation, no new version.
    async with session_factory() as s, s.begin():
        replay = await TheoryService(s).evaluate_by_user(**_kwargs())
    assert replay.replayed and replay.evaluation.evaluation_id == outcome.evaluation.evaluation_id

    # Stale expected_version conflicts.
    async with session_factory() as s, s.begin():
        with pytest.raises(TheoryVersionConflictError):
            await TheoryService(s).evaluate_by_user(**_kwargs(idempotency_key="k2"))

    # Changing the mark flips the edge direction; the old user edge is retired.
    async with session_factory() as s, s.begin():
        second = await TheoryService(s).evaluate_by_user(
            **_kwargs(
                assessment=TheoryAssessment.SUPPORTED, expected_version=2, idempotency_key="k3"
            )
        )
    assert second.theory_version == 3
    async with session_factory() as s:
        assert await _edges(s, theory_node) == [(node, "evidence_for", [thread])]

    # Reopening clears the user's directional edges but keeps the history.
    async with session_factory() as s, s.begin():
        await TheoryService(s).evaluate_by_user(
            **_kwargs(assessment=TheoryAssessment.OPEN, expected_version=3, idempotency_key="k4")
        )
    async with session_factory() as s:
        assert await _edges(s, theory_node) == []
        count = (
            await s.execute(
                text(
                    "SELECT count(*) FROM c15.theory_evaluations "
                    "WHERE theory_id = :t AND evaluation_kind = 'user'"
                ),
                {"t": theory_id},
            )
        ).scalar_one()
        assert count == 3
        repo = TheoryRepository(s)
        history = await repo.list_user_evaluations(theory_id)
        assert [e.assessment for e in history] == ["open", "supported", "weakened"]
        latest = await repo.latest_user_evaluations([theory_id, uuid.uuid4()])
        assert list(latest) == [theory_id] and latest[theory_id].assessment == "open"

    # The DB back-stops the rule: a user evaluation without evidence is refused.
    async with session_factory() as s:
        with pytest.raises(IntegrityError):
            async with s.begin():
                await s.execute(
                    text(
                        "INSERT INTO c15.theory_evaluations (theory_id, patient_id, "
                        "evaluation_version, proposed_status, proposed_safety_level, "
                        "evaluation_kind, assessment, from_status, rationale, "
                        "evaluator_actor_id) VALUES (:t, :p, 99, 'unreviewed', 'low', "
                        "'user', 'open', 'unreviewed', 'why', :p)"
                    ),
                    {"t": theory_id, "p": patient},
                )

    async with session_factory() as s, s.begin():
        await s.execute(text("DELETE FROM graph.kg_edges WHERE patient_id = :p"), {"p": patient})
        await s.execute(text("DELETE FROM c15.theories WHERE patient_id = :p"), {"p": patient})
        await s.execute(text("DELETE FROM graph.kg_nodes WHERE patient_id = :p"), {"p": patient})
