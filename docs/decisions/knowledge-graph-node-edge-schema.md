# Decision: Knowledge Graph node/edge schema and subgraph isolation pattern

**Status:** Proposed  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-98  
**Blocks:** WEL-77 — Build Knowledge Graph Store with typed nodes, evidence-weighted edges, and graph traversal API

---

## Question

What are the canonical node types and edge types for the Knowledge Graph (C6), how are evidence-weighted edges (PotentialScore) computed and stored using Postgres + Apache AGE, how are per-thread subgraphs isolated, and which graph queries are identified as hot paths requiring recursive CTE optimization?

Specifically:
1. What are the initial node type taxonomy and the minimum fields every node must carry?
2. What are the allowed edge types, what are their semantics, and which are explicitly prohibited?
3. How is `PotentialScore` stored and recomputed — as a materialized column, a separate scoring table, or an event-driven worker?
4. How are per-thread and per-patient subgraphs isolated — one AGE graph per thread, one per patient, or one global graph with filter predicates?
5. What are the identified hot-path queries and what indexes support them?

## Context

C6 is the structured knowledge layer that connects extracted facts, health signals, conditions, and clinical events into a typed, evidence-weighted graph. It sits at layer L2 and is consumed by C7 (Health Thread context), C8 (Six Memories), C10 (Intelligence Engines), and the visualization layer. The graph must be queryable in two modes: fast relational queries for API hot paths, and flexible Cypher traversal for exploration and visualization.

The safety model places a hard constraint on edge semantics: WellBe is not a diagnostic system. The graph must not encode causal or diagnostic certainty — the strongest allowed causal-adjacent edge is `may_explain`. Diagnostic or finality edges (`causes`, `diagnoses`, `rules_out`, etc.) are prohibited by schema design, not just convention.

The tech stack has committed to PostgreSQL 17 + Apache AGE for graph storage and Cypher queries, pgvector for semantic embeddings, and relational tables as the authoritative hot-path store.

## Research provided

### Executive summary (C6)

C6 stores a typed, evidence-weighted graph projection with safety-limited edge semantics. Relational `kg_nodes` and `kg_edges` tables are authoritative for hot-path API queries and enforcement; Apache AGE is a graph/Cypher projection for traversal and visualization. `PotentialScore` is materialized on the edge as a versioned score with scoring inputs stored in a jsonb column, recomputed asynchronously by a scoring worker when new evidence arrives. Subgraph isolation uses `patient_id` and `thread_ids` properties plus RLS at the relational layer — not one AGE graph per thread.

### Q1 — Node type taxonomy

**Recommended initial node types:**
```
Thread, RawContextEvent, ExtractedFact, HealthSignal,
Symptom, Finding, LabTest, LabResult, Medication,
ProcedureOrTest, Referral, Visit, Clinician, Organization,
BodyRegion, TimePoint, TimeInterval, ConditionHypothesis,
PendingItem, Document
```

**Important:** use `ConditionHypothesis` over bare `Condition` for inferred graph nodes. If a diagnosis appears in an imported medical record, model it as a sourced `Finding` or `ConditionMention` — not as a WellBe final conclusion. This enforces the safety principle that WellBe does not diagnose.

**Minimum fields on every node:**
```
id, patient_id, node_type, label,
normalized_key (nullable), code_system (nullable), code (nullable),
thread_ids (array), evidence_refs (array), confidence,
status, created_at, updated_at,
embedding_id (nullable, FK to pgvector store),
metadata (jsonb)
```

### Q2 — Edge type taxonomy and semantics

**Allowed edge types:**
```
belongs_to_thread, mentioned_in, supported_by,
co_occurs_with, temporally_precedes, same_as, part_of,
located_in, measured_by, treated_with, referred_to,
contradicted_by, may_explain
```

**Prohibited edge types (schema-enforced):**
```
causes, diagnoses, confirms_diagnosis, rules_out, proves
```

`may_explain` is the strongest allowed causal-adjacent edge. It means there is evidence that entity A may be relevant to understanding entity B — not that A caused B. Enforcement:
- An `edge_type` lookup table lists exactly the allowed values
- C6 service validates edge type at write time against the allowed list
- Database FK/check constraint against the allowed-edge-types table
- Tests that prohibited names cannot be inserted
- Migration review rule: any migration adding an edge type requires explicit approval

### Q3 — PotentialScore computation and storage

**Recommended approach:** materialize PotentialScore on the edge row with versioned inputs; recompute asynchronously when new evidence arrives.

```
kg_edges:
  potential_score (numeric),
  score_version (integer),
  score_inputs (jsonb),
  last_scored_at (timestamptz),
  needs_rescore (boolean)
```

**Scoring inputs for PotentialScore:**
- C5 evidence confidence
- Co-occurrence frequency
- Temporal proximity
- Source quality
- Semantic similarity (pgvector cosine distance)
- Same-thread boost
- Cross-thread recurrence
- User confirmation/correction weight
- Contradiction penalty
- Recency decay

**Scoring worker trigger events:**
```
fact.extracted, health_signal.created, evidence.linked,
correction.applied, thread.state_changed
```

When any of these events arrive, the C6 scoring worker identifies affected edge candidates and recomputes `potential_score`. If the score changes meaningfully, it emits `graph.edge_scored`. Use pgvector for semantic candidate matching (finding candidate edges where two nodes are semantically close) — not as the final edge score itself.

### Q4 — Per-thread subgraph isolation

**Recommended approach:** one graph namespace per environment (or tenant); `patient_id` and `thread_ids` on every node and edge; RLS at the relational layer; explicit WHERE filters in AGE Cypher queries.

**Rejected approach:**
```
graph_<thread_id>   ← one AGE graph per thread
```
This creates unmanageable graph proliferation and makes cross-thread queries (which are sometimes needed for pattern detection) impossible.

**Recommended approach:**
```
one graph: e.g. "wellbe" or "wellbe_tenant_<id>"
every node: patient_id, thread_ids[] (multi-valued)
every edge: patient_id, thread_ids[]
relational mirrors: kg_nodes, kg_edges (with indexes)
authorization: RLS on relational tables; explicit predicates in AGE queries
```

**Relational mirrors for hot paths:**
```
kg_nodes(patient_id, node_id, node_type, thread_ids, label, normalized_key, confidence, ...)
kg_edges(patient_id, from_node_id, to_node_id, edge_type, potential_score, thread_ids, ...)
```

### Q5 — Hot-path queries and indexes

**Identified hot paths:**
1. Fetch all nodes and edges within 2 hops of a thread → used by C7 for thread context
2. Fetch highest-PotentialScore edges for a node → used by C8/C10 for memory and intelligence
3. Fetch all edges among a selected symptom/finding set → used by C10 pattern detection
4. Fetch evidence behind an edge → used by C13/UI for provenance display
5. Find `same_as` candidates for entity resolution → used by C4/C6 for deduplication
6. Fetch graph summary for C7 thread context

**Recommended indexes:**
```sql
CREATE INDEX ON kg_nodes(patient_id, node_type);
CREATE INDEX ON kg_nodes(patient_id, normalized_key);
CREATE INDEX ON kg_edges(patient_id, from_node_id, edge_type, potential_score DESC);
CREATE INDEX ON kg_edges(patient_id, to_node_id, edge_type);
CREATE INDEX ON kg_edges(patient_id, thread_id, potential_score DESC);
CREATE INDEX ON kg_edges(patient_id, edge_type);
```

**Default routing rule:**
- C13/C7/C8/C10 hot reads → relational/CTE path (recursive CTEs for hop traversal)
- Graph visualization (F-KG-VIZ) and analyst/debug queries → Apache AGE Cypher path

**AGE performance note:** based on Azure guidance on Apache AGE performance, hot API paths should use relational mirrors + indexed adjacency queries, not AGE Cypher for production latency-sensitive paths.

### References

- Apache AGE graph model documentation — https://age.apache.org/age-manual/master/intro/graphs.html
- Azure guidance: Apache AGE performance — https://learn.microsoft.com/en-us/azure/postgresql/azure-ai/generative-ai-age-performance
- pgvector documentation — https://github.com/pgvector/pgvector
- PostgreSQL 17 WITH / recursive queries — https://www.postgresql.org/docs/17/queries.html

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| One AGE graph per thread | Rejected | Graph proliferation; cross-thread queries impossible |
| One AGE graph per patient | Partially adopted | Better, but still over-partitioned; per-patient isolation done via `patient_id` property + RLS instead |
| One global graph with `patient_id` + `thread_ids` properties | **Accepted** | Manageable; authorization via RLS and explicit predicates |
| Bare `Condition` node type | Rejected | Implies WellBe confirms a diagnosis — safety violation |
| `ConditionHypothesis` + `Finding` / `ConditionMention` | **Accepted** | Preserves investigative posture; `ConditionHypothesis` is never a diagnosis |
| `causes` / `diagnoses` edge types | Rejected | Prohibited by safety model — WellBe does not diagnose or assert causation |
| `may_explain` as strongest causal edge | **Accepted** | Investigative posture only; enforcement at schema + service + test layers |
| PotentialScore as runtime-computed value (no materialization) | Rejected | Hot-path performance unacceptable; every edge read would trigger computation |
| PotentialScore as materialized column + async recompute on events | **Accepted** | Fast reads; eventual consistency accepted for score freshness |
| AGE Cypher for all queries including hot paths | Rejected | AGE Cypher has unpredictable latency for production API paths |
| Relational mirrors (kg_nodes, kg_edges) for hot paths + AGE for exploration | **Accepted** | Predictable performance for API; full graph power for visualization |

## Decision

C6 stores a typed, evidence-weighted graph with safety-limited edge semantics. Relational `kg_nodes` and `kg_edges` tables are authoritative for hot-path API queries and enforcement; Apache AGE is a graph/Cypher projection for traversal and visualization. `may_explain` is the strongest allowed causal-adjacent edge; `causes`, `diagnoses`, `confirms_diagnosis`, `rules_out`, and `proves` are prohibited at schema, service, and test layers. `PotentialScore` is materialized on the edge row with versioned inputs and recomputed asynchronously by scoring workers that consume evidence/fact events. Subgraph isolation uses `patient_id` and `thread_ids` properties plus RLS — not one AGE graph per thread.

## Trade-offs accepted

- Dual representation (relational mirrors + AGE projection) adds write complexity and projection work — accepted for predictable hot-path performance and simpler authorization.
- PotentialScore is eventually consistent (recomputed asynchronously) — accepted; edge scores are not real-time; freshness is sufficient, not instant.
- Single AGE graph namespace means cross-patient queries are structurally possible — mitigated by RLS and explicit predicates; the C1 cross-patient gate is the primary guard.

## Implementation notes

- The `edge_type` lookup table must be the single source of truth for allowed edge types. The migration review process for this table is mandatory.
- `ConditionHypothesis` node type and its semantics must be documented in the C13 API contract to prevent consumer code from displaying it as a confirmed diagnosis.
- Events emitted via outbox: `graph.node_created`, `graph.edge_created`, `graph.edge_scored`, `graph.edge_retracted`.
- `needs_rescore = true` is set by the event consumer on affected edges and is consumed by the scoring worker to determine the next batch.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
