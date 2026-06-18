"""Live C6 integration test for the signals coverage read (WEL-91).

Skipped unless WELLBE_DATABASE_URL is set, e.g.:

    kubectl port-forward -n wellbe svc/wellbe-postgres 5432:5432 &
    WELLBE_DATABASE_URL="postgresql+asyncpg://wellbe:wellbe_dev@localhost:5432/wellbe" \
        uv run pytest packages/c6_graph/tests/integration -v

Verifies the privacy-critical guarantee the signals summary relies on against the
live schema: ``nodes_for_patient`` returns ONLY the authenticated patient's nodes
(another patient's nodes are never visible) and honors the node-type filter.
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
                text("DELETE FROM graph.kg_nodes WHERE patient_id = :pid"),
                {"pid": pid},
            )


@pytest.mark.asyncio
async def test_signals_nodes_are_patient_scoped_and_filtered(session_factory):
    patient = uuid.uuid4()
    other = uuid.uuid4()
    try:
        async with session_factory() as session, session.begin():
            repo = GraphRepository(session)
            await repo.upsert_node(
                patient_id=patient, node_type="VitalSign",
                normalized_key=f"bp-{uuid.uuid4()}", display_label="Blood pressure 118/76",
            )
            await repo.upsert_node(
                patient_id=patient, node_type="LabResult",
                normalized_key=f"glucose-{uuid.uuid4()}", display_label="Glucose 92",
            )
            # Another patient's node must never appear.
            await repo.upsert_node(
                patient_id=other, node_type="VitalSign",
                normalized_key=f"intruder-{uuid.uuid4()}", display_label="Intruder BP",
            )

        async with session_factory() as session:
            repo = GraphRepository(session)
            mine = await repo.nodes_for_patient(patient_id=patient)
            labels = {n.display_label for n in mine}
            assert labels == {"Blood pressure 118/76", "Glucose 92"}
            assert all(n.patient_id == patient for n in mine)

            # Node-type filter is honored.
            vitals = await repo.nodes_for_patient(
                patient_id=patient, node_types=["VitalSign"]
            )
            assert {n.display_label for n in vitals} == {"Blood pressure 118/76"}

            # Isolation: the other patient never sees our nodes.
            theirs = await repo.nodes_for_patient(patient_id=other)
            assert {n.display_label for n in theirs} == {"Intruder BP"}
    finally:
        await _cleanup(session_factory, [patient, other])
