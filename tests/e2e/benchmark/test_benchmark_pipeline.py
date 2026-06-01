"""E2E validation of the WellBe benchmark corpus against the deterministic
"should-be" expected results.

These tests run against the LIVE kind cluster (namespace ``wellbe``). The session
fixture in ``conftest.py`` resets the pipeline, seeds all five cases in blind mode, and
waits for processing to settle. Each test then asserts the measured Postgres state
equals the deterministic prediction in
``docs/analysis/benchmark-expected-results.md`` section 5.1.

What "validated as designed" means here:
  * C2 -> C4 -> C5 -> C6 is the only pipeline that runs on this corpus.
  * Per-case and global counts match the deterministic forecast to the unit.
  * Evidence linking is exactly-once and 1:1 with facts (post WEL-103/104).
  * Safety invariants hold: only Other/Symptom/Medication node types, no causal/
    diagnosis edges, no orphan claims.
"""

from __future__ import annotations

import asyncpg
import pytest

from . import db, expected

pytestmark = pytest.mark.asyncio

CASE_IDS = [c.case_id for c in expected.CASES]


def _case(case_id: str) -> expected.CaseExpectation:
    return expected.CASES_BY_ID[case_id]


# --- seeding sanity ------------------------------------------------------------


async def test_seed_accepted_all_events(seeded_cluster: dict):
    """The ingestion-worker accepted exactly the expected number of events."""
    sent = seeded_cluster["sent_by_case"]
    for case in expected.CASES:
        assert sent[case.case_id] == case.events, (
            f"{case.case_id}: ingestion accepted {sent[case.case_id]} events, "
            f"expected {case.events}"
        )
    assert sum(sent.values()) == expected.TOTAL_EVENTS


# --- global totals (DB holds ONLY the benchmark after reset) -------------------


async def test_global_totals(conn: asyncpg.Connection):
    assert await db.count_events(conn) == expected.TOTAL_EVENTS
    assert await db.count_facts(conn) == expected.TOTAL_FACTS
    assert await db.count_nodes(conn) == expected.TOTAL_NODES
    assert await db.count_edges(conn) == expected.TOTAL_EDGES
    # C5 corrected behaviour: one PRIMARY link per fact -> link rows == facts.
    assert await db.count_links(conn) == expected.TOTAL_LINKS


# --- per-case structural counts ------------------------------------------------


@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_case_event_count(conn: asyncpg.Connection, case_id: str):
    case = _case(case_id)
    assert await db.events_for(conn, case.patient_id) == case.events


@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_case_fact_count_and_types(conn: asyncpg.Connection, case_id: str):
    case = _case(case_id)
    assert await db.facts_for(conn, case.patient_id) == case.facts_total
    assert await db.fact_type_counts(conn, case.patient_id) == case.fact_types


@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_case_node_count_and_types(conn: asyncpg.Connection, case_id: str):
    case = _case(case_id)
    assert await db.nodes_for(conn, case.patient_id) == case.nodes_total
    assert await db.node_type_counts(conn, case.patient_id) == case.node_types


@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_case_node_identities(conn: asyncpg.Connection, case_id: str):
    """Distinct Symptom/Medication node identities match the prediction exactly."""
    case = _case(case_id)
    assert (
        await db.node_identities(conn, case.patient_id, "Symptom")
        == set(case.symptom_nodes)
    )
    assert (
        await db.node_identities(conn, case.patient_id, "Medication")
        == set(case.medication_nodes)
    )


@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_case_links_one_to_one_with_facts(conn: asyncpg.Connection, case_id: str):
    """Post-fix C5: exactly one PRIMARY evidence link per fact, per case."""
    case = _case(case_id)
    assert await db.links_for(conn, case.patient_id) == case.facts_total


@pytest.mark.parametrize("case_id", CASE_IDS)
async def test_case_no_edges(conn: asyncpg.Connection, case_id: str):
    case = _case(case_id)
    assert await db.edges_for(conn, case.patient_id) == case.edges


# --- safety & provenance invariants (cross-cutting) ----------------------------


async def test_only_keyword_node_types_appear(conn: asyncpg.Connection):
    """The keyword extractor can only ever emit Other/Symptom/Medication nodes.

    None of the richer FACT_TYPE_TO_NODE_TYPE entries (LabResult, Procedure, ...)
    appear, because the rule-based extractor never emits those fact types.
    """
    assert await db.all_node_types(conn) <= expected.ALLOWED_NODE_TYPES


async def test_no_diagnosis_or_causal_edges(conn: asyncpg.Connection):
    """WellBe investigates, never diagnoses. No causal/diagnosis edges may exist.

    On this corpus the auto-linker has no caller, so the graph is edge-free; this
    test also guards the safety ceiling (``may_explain`` is the strongest permitted
    edge; ``diagnoses``/``causes`` are forbidden).
    """
    assert await db.count_edges(conn) == 0
    forbidden = {"diagnoses", "causes", "diagnosis"}
    assert await db.edge_types_present(conn) & forbidden == set()


async def test_no_orphan_claims(conn: asyncpg.Connection):
    """Every fact has at least one evidence link (WB-DEV-008 no-orphan-claims)."""
    assert await db.facts_without_link(conn) == 0


async def test_evidence_links_idempotent_no_orphans(conn: asyncpg.Connection):
    """WEL-103/104: linking is exactly-once. No orphan links; every link is valid;
    each fact carries exactly one PRIMARY link."""
    assert await db.orphan_link_count(conn) == 0
    assert await db.valid_link_count(conn) == expected.TOTAL_FACTS
    assert await db.links_per_fact_distribution(conn) == {1: expected.TOTAL_FACTS}
    assert await db.link_types(conn) <= {"primary"}
