"""Live C16 External Evidence + Relevance test against the kind cluster Postgres.

Skipped unless WELLBE_DATABASE_URL is set. See the C7 live test for setup.
Verifies the hard separation invariants: an external source/claim links to a
personal fact ONLY via the context-only relevance bridge, with a tier snapshot,
and NEVER as a graph.kg_edges row.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text
from wellbe_c16_external.service import ExternalEvidenceService
from wellbe_contracts.c16_external import (
    RELEVANCE_LINK_CREATED,
    ExternalClaimKind,
    ExternalSourceType,
    RelevanceScoreInputs,
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
            "VALUES (:id, :p, 'Symptom', :k, :l, 'active', '{}', :now, :now, :now, :now)"
        ),
        {"id": node_id, "p": patient_id, "k": f"symptom:{node_id}", "l": label, "now": now},
    )
    return node_id


async def _cleanup(session_factory, patient_id, node_id, source_id, corr) -> None:
    async with session_factory() as s, s.begin():
        await s.execute(
            text("DELETE FROM external_bridge.relevance_links WHERE patient_id = :p"),
            {"p": patient_id},
        )
        await s.execute(
            text("DELETE FROM external_kg.source_quality_reviews WHERE source_id = :s"),
            {"s": source_id},
        )
        await s.execute(
            text("DELETE FROM external_kg.external_claims WHERE source_id = :s"),
            {"s": source_id},
        )
        await s.execute(
            text("DELETE FROM external_kg.external_evidence_sources WHERE id = :s"),
            {"s": source_id},
        )
        await s.execute(text("DELETE FROM graph.kg_nodes WHERE patient_id = :p"), {"p": patient_id})
        await s.execute(
            text("DELETE FROM events.outbox_events WHERE correlation_id = :c"),
            {"c": corr},
        )


@pytest.mark.asyncio
async def test_live_relevance_link_is_context_only(session_factory):
    patient_id = uuid.uuid4()
    corr = f"c16-live-{patient_id}"
    node_id = None
    source_id = None
    try:
        # Register an external source + claim (external_kg, no patient_id).
        async with session_factory() as s, s.begin():
            svc = ExternalEvidenceService(s)
            source = await svc.register_source(
                source_type=ExternalSourceType.CLINICAL_GUIDELINE,
                source_quality_tier=2,
                tier_reason="National specialty society guideline",
                title="Fatigue evaluation guideline",
                assigned_by="curation-team",
                correlation_id=corr,
                trace_id="x",
            )
            source_id = source.id
            claim = await svc.register_claim(
                source_id=source_id,
                claim_text="Poor sleep is associated with daytime fatigue.",
                claim_kind=ExternalClaimKind.ASSOCIATION,
                correlation_id=corr,
                trace_id="x",
            )

        # Personal fact nodes to attach context to.
        async with session_factory() as s, s.begin():
            node_id = await _make_symptom_node(s, patient_id, "fatigue")
            node_id2 = await _make_symptom_node(s, patient_id, "poor sleep")

        # Link relevance (the ONLY personal<->external connection).
        async with session_factory() as s, s.begin():
            result = await ExternalEvidenceService(s).link_relevance(
                patient_id=patient_id,
                personal_node_id=node_id,
                external_source_id=source_id,
                external_claim_id=claim.id,
                relevance_inputs=RelevanceScoreInputs(
                    entity_or_code_match=1.0,
                    semantic_similarity=0.8,
                    thread_context_match=0.5,
                ),
                correlation_id=corr,
                trace_id="x",
            )
        expected = 0.35 * 1.0 + 0.25 * 0.8 + 0.15 * 0.5
        assert abs(result.relevance_score - expected) < 1e-6
        assert result.source_quality_tier_snapshot == 2
        assert result.context_only is True

        # The bridge row exists; NO relevance_link ever appears in graph.kg_edges.
        async with session_factory() as s:
            bridge_count = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM external_bridge.relevance_links "
                        "WHERE patient_id = :p AND personal_node_id = :n"
                    ),
                    {"p": patient_id, "n": node_id},
                )
            ).scalar_one()
            assert bridge_count == 1

            edge_count = (
                await s.execute(
                    text("SELECT count(*) FROM graph.kg_edges WHERE edge_type = 'relevance_link'")
                )
            ).scalar_one()
            assert edge_count == 0

            event_count = (
                await s.execute(
                    text(
                        "SELECT count(*) FROM events.outbox_events "
                        "WHERE event_type = :et AND correlation_id = :c"
                    ),
                    {"et": RELEVANCE_LINK_CREATED, "c": corr},
                )
            ).scalar_one()
            assert event_count == 1

        # Surfacing: list context for the node returns the link with its tier.
        async with session_factory() as s:
            links = await ExternalEvidenceService(s).list_context_for_node(
                patient_id=patient_id, personal_node_id=node_id
            )
            assert len(links) == 1
            assert links[0].source_quality_tier_snapshot == 2

        # The personal-graph guard physically rejects a relevance_link edge.
        async with session_factory() as s:
            with pytest.raises(Exception):  # noqa: B017 - DB CHECK violation
                await s.execute(
                    text(
                        "INSERT INTO graph.kg_edges "
                        "(id, from_node_id, to_node_id, edge_type, potential_score, "
                        " thread_ids, patient_id, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :n1, :n2, 'relevance_link', 0.5, "
                        " '{}', :p, now(), now())"
                    ),
                    {"n1": node_id, "n2": node_id2, "p": patient_id},
                )
            await s.rollback()

        # Editorial tier downgrade is recorded and applied (usage never upgrades).
        async with session_factory() as s, s.begin():
            await ExternalEvidenceService(s).review_source_tier(
                source_id=source_id,
                new_tier=4,
                reason="Superseded by newer guideline",
                reviewer_actor_id=uuid.uuid4(),
                correlation_id=corr,
                trace_id="x",
            )
        async with session_factory() as s:
            tier = (
                await s.execute(
                    text(
                        "SELECT source_quality_tier FROM external_kg.external_evidence_sources "
                        "WHERE id = :s"
                    ),
                    {"s": source_id},
                )
            ).scalar_one()
            assert tier == 4
    finally:
        if node_id is not None and source_id is not None:
            await _cleanup(session_factory, patient_id, node_id, source_id, corr)
