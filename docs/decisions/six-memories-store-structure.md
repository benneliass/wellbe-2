# Decision: Six Memories store structure and authored-vs-derived population model

**Status:** Approved
**Date opened:** 2026-06-01
**Research received:** 2026-06-01
**Date approved:** 2026-06-01
**Approved by:** User
**Jira Spike:** WEL-136
**Blocks:** WEL-70 — Build Story, Clinical, Pattern, Decision, Responsibility, and Equity memory models

---

## Question

How should the Six Memories store (C8) structure, partition, and populate each memory type (Story / Clinical / Pattern / Decision / Responsibility / Equity) — which are user-authored vs system-derived, and how do they read from the C6 knowledge graph and cite C5 provenance without becoming a competing source of truth?

Specifically:
1. Is each memory type a distinct table/schema, or one polymorphic store with a `memory_type` discriminator?
2. Which memory types are authored by the user, which are derived from C4/C5/C6, and which are hybrid?
3. How does a derived memory entry reference its source (C5 evidence links / C6 nodes) so it stays consistent and correctable, rather than copying facts?
4. How are corrections (C11) reflected in memory reads without mutating source data?

## Context

C8 sits at L4 and is read by C13 (and the future UI). Affected core component: Six Memories Store (C8), with hard dependencies on Evidence & Provenance (C5) and Knowledge Graph Store (C6). If memory entries duplicate facts instead of referencing C5/C6, we create a second source of truth that can silently diverge, violate the "no orphan claims" provenance rule, and make C11 corrections impossible to propagate. The authored-vs-derived split becomes a stable contract once C13 exposes memory surfaces, so guessing wrong is expensive.

## Research provided

_Source: provided research report `wellbe_c8_c9_c11_research_report_2026-06-01.docx` (GPT-5.5 Pro for WellBe review, dated 2026-06-01), section "C8 Six Memories Store — WEL-136 / WEL-70". Recorded as a faithful summary; external source labels [S1]–[S20] are the report's own cited-source register._

### Source findings the report relied on (C8)

- **Provenance as a graph of sources, not copied truth.** W3C PROV-O models derivation as a relation from one entity to another and supports qualified derivation when the derivation itself needs metadata [S1]. The report uses this to argue C8 should store memory entries as derived entities that link to source entities, rather than duplicating facts.
- **Target-centric provenance.** FHIR Provenance links provenance records to target resources and allows multiple provenance records per target [S2]. The report concludes each visible memory entry should be a provenance target with C5 evidence links.
- **Generated summaries should limit copied content.** FHIR Narrative allows generated content from referenced resources but warns referenced resources may be updated, so copied content should be limited [S3]. The report treats this as precedent for storing pointers + minimal display metadata instead of derived fact copies.
- **CQRS / materialized views are valid only if rebuildable.** CQRS and materialized-view patterns support read-optimized projections but introduce synchronization and eventual-consistency risk [S17, S18, S20]. The report requires any C8 projection to be rebuildable and to never become the truth source.

### WellBe constraints the report says dominate the design (C8)

- C8 memory entries are derived objects and must satisfy C5 no-orphan provenance before becoming visible.
- C8 cannot be a second source of truth; it must reference C5/C6/C7/C9/C15 rather than copy clinical facts.
- Corrections in C11 must change C8 reads without mutating C8 historical entries or source data.
- Pattern Memory is safety-sensitive and must stay below the diagnosis ceiling: it may surface patterns, persistent symptoms, repeat visits, uncertainty, and follow-up criteria, but not diagnosis, differential ranking, or "rule out" claims.
- Any AI-generated or AI-assisted memory summary must pass C10 and carry the render token and output hash required by C13/C10.

## Approaches considered

_Each approach is taken from the report's "Approaches considered" for C8 and grounded only in that report. Sub-question references: (1) table/schema shape; (2) authored vs derived vs hybrid; (3) reference-not-copy mechanism; (4) correction propagation on read._

### Approach 1 — Six dedicated tables, one per memory type (sub-questions 1, 3)

Distinct `c8.story_memory` … `c8.equity_memory` tables with type-specific columns. **Pros:** strong type-specific constraints, easy indexing, localizes sensitive Equity fields. **Cons:** six divergent write paths increase the chance of provenance-enforcement gaps; shared lifecycle / C5 links / C11 resolution / C13 DTOs / audit / access predicates get duplicated; cross-memory chronology queries get harder; adding a seventh surface duplicates more infra. The report rates this acceptable only if a shared base table enforces provenance/lifecycle; alone it raises second-source-of-truth risk.

### Approach 2 — One polymorphic table with `memory_type` + JSONB payload (sub-questions 1, 2)

Single `c8.memory_entries` with `memory_type`, `authorship_mode`, and `payload jsonb`. **Pros:** single provenance gate, single audit path, uniform C13 contract, easy chronological thread view, flexible during MVP. **Cons:** JSONB can hide type-specific constraints and tempt engineers to store copied facts in payload; query/schema-evolution can get messy. The report rates it a good base pattern but insufficient without typed pointer constraints and lint/test enforcement that payload cannot hold authoritative clinical values.

### Approach 3 — Hybrid base table + typed pointer satellite tables (sub-questions 1, 2, 3, 4) — recommended

One append-only `c8.memory_entries` base table with shared provenance/lifecycle fields, plus narrow typed satellite tables (`c8.memory_source_refs`, `c8.pattern_memory_refs`, `c8.responsibility_pending_refs`, `c8.equity_access_attrs`) for memory-specific references and constraints. Precedent: CQRS/read-model base + typed projections, PROV-style entity references, FHIR-style resources with external Provenance [S1, S2, S17, S18]. **Pros:** one shared provenance/audit/read contract; type-specific constraints where needed; makes pointer tables first-class so copied-fact payloads are prevented; projections are rebuildable; C11 overlay resolution applied consistently at the read layer. **Cons:** more tables than pure polymorphic; requires repository/service discipline + tests to prevent payload misuse; some reads need joins through C5/C6/C11. The report rates this the best fit.

### Approach 4 — Pure computed-on-read views, no persisted entries (sub-questions 1, 3)

Derive every memory surface dynamically from C5/C6/C7/C9/C15 at request time. **Pros:** always fresh, minimal storage, no materialized drift. **Cons:** weak audit of what was shown when; hard to attach user-authored Story/Decision/Responsibility/Equity entries; expensive and fragile cross-component reads; no durable memory artifacts for C13/C12. The report rates this useful as a fallback/resolution path but insufficient as the primary store.

## Decision

**(Proposed — pending user approval.)** Adopt a **hybrid C8 store** (report Approach 3): a single append-only `c8.memory_entries` base table keyed by `patient_id`, `thread_id`, and `memory_type`, carrying `authorship_mode` and lifecycle fields, plus small typed satellite tables that hold source pointers and type-specific constraints. C8 stores user-authored entries and rebuildable derived **pointer projections**, but never stores derived clinical facts as authoritative payload. Authored/derived/hybrid split: **Story** and **Equity & Access** are controller-authored or controller-confirmed; **Clinical** and **Pattern** are derived; **Decision** and **Responsibility** are hybrid. Every visible memory entry is written through the C5 gate and must have ≥1 C5 evidence link. Derived entries reference C5 evidence links, C6 node/edge IDs, C7 transition IDs, C9 pending-item IDs, or C15 theory/evaluation IDs; **displayed values are resolved at read time through the shared C11 correction-resolution layer plus current C5/C6 state** — C8 never implements its own correction precedence.

## Trade-offs accepted

- Read-time joins are accepted to prevent C8 from becoming a competing source of truth.
- Eventual projection staleness is accepted only for pointer indexes, never for displayed clinical facts; a stale pointer projection must refresh on read or return a safe `projection_stale` marker and trigger rebuild.
- JSONB flexibility is accepted only for non-authoritative UI metadata — never for resolved medical values, source-derived assertions, or unprovenanced claims.
- Historical memory entries remain append-only even when no longer current; read models may downgrade/suppress them from the current view, but C12/C5 history stays intact.
- Equity/access memory is intentionally conservative: sensitive access/identity attributes should be controller-authored or controller-confirmed; system inference alone should not become durable Equity Memory.

## Implementation notes

_All schema/DDL and tests below are the report's recommendation, recorded for the implementer; exact column shapes are subject to the approved C5 schema._

### Authored / derived / hybrid classification (report table)

| Memory | Mode | Population rule | Primary source-pointer rule |
|---|---|---|---|
| Story | User-authored, system-indexed | User's own words, concerns, timeline, fear, theory, daily-life impact. Summaries/tags are derived and C10-gated if AI-assisted. | Link to C2 raw user input + C5 evidence link; optional C6 symptom/timeline nodes. |
| Clinical | Derived from sourced records | Imported problems, meds, allergies, labs, imaging, vitals, notes, imported diagnosis mentions. Render as "source record says", not a WellBe conclusion. | Link to C5 evidence links + C6 Finding / ConditionMention / observation nodes. No `Condition` diagnosis conclusion. |
| Pattern | Derived | Repeat visits, persistent symptoms after normal tests, trends, worsening patterns, unresolved complaints, post-C10 theory-evaluation summaries. | Link to C6 scored edges/nodes, C14 investigation IDs, C15 `source_theory_id`/`source_evaluation_id`, C10 gate ID for summaries. |
| Decision | Hybrid | User/caregiver/clinician accepted notes + C14/C15 decision history (considered, uncertain, missing data, reassessment triggers). | Link to C14/C15 records, C7 transitions, source evidence refs, accepted role annotations via C11 when applicable. |
| Responsibility | Hybrid, operational | Owners, due dates, unknown owner/contact, pending results, referrals, follow-up tasks, next actions. | Link to C9 `pending_item_id` as the authoritative operational object + C5 source evidence. |
| Equity & Access | User-authored or controller-confirmed hybrid | Language, transport, digital access, disability accommodations, caregiver involvement, trust/cultural safety, access barriers. | Link to C2 user statement or controller confirmation; system-derived suggestions stay pending confirmation. |

### Storage sketch (report DDL, reformatted)

```sql
CREATE SCHEMA IF NOT EXISTS c8;
CREATE TYPE c8.memory_type AS ENUM (
  'story', 'clinical', 'pattern', 'decision', 'responsibility', 'equity_access');
CREATE TYPE c8.authorship_mode AS ENUM (
  'controller_authored', 'controller_confirmed',
  'role_authored_pending_acceptance', 'system_derived', 'hybrid');
CREATE TYPE c8.memory_lifecycle_state AS ENUM (
  'draft', 'visible', 'not_current', 'superseded_by_correction',
  'projection_stale', 'archived');
CREATE TABLE c8.memory_entries (
  memory_entry_id uuid PRIMARY KEY,
  patient_id uuid NOT NULL,
  thread_id uuid NOT NULL,
  memory_type c8.memory_type NOT NULL,
  authorship_mode c8.authorship_mode NOT NULL,
  lifecycle_state c8.memory_lifecycle_state NOT NULL DEFAULT 'draft',
  title text NULL,
  display_intent text NOT NULL DEFAULT 'memory_surface',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,    -- non-authoritative metadata only
  source_version_hash text NULL,
  source_projection_version bigint NOT NULL DEFAULT 0,
  c10_gate_id uuid NULL,
  created_by_actor jsonb NOT NULL,
  accepted_by_controller_actor jsonb NULL,
  accepted_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  visible_at timestamptz NULL,
  superseded_at timestamptz NULL,
  idempotency_key text NOT NULL UNIQUE,
  CHECK (jsonb_typeof(payload) = 'object'));
CREATE TABLE c8.memory_source_refs (
  memory_entry_id uuid NOT NULL REFERENCES c8.memory_entries(memory_entry_id),
  source_ref_id uuid NOT NULL,
  source_ref_type text NOT NULL CHECK (source_ref_type IN (
    'c2_raw_event', 'c4_extracted_fact', 'c5_evidence_link',
    'c6_kg_node', 'c6_kg_edge', 'c7_thread_transition',
    'c9_pending_item', 'c14_investigation', 'c15_theory',
    'c15_theory_evaluation', 'c10_gate', 'c11_correction')),
  source_ref_version text NULL,
  field_path text NULL,
  link_role text NOT NULL CHECK (link_role IN (
    'primary', 'corroborating', 'contextual', 'contradicting', 'display_anchor')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (memory_entry_id, source_ref_id, source_ref_type, coalesce(field_path, '')));
CREATE TABLE c8.pattern_memory_refs (
  memory_entry_id uuid PRIMARY KEY REFERENCES c8.memory_entries(memory_entry_id),
  min_current_score numeric NULL,
  current_score numeric NULL,
  current_score_asof timestamptz NULL,
  source_theory_id uuid NULL,
  source_evaluation_id uuid NULL,
  c10_gate_id uuid NOT NULL,
  safety_level text NOT NULL,
  CHECK (safety_level IN ('non_diagnostic_pattern', 'watchful_waiting', 'needs_clinician_review')));
CREATE TABLE c8.responsibility_memory_refs (
  memory_entry_id uuid PRIMARY KEY REFERENCES c8.memory_entries(memory_entry_id),
  pending_item_id uuid NOT NULL,
  pending_item_version bigint NOT NULL,
  responsibility_role text NOT NULL CHECK (responsibility_role IN (
    'patient', 'caregiver', 'clinician', 'care_team', 'admin', 'unknown')));
```

The C5 write gate should reject `lifecycle_state = 'visible'` unless C5 evidence links exist for the `memory_entry_id`. The invariant (not the exact FK shape) is what matters: C8 cannot make a visible memory entry without C5 provenance.

### Read-resolution algorithm (report)

1. Resolve the caller's C1/C17 `AccessPredicate` before retrieval.
2. Load C8 memory entries + source refs for the thread and requested memory type.
3. For each source ref, call the shared C11 resolver for the current overlay state of that target/field path.
4. Load current C5/C6/C7/C9/C15 source data through the resolver result, **not** from C8 payload.
5. If a pointer projection is stale (by `source_version_hash`, `graph.edge_scored`, `evidence.corrected`, `c11.correction.applied`, `thread.state_changed`, or C9 pending-item version), refresh synchronously for small reads or return `projection_stale` with a rebuild event for large reads.
6. For AI summaries: assemble source-linked candidate text, pass C10, store `c10_gate_id` + output hash, return through C13 with `SourceRefV2`.

### Event / invalidation model (report)

C8 consumes or is invalidated by: `evidence.linked`, `evidence.corrected`, `c11.correction.applied` (+ compatibility alias `correction.applied` if existing C6 workers consume that name), `graph.edge_scored`, `thread.state_changed`, `c9.pending_item.created/updated/resolved/cancelled`, and C15 theory-evaluation events indicating a post-C10 summary is available. C8 emits C12 audit on memory creation, controller acceptance, projection rebuild/invalidation, and rendered memory reads (routine internal refreshes may be audit-only; user-facing renders carry access/render audit context).

### Edge-case decisions (report)

- **Pattern edge rescored near zero:** keep the entry for audit/history, set read state to `not_current`/`projection_stale`, do not present as an active pattern unless current score crosses threshold; if shown in history, label as previously surfaced and source-linked.
- **Imported diagnosis in Clinical Memory:** render only as a sourced record ("Record from [source] lists [term]"), never as WellBe asserting the condition.
- **Entry whose only link is a C11 correction:** allowed if the correction itself has C2/C5 provenance (chain: C8 entry → C5 link with `correction_id` → C11 correction → C2 raw correction event + target refs).
- **Story free text:** user statement is evidence; store raw words in C2 and link the Story entry via C5; tags/summaries are derived and separately linked/gated.
- **Divergence detection:** compute `source_version_hash` from source IDs, source/status versions, active C11 correction IDs, and C6 edge-score versions; on mismatch, recompute display values rather than read from C8 payload.

### Test / acceptance criteria (report)

Inserting a visible entry without a C5 evidence link is rejected (app gate + deferred DB trigger); a lab-value correction changes the Clinical read without touching the C4 fact/C6 node/C8 row; a Pattern entry below threshold is no longer current but stays in audit/history; imported diagnosis renders as a sourced mention; Story entries link to C2 raw words without requiring a clinician-sourced record; Responsibility reads pull current status from C9; derived Equity suggestions stay pending until controller confirmation; C13 rejects derived memory claims missing `SourceRefV2`; AI summaries cannot return without a C10 render token bound to the output hash; drift tests prove C8 recomputes or marks `projection_stale` before user-facing output.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
