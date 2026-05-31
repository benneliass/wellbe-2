# Decision: Knowledge Graph node/edge type taxonomy and subgraph isolation pattern

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-98  
**Blocks:** WEL-77 — Build Knowledge Graph store with AGE/pgvector and background auto-linking worker

---

## Question

What are the canonical node types and edge types for the Knowledge Graph (C6), how are evidence-weighted edges (PotentialScore) computed and stored using Postgres + Apache AGE, how are per-thread subgraphs isolated, and which graph queries are identified as hot paths requiring recursive CTE optimization?

Specifically:
1. What are the node types — `Entity`, `Symptom`, `Lab`, `Medication`, `Condition`, `Visit`, `Referral`, `HealthSignal`, or other — and what fields are on each node?
2. What are the edge types and their semantics — what is `may_explain`, `co_occurs_with`, `temporally_precedes`, and what is the strongest causal edge allowed (never `causes`)?
3. How is PotentialScore computed — what inputs (co-occurrence frequency, temporal proximity, evidence confidence, user correction) feed the score, and is it computed at write time or query time?
4. How are per-thread subgraphs isolated in Apache AGE — a `thread_id` property on every node/edge, a separate AGE graph per thread, or a label-based partition?
5. Which queries are hot paths that need recursive CTE fallback instead of AGE Cypher?

## Context

C6 is the shared substrate for the entire intelligence layer. It sits at layer L2 and is the primary input for C7 (Health Thread Engine), C8 (Six Memories), and the Intelligence Engines (F-ENGINES). The node/edge type taxonomy is a stable schema contract — once C7 and C8 are built on top of C6, changing node types or edge semantics requires migrations across graph, relational, and API layers simultaneously.

The tech stack has committed to Postgres + Apache AGE for graph storage, with pgvector for semantic similarity. A flagged architectural risk is that AGE's Cypher-wrapper overhead is significant under high write throughput or deep (6+ hop) traversals. WellBe's dominant pattern is 1–2 hop, per-user, thread-scoped reads — which makes AGE the right MVP fit — but the hot-path queries that need recursive CTE optimization must be identified up front.

**Key constraint from the system design:** `may_explain` is the strongest causal edge WellBe is permitted to create. Edges like `causes` or `diagnoses` are prohibited — they would violate the "investigate, never diagnose" principle. The edge type taxonomy must encode this constraint structurally, not just as a policy.

**Phase note:** C6 is post-MVP (WEL-77 under E5: Knowledge Graph, P2-important). The MVP delivers a minimal graph (WB-DEV-009); the auto-linking worker (WB-DEV-010) ships post-MVP. The schema decision still needs to be made before the minimal MVP graph is built.

## Research provided

_Awaiting user research._

_Research received: —_

## Approaches considered

_To be written after research is received._

## Decision

_To be written after research is received and approved._

## Trade-offs accepted

_To be written after research is received and approved._

## Implementation notes

_To be written after approval._

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
