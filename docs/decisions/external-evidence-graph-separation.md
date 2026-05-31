# Decision: External Evidence Graph separation and relevance-link semantics

**Status:** Proposed — awaiting user approval  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-130  
**Blocks:** WEL-116 (External Evidence Graph), WEL-117 (Research Relevance engine), WEL-124 (C3 adapter), WEL-126 (C5 provenance), WEL-135 (C6 retrofit)

---

## Question

How should the **External Evidence Graph** (C16) be separated from the personal Knowledge Graph (C6) and Evidence & Provenance Service (C5), and how are **relevance links** scored and constrained so external claims never become facts about the user?

Specifically:
1. Physical/logical separation: separate store, separate schema in the same store, or namespaced subgraph — and how is cross-contamination structurally prevented?
2. How is `source_quality_tier` (Tier 1–5) assigned, stored, and surfaced, and can it ever be upgraded by usage?
3. How is a `relevance_link` scored (confidence) and what prevents an external claim from being asserted as a personal fact?
4. How does C5 provenance treat external sources differently from personal sources (so external claims are never counted as evidence about the user)?

## Context

The vision's core safety stance is that external medical knowledge is *context, never fact about the user*. Blending the external graph into C6, or letting C5 score external claims as personal evidence, would break that guarantee and the "no orphan claims" provenance rule. C5 and C6 are both in-flight/Done foundation components, so the separation boundary and relevance-link contract must be settled before C16 is built and before any retrofit touches C5/C6.

## Research provided

_Research received: 2026-05-31_ — external consultant report, archived verbatim at [research-inputs/wellbe_c6_kg_retrofit_report.md](research-inputs/wellbe_c6_kg_retrofit_report.md) (source `.docx` alongside it). Section 2 of the report addresses this decision. Source basis cited in the report: HL7 FHIR Provenance/Consent/Evidence/Citation/ArtifactAssessment/DetectedIssue [S1, S3, S8, S9, S10, S15]; W3C PROV and SPARQL named graphs [S2, S7]; PostgreSQL Row-Level Security and Schemas [S4, S5]; Apache AGE [S6]; SNOMED CT context modeling [S23, S24].

## Approaches considered

_Based only on the provided research (report §2.2)._

1. **Separate database / separate graph store for C16.** Strongest structural separation (separate backups, roles, query paths); avoids treating public medical knowledge as tenant-owned. Cons: cross-store transactions and referential integrity must be handled by service checks or repair jobs (no DB FK), harder local dev/migrations, async indexing. Grounded in W3C PROV / FHIR Provenance treating provenance as source-contextual metadata [S1, S2].
2. **Separate `external_kg` schema in the same PostgreSQL DB + service role + patient-scoped bridge table with RLS (recommended).** Strong logical boundary at lower operational cost; bridge can use transactional FKs to both personal and external tables while keeping patient RLS on the bridge; ships as an additive migration; fits C6's relational-authoritative + optional-AGE architecture. Cons: Postgres schemas are namespaces, **not** hard isolation [S5] — must be paired with explicit grants, search-path discipline, RLS, service roles, security-definer views, and tests. Grounded in PG RLS default-deny [S4], FHIR Citation/ArtifactAssessment [S8, S9].
3. **Namespaced subgraph / separate Apache AGE graph (`wellbe_external`) in the same DB.** Useful for visualization/Cypher/research-watch traversal [S6]. Cons: insufficient as source-of-truth separation because C6's authoritative store is relational, and SPARQL precedent shows named graphs can be merged into the default graph — exactly the contamination to prevent [S7]. Projection mechanism, not a safety boundary.
4. **Single `kg_nodes`/`kg_edges` with `scope`/`is_external` + `patient_id IS NULL` external rows (rejected).** Minimal tables and reuses edge scoring, but makes external knowledge reachable through the same node/edge path as personal facts, risks C5/auto-linker/outputs counting external content as personal, and weakens the "every C6 row is patient-scoped" invariant. SNOMED context ambiguity [S23] and FHIR DetectedIssue's patient-specific vs. general-knowledge boundary [S15] argue against mixing.

## Decision

_Proposed (report §2.3, §6.1):_ Adopt a **separate C16 External Evidence Graph in an `external_kg` schema** (same PostgreSQL DB for v1) with separate ownership/roles, and store personal↔external relationships **only** in a patient-scoped, RLS-protected `external_bridge.relevance_links` table. **Do not** store external nodes in `graph.kg_nodes`; **do not** store `relevance_link` rows in `graph.kg_edges` (enforced by a guard); **do not** let C5 personal evidence scoring consume external references. `source_quality_tier` is an editorial/source-classification attribute (Tier 1–5), never usage-derived — usage can never upgrade a tier; changes only via auditable editorial events (retraction, guideline update, peer-review change, manual review). `relevance_score` is a separate topical-relatedness metric (not `potential_score`, not diagnostic confidence). Treat as a staged hardening path: Stage 1 (WEL-135) same DB + separate schemas + role + bridge RLS; Stage 2 (future) move `external_kg` to a separate database/store behind the same bridge API if stronger isolation is needed.

Satisfies the hard constraints: **G1** (external claims never stored as personal facts; only `relevance_link` = "is relevant context for"), **G2** (external rows structurally outside `kg_nodes`/`kg_edges`; C5 ignores bridge rows), **G3** (personal facts still require C5 provenance), **G4** (external context cannot close a thread/investigation), **G5** (additive), **G6** (personal RLS intact; bridge patient-scoped; external tables not exposed as personal rows), **G7** (relevance-link create/view passes C1/C17 grant checks).

## Trade-offs accepted

- Less graph-traversal convenience — cross-boundary traversal needs a join/service call, not one `kg_edges` hop.
- More schema surface (bridge + external tables → more migrations/tests).
- Not maximum physical isolation in v1; mitigated by strict role grants, no external rows in C6 tables, bridge RLS, and service-level tests.
- Source quality and relevance are kept separate concepts — a low-quality anecdote can be topically relevant but must surface with low tier + strict contextual warning.

## Implementation notes

_From report §2.5 (verbatim DDL in the archived report)._

- **Node-type retrofit:** keep PascalCase codes; expand `ck_node_type` to add `Investigation`, `Theory`; add a `graph.node_type_aliases` (or longer-term `graph.node_types` reference table) to expose lowercase API aliases. Do not rename existing rows.
- **Edge vocabulary:** add categories `evidential`, `process`, `external_context`; insert `evidence_for`/`evidence_against` (evidential), `investigates` (process), `relevance_link` (external_context). Store `evidence_for`/`evidence_against`/`investigates` in `kg_edges` only when both endpoints are patient-scoped; **register but never store** `relevance_link` in `kg_edges` (add a CHECK/trigger rejecting it).
- **External schema:** `external_kg.external_evidence_sources` (source_type, `source_quality_tier 1–5`, tier_reason, citation/url/doi, retraction_status, assigned_by/at) and `external_kg.external_claims` (claim_text, claim_kind, population_context, evidence_attributes). Tier-history table `external_kg.source_quality_reviews`.
- **Bridge:** `external_bridge.relevance_links` (patient_id, personal_node_id FK→`kg_nodes`, external_source_id/claim_id FKs, `edge_type='relevance_link'` CHECK, `relevance_score numeric(5,4)`, `source_quality_tier_snapshot`, `context_only IS TRUE` CHECK, grant fields, UNIQUE) with RLS by `app.patient_id` and a trigger asserting `kg_nodes.patient_id = relevance_links.patient_id`.
- **Relevance scoring (v1):** `0.35*entity_or_code_match + 0.25*semantic_similarity + 0.15*thread_context_match + 0.10*population_applicability + 0.10*source_currentness + 0.05*reviewer/user_signal`, clamped [0,1]; tier drives surfacing caps + required labels, not relatedness.
- **C5 provenance:** add `evidence.evidence_links.source_scope` defaulting `'personal'` with CHECK `= 'personal'` (or enforce in service+tests first); external context lives in a separate `evidence.external_context_refs`/bridge and never enters `PotentialScoreComputer`.
- **Open risks:** visualization leakage (C10 must gate graph summaries; external nodes render with distinct label+tier+warning); relevance_score vs potential_score confusion (separate table/column/service + tests); schema separation over-trust (roles, forced search_path, RLS, tests); external text copied into `kg_nodes.metadata` (prohibit); tier gaming (usage never upgrades tier).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
