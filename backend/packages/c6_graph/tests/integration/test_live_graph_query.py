"""Live C6 integration test for thread-scoped graph reads (WEL-156).

Skipped unless WELLBE_DATABASE_URL is set, e.g.:

    kubectl port-forward -n wellbe svc/postgres 5432:5432 &
    WELLBE_DATABASE_URL="postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe" \
        uv run pytest packages/c6_graph/tests/integration -v

Verifies the privacy-critical guarantees of the read contract against the live
schema: nodes/edges are scoped to BOTH the authenticated patient and the
requested thread; a node tagged to another thread or owned by another patient
is never returned; and an edge that would reach an out-of-thread node is
structurally omitted (no adjacency leakage).
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
async def test_thread_scoping_and_patient_isolation(session_factory):
    patient = uuid.uuid4()
    other_patient = uuid.uuid4()
    thread_a = uuid.uuid4()
    thread_b = uuid.uuid4()
    try:
        async with session_factory() as session, session.begin():
            repo = GraphRepository(session)
            # Two in-thread-A nodes for our patient + an edge between them.
            n1 = await repo.upsert_node(
                patient_id=patient, node_type="Symptom",
                normalized_key=f"headache-{uuid.uuid4()}", display_label="Headache",
                thread_ids=[thread_a],
            )
            n2 = await repo.upsert_node(
                patient_id=patient, node_type="Medication",
                normalized_key=f"ibuprofen-{uuid.uuid4()}", display_label="Ibuprofen",
                thread_ids=[thread_a],
            )
            await repo.insert_edge(
                from_node_id=n1.id, to_node_id=n2.id, edge_type="may_explain",
                potential_score=0.5, patient_id=patient, thread_ids=[thread_a],
            )
            # A node in thread B (must be omitted for a thread-A query).
            n_b = await repo.upsert_node(
                patient_id=patient, node_type="Symptom",
                normalized_key=f"nausea-{uuid.uuid4()}", display_label="Nausea",
                thread_ids=[thread_b],
            )
            # An edge from an in-thread-A node to the thread-B node, also tagged A:
            # it must be omitted because one endpoint is out of the in-thread set.
            await repo.insert_edge(
                from_node_id=n1.id, to_node_id=n_b.id, edge_type="associated_with",
                potential_score=0.4, patient_id=patient, thread_ids=[thread_a],
            )
            # Another patient's node tagged with the SAME thread id (isolation).
            await repo.upsert_node(
                patient_id=other_patient, node_type="Symptom",
                normalized_key=f"intruder-{uuid.uuid4()}", display_label="Intruder",
                thread_ids=[thread_a],
            )

        async with session_factory() as session:
            repo = GraphRepository(session)
            nodes = await repo.nodes_for_thread(
                patient_id=patient, thread_id=thread_a
            )
            labels = {n.display_label for n in nodes}
            assert labels == {"Headache", "Ibuprofen"}, labels  # not Nausea/Intruder

            node_ids = [n.id for n in nodes]
            edges = await repo.edges_among_nodes(
                patient_id=patient, thread_id=thread_a, node_ids=node_ids
            )
            # Only the in-thread edge survives; the edge reaching thread-B node is
            # structurally omitted (both endpoints must be in the node set).
            assert len(edges) == 1
            assert edges[0].edge_type == "may_explain"

            # Isolation: other patient cannot see our thread's nodes.
            other_nodes = await repo.nodes_for_thread(
                patient_id=other_patient, thread_id=thread_a
            )
            assert {n.display_label for n in other_nodes} == {"Intruder"}
    finally:
        await _cleanup(session_factory, [patient, other_patient])
