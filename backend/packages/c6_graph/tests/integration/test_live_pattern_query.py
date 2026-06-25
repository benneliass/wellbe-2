"""Live C6 integration test for the pattern read surface (WEL-79).

Skipped unless WELLBE_DATABASE_URL is set, e.g.:

    kubectl port-forward -n wellbe svc/wellbe-postgres 5432:5432 &
    WELLBE_DATABASE_URL="postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe" \
        uv run pytest packages/c6_graph/tests/integration -v

Verifies the privacy-critical guarantees the pattern engine relies on against the
live schema: ``edges_for_patient`` returns ONLY the authenticated patient's edges
(another patient's edges are never visible), the edge-type filter is honored, and
``nodes_by_ids`` is patient-scoped so endpoint labels can't leak across patients.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c6_graph.repository import GraphRepository
from wellbe_db import create_engine, create_session_factory

DATABASE_URL = os.environ.get("WELLBE_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="WELLBE_DATABASE_URL not set; live integration test skipped",
)


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine(DATABASE_URL)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def _cleanup(session_factory, patient_ids: list[uuid.UUID]) -> None:
    async with session_factory() as session, session.begin():
        for pid in patient_ids:
            await session.execute(
                text("DELETE FROM graph.kg_edges WHERE patient_id = :pid"),
                {"pid": pid},
            )
            await session.execute(
                text("DELETE FROM graph.kg_nodes WHERE patient_id = :pid"),
                {"pid": pid},
            )


@pytest.mark.asyncio
async def test_pattern_edges_are_patient_scoped_and_filtered(session_factory):
    patient = uuid.uuid4()
    other_patient = uuid.uuid4()
    thread = uuid.uuid4()
    try:
        async with session_factory() as session, session.begin():
            repo = GraphRepository(session)
            n1 = await repo.upsert_node(
                patient_id=patient, node_type="Symptom",
                normalized_key=f"headache-{uuid.uuid4()}", display_label="Headache",
                thread_ids=[thread],
            )
            n2 = await repo.upsert_node(
                patient_id=patient, node_type="SocialFactor",
                normalized_key=f"poor-sleep-{uuid.uuid4()}", display_label="Poor sleep",
                thread_ids=[thread],
            )
            # An associative edge (surfaced) and a refinement edge (not a pattern
            # edge type) — the type filter must exclude the latter.
            await repo.insert_edge(
                from_node_id=n1.id, to_node_id=n2.id, edge_type="co_occurs_with",
                potential_score=0.7, patient_id=patient, thread_ids=[thread],
            )
            await repo.insert_edge(
                from_node_id=n1.id, to_node_id=n2.id, edge_type="refines",
                potential_score=0.9, patient_id=patient, thread_ids=[thread],
            )
            # Another patient's associative edge (must never be visible).
            o1 = await repo.upsert_node(
                patient_id=other_patient, node_type="Symptom",
                normalized_key=f"intruder-a-{uuid.uuid4()}", display_label="Intruder A",
                thread_ids=[thread],
            )
            o2 = await repo.upsert_node(
                patient_id=other_patient, node_type="Symptom",
                normalized_key=f"intruder-b-{uuid.uuid4()}", display_label="Intruder B",
                thread_ids=[thread],
            )
            await repo.insert_edge(
                from_node_id=o1.id, to_node_id=o2.id, edge_type="co_occurs_with",
                potential_score=0.8, patient_id=other_patient, thread_ids=[thread],
            )

        async with session_factory() as session:
            repo = GraphRepository(session)
            edges = await repo.edges_for_patient(
                patient_id=patient, edge_types=["co_occurs_with", "temporal_sequence"]
            )
            # Only our patient's co_occurs_with edge — not refines, not the other
            # patient's edge.
            assert len(edges) == 1
            assert edges[0].edge_type == "co_occurs_with"
            assert edges[0].patient_id == patient

            node_ids = {edges[0].from_node_id, edges[0].to_node_id}
            nodes = await repo.nodes_by_ids(
                patient_id=patient, node_ids=list(node_ids)
            )
            assert {n.display_label for n in nodes.values()} == {
                "Headache", "Poor sleep",
            }

            # Isolation: another patient asking by OUR node ids gets nothing.
            leaked = await repo.nodes_by_ids(
                patient_id=other_patient, node_ids=list(node_ids)
            )
            assert leaked == {}
    finally:
        await _cleanup(session_factory, [patient, other_patient])
