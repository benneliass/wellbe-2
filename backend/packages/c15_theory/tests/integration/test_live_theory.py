"""Live C15 Theory test against the kind cluster Postgres.

Skipped unless WELLBE_DATABASE_URL is set. See the C7 live test for setup.
Exercises the real TheoryService: diagnostic text is blocked (no projection
node), non-diagnostic text is reframed + projected, personal evidence drives
status, external sources never become graph evidence edges, and every output
passes the C10 gate.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c15_theory.errors import TheoryBlockedError
from wellbe_c15_theory.service import TheoryService
from wellbe_contracts.c15_theory import (
    EvidenceDirection,
    PersonalEvidenceRef,
    TheorySafetyLevel,
    TheoryStatus,
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


async def _make_symptom_node(s, patient_id: uuid.UUID, label: str) -> uuid.UUID:
    node_id = uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)
    await s.execute(
        text(
            "INSERT INTO graph.kg_nodes "
            "(id, patient_id, node_type, normalized_key, display_label, status, "
            " thread_ids, first_seen_at, last_seen_at, created_at, updated_at) "
            "VALUES (:id, :p, 'Symptom', :k, :l, 'active', '{}', "
            " :now, :now, :now, :now)"
        ),
        {"id": node_id, "p": patient_id, "k": f"symptom:{node_id}", "l": label, "now": now},
    )
    return node_id


async def _cleanup(session_factory, patient_id: uuid.UUID, corr: str) -> None:
    async with session_factory() as s, s.begin():
        await s.execute(
            text(
                "DELETE FROM graph.kg_edges WHERE patient_id = :p AND to_node_id IN "
                "(SELECT id FROM graph.kg_nodes WHERE patient_id = :p AND node_type = 'Theory')"
            ),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM c15.theory_evaluations WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM c15.theory_external_context WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(text("DELETE FROM c15.theories WHERE patient_id = :p"), {"p": patient_id})
        await s.execute(text("DELETE FROM graph.kg_nodes WHERE patient_id = :p"), {"p": patient_id})
        await s.execute(
            text("DELETE FROM events.outbox_events WHERE correlation_id = :c"),
            {"c": corr},
        )


@pytest.mark.asyncio
async def test_live_theory_lifecycle(session_factory):
    patient_id = uuid.uuid4()
    corr = f"c15-live-{patient_id}"
    try:
        # 1. Diagnostic assertion is blocked: no projection node, safety blocked.
        async with session_factory() as s, s.begin():
            svc = TheoryService(s)
            blocked_id = await svc.create_theory(
                patient_id=patient_id,
                theory_text="I have lupus",
                theory_type=TheoryType.SYMPTOM_CAUSE,
                correlation_id=corr,
                trace_id="x",
            )
        async with session_factory() as s:
            row = (
                await s.execute(
                    text("SELECT safety_level, projection_node_id FROM c15.theories WHERE id = :i"),
                    {"i": blocked_id},
                )
            ).one()
            assert row.safety_level == TheorySafetyLevel.BLOCKED_DUE_TO_DIAGNOSTIC_CLAIM.value
            assert row.projection_node_id is None

        # Evaluating a blocked theory is refused.
        async with session_factory() as s, s.begin():
            svc = TheoryService(s)
            with pytest.raises(TheoryBlockedError):
                await svc.evaluate_theory(theory_id=blocked_id, correlation_id=corr, trace_id="x")

        # 2. Non-diagnostic theory is reframed + projected as a Theory node.
        async with session_factory() as s, s.begin():
            n_for = await _make_symptom_node(s, patient_id, "fatigue")
            theory_id = await TheoryService(s).create_theory(
                patient_id=patient_id,
                theory_text="Could my fatigue be related to poor sleep?",
                theory_type=TheoryType.SYMPTOM_CAUSE,
                correlation_id=corr,
                trace_id="x",
            )
        async with session_factory() as s:
            node = (
                await s.execute(
                    text("SELECT node_type FROM graph.kg_nodes WHERE normalized_key = :k"),
                    {"k": f"theory:{theory_id}"},
                )
            ).one()
            assert node.node_type == "Theory"

        # 3. Evaluate with one supporting personal-evidence edge -> partially_supported.
        async with session_factory() as s, s.begin():
            result = await TheoryService(s).evaluate_theory(
                theory_id=theory_id,
                correlation_id=corr,
                trace_id="x",
                personal_evidence=[
                    PersonalEvidenceRef(
                        node_id=n_for,
                        direction=EvidenceDirection.FOR,
                        evidence_link_id=uuid.uuid4(),
                    )
                ],
            )
        assert result.status is TheoryStatus.PARTIALLY_SUPPORTED
        assert result.safety_level is TheorySafetyLevel.LOW
        assert result.evidence_for_count == 1
        assert result.c10_decision in {"allow", "allow_with_obligations"}

        # A personal evidence edge now points at the Theory node.
        async with session_factory() as s:
            edge_count = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM graph.kg_edges e "
                        "JOIN graph.kg_nodes n ON n.id = e.to_node_id "
                        "WHERE n.normalized_key = :k AND e.edge_type = 'evidence_for'"
                    ),
                    {"k": f"theory:{theory_id}"},
                )
            ).scalar_one()
            assert edge_count == 1

        # 4. Contradicting personal evidence routes to clinician discussion.
        async with session_factory() as s, s.begin():
            n_against = await _make_symptom_node(s, patient_id, "good sleep log")
            result2 = await TheoryService(s).evaluate_theory(
                theory_id=theory_id,
                correlation_id=corr,
                trace_id="x",
                personal_evidence=[
                    PersonalEvidenceRef(
                        node_id=n_against,
                        direction=EvidenceDirection.AGAINST,
                        evidence_link_id=uuid.uuid4(),
                    )
                ],
            )
        assert result2.evaluation_version == 2
        assert result2.status is TheoryStatus.DISCUSS_WITH_CLINICIAN
        assert result2.safety_level is TheorySafetyLevel.NEEDS_CLINICIAN_CONTEXT
    finally:
        await _cleanup(session_factory, patient_id, corr)
