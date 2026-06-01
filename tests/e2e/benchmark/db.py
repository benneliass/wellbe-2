"""Read-only-ish Postgres helpers for the benchmark E2E validation.

The only write performed here is the deliberate pipeline reset (TRUNCATE) used to
guarantee a clean, reproducible run. All assertions read via plain SELECT/COUNT.

Table reference (confirmed against the live schema):
  vault.raw_context_events       -- C2 vault rows
  processing.extracted_facts     -- C4 facts
  evidence.evidence_links        -- C5 evidence links
  graph.kg_nodes / graph.kg_edges-- C6 graph
"""

from __future__ import annotations

import os

import asyncpg

PG_DSN = os.environ.get(
    "WELLBE_PG_DSN",
    "postgresql://wellbe:wellbe_dev@localhost:5432/wellbe",
)

# Every pipeline table that holds per-event derived state. TRUNCATE bypasses the
# row-level append-only trigger on vault.raw_context_events (the trigger is
# BEFORE UPDATE OR DELETE, which does not fire on TRUNCATE). CASCADE also clears
# external_bridge.relevance_links (FK -> graph.kg_nodes).
_RESET_TABLES = (
    "vault.raw_context_events",
    "processing.extracted_facts",
    "processing.health_signals",
    "evidence.evidence_links",
    "graph.kg_nodes",
    "graph.kg_edges",
    "events.outbox_events",
)


async def connect() -> asyncpg.Connection:
    return await asyncpg.connect(PG_DSN)


async def reset_pipeline(conn: asyncpg.Connection) -> None:
    await conn.execute(f"TRUNCATE {', '.join(_RESET_TABLES)} CASCADE;")


# --- global counts -------------------------------------------------------------


async def count_events(conn: asyncpg.Connection) -> int:
    return await conn.fetchval("SELECT count(*) FROM vault.raw_context_events")


async def count_facts(conn: asyncpg.Connection) -> int:
    return await conn.fetchval("SELECT count(*) FROM processing.extracted_facts")


async def count_links(conn: asyncpg.Connection) -> int:
    return await conn.fetchval("SELECT count(*) FROM evidence.evidence_links")


async def count_nodes(conn: asyncpg.Connection) -> int:
    return await conn.fetchval("SELECT count(*) FROM graph.kg_nodes")


async def count_edges(conn: asyncpg.Connection) -> int:
    return await conn.fetchval("SELECT count(*) FROM graph.kg_edges")


# --- per-patient counts --------------------------------------------------------


async def events_for(conn: asyncpg.Connection, patient_id: str) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM vault.raw_context_events WHERE patient_id = $1",
        patient_id,
    )


async def facts_for(conn: asyncpg.Connection, patient_id: str) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM processing.extracted_facts WHERE patient_id = $1",
        patient_id,
    )


async def links_for(conn: asyncpg.Connection, patient_id: str) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM evidence.evidence_links WHERE patient_id = $1",
        patient_id,
    )


async def nodes_for(conn: asyncpg.Connection, patient_id: str) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM graph.kg_nodes WHERE patient_id = $1",
        patient_id,
    )


async def edges_for(conn: asyncpg.Connection, patient_id: str) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM graph.kg_edges WHERE patient_id = $1",
        patient_id,
    )


async def fact_type_counts(conn: asyncpg.Connection, patient_id: str) -> dict[str, int]:
    rows = await conn.fetch(
        "SELECT fact_type, count(*) AS n FROM processing.extracted_facts "
        "WHERE patient_id = $1 GROUP BY fact_type",
        patient_id,
    )
    return {r["fact_type"]: r["n"] for r in rows}


async def node_type_counts(conn: asyncpg.Connection, patient_id: str) -> dict[str, int]:
    rows = await conn.fetch(
        "SELECT node_type, count(*) AS n FROM graph.kg_nodes "
        "WHERE patient_id = $1 GROUP BY node_type",
        patient_id,
    )
    return {r["node_type"]: r["n"] for r in rows}


async def node_identities(
    conn: asyncpg.Connection, patient_id: str, node_type: str
) -> set[str]:
    rows = await conn.fetch(
        "SELECT normalized_key FROM graph.kg_nodes "
        "WHERE patient_id = $1 AND node_type = $2",
        patient_id,
        node_type,
    )
    return {r["normalized_key"] for r in rows}


async def all_node_types(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT DISTINCT node_type FROM graph.kg_nodes")
    return {r["node_type"] for r in rows}


# --- safety / provenance invariants --------------------------------------------


async def orphan_link_count(conn: asyncpg.Connection) -> int:
    """Links whose source fact no longer exists (the WEL-103/104 artifact)."""
    return await conn.fetchval(
        "SELECT count(*) FROM evidence.evidence_links l "
        "WHERE NOT EXISTS (SELECT 1 FROM processing.extracted_facts f WHERE f.id = l.source_id)"
    )


async def valid_link_count(conn: asyncpg.Connection) -> int:
    return await conn.fetchval(
        "SELECT count(*) FROM evidence.evidence_links l "
        "WHERE EXISTS (SELECT 1 FROM processing.extracted_facts f WHERE f.id = l.source_id)"
    )


async def facts_without_link(conn: asyncpg.Connection) -> int:
    """No-orphan-claims rule: every fact must have at least one evidence link."""
    return await conn.fetchval(
        "SELECT count(*) FROM processing.extracted_facts f "
        "WHERE NOT EXISTS (SELECT 1 FROM evidence.evidence_links l WHERE l.source_id = f.id)"
    )


async def links_per_fact_distribution(conn: asyncpg.Connection) -> dict[int, int]:
    rows = await conn.fetch(
        "SELECT cnt AS links_per_fact, count(*) AS num_facts FROM ("
        "  SELECT source_id, count(*) AS cnt FROM evidence.evidence_links GROUP BY source_id"
        ") s GROUP BY cnt ORDER BY cnt"
    )
    return {r["links_per_fact"]: r["num_facts"] for r in rows}


async def link_types(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT DISTINCT link_type FROM evidence.evidence_links")
    return {r["link_type"] for r in rows}


async def edge_types_present(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch("SELECT DISTINCT edge_type FROM graph.kg_edges")
    return {r["edge_type"] for r in rows}
