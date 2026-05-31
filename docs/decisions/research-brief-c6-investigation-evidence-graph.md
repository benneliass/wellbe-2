# Research Brief — C6 Knowledge Graph retrofit for the Health Investigation OS

**Prepared for:** external research consultant
**Prepared:** 2026-05-31
**Owner:** Ben Elias (data controller / product owner)
**Status:** Open — awaiting external research
**Jira:** WEL-135 (retrofit story), blocked by Spikes WEL-130, WEL-128, WEL-129
**Decision records to be filled from your output:**
- `docs/decisions/external-evidence-graph-separation.md` (WEL-130)
- `docs/decisions/investigation-object-and-thread-coupling.md` (WEL-128)
- `docs/decisions/theory-object-evaluation-and-safety.md` (WEL-129)

---

## 0. How to use this brief

This document is self-contained. You do **not** need access to the codebase to answer it. It gives you:

- **Part A–B** — what WellBe is, its safety posture, and the architecture (enough context to reason safely).
- **Part C** — the **as-built** C6 Knowledge Graph (ground truth — this is what already runs in production-shaped code).
- **Part D** — the **target design** the new vision wants C6 to reach.
- **Part E** — the divergence between C (built) and D (designed) you must help reconcile.
- **Part F** — the **three concrete research questions** that are the actual deliverable.
- **Part G** — the non-negotiable safety constraints any answer must respect.
- **Part H** — the exact output format we need back.

> **What we need from you:** evidence-grounded options + a recommended approach for each of the three questions in Part F, respecting the constraints in Part G, returned in the format of Part H. Cite your sources. We will record your output verbatim and our team will make the final decision.

---

## Part A — What WellBe is (system context)

WellBe is a **Patient-Centered Health Investigation OS**. Its sovereign core is a **Personal Shared Health Memory** — a user-controlled memory layer that carries a person's health context forward until each concern is **resolved, explained, monitored, or safely handed off**.

**The operating loop (six steps):**
`Capture → Connect → Investigate → Clarify → Close → Correct`

- **Capture** — ingest raw health context (documents, labs, messages, device data, notes).
- **Connect** — link entities across time, source, and domain into a knowledge graph.
- **Investigate** — *(new step)* run a structured research process around an unresolved concern.
- **Clarify** — surface uncertainty, missing data, contradictions — never a diagnosis.
- **Close** — track open loops (results, referrals, follow-ups) to closure.
- **Correct** — let the user repair the memory; corrections are additive, never destructive.

**Central object — the Health Thread:** one unresolved or ongoing concern, with its story, timeline, data, uncertainty, pending items, corrections, and shareable summaries.

**Non-negotiable identity facts (these are "bible" rules — they cannot be relaxed by any technical decision):**
1. **The individual is always the data controller.** Clinicians, institutions, and researchers are *users of workspaces* under explicit, scoped, time-boxed, revocable grants — never controllers of the person's data.
2. **Investigate, never diagnose.** The system never asserts a diagnosis, a ranked differential, or a disease claim. The strongest causal language permitted anywhere in the graph is **`may_explain`**.
3. **External medical knowledge is context, never fact about the user.** Papers, guidelines, and explainers may be *referenced* but never *imported* as facts about the individual.
4. **No orphan claims.** Every derived fact about the user must trace back to a raw source event (provenance).
5. **Safety gate before output.** Every user-facing AI output passes a mandatory Safety & Governance Gate (do-not-diagnose lexicon, panic-language, provenance-present, bias) before it reaches a human.

---

## Part B — Architecture (the parts you need to know)

WellBe is a Python monorepo of layered "core components" (C1–C17). Components C1–C6 are **already built and Done**; C14–C17 are **new** (this vision's expansion).

| # | Component | Status | Role (one line) |
|---|---|---|---|
| C1 | Trust & Consent Service | **Done** | Auth identity, consent scopes, share grants, revocation, cross-patient opt-in gate. |
| C2 | Raw Context Vault | **Done** | Immutable append-only store of every raw input with provenance. Personal data only. |
| C3 | Ingestion Layer | **Done** | Source adapters that write into the Vault. |
| C4 | Processing Pipeline | **Done** | Extracts entities/facts/signals; quality/confidence scoring. |
| C5 | Evidence & Provenance Service | **Done** | Links every derived fact to its raw source; enforces "no orphan claims". |
| **C6** | **Knowledge Graph Store** | **Done** | **Typed nodes + evidence-weighted edges across threads/time/sources. ← the focus of this brief.** |
| C7 | Health Thread Engine + State Machine | In flight | The central thread object: lifecycle, linking, status. |
| C8 | Six Memories Store | Planned | Story / Clinical / Pattern / Decision / Responsibility / Equity memories. |
| C10 | Safety & Governance Gate | Planned | Mandatory pre-output safety gate. |
| **C14** | **Investigation Engine** | **New** | Owns the **Investigation** object (the "Investigate" loop step). |
| **C15** | **Theory Service** | **New** | Owns the **Theory** object (safe hypothesis evaluation; never diagnosis). |
| **C16** | **External Evidence Graph + Research Watch** | **New** | **Separate** graph of external sources with quality tiers; relevance-links to personal facts. |
| C17 | Workspace, Role & Grant Layer | New | Role-specific workspaces + deep grant model; individual stays controller. |

The retrofit in question (**WEL-135**) extends the already-built **C6** to host the new `Investigation` and `Theory` node types and the new edges, and to enforce the **separation** of the external evidence graph (C16) from the personal graph.

---

## Part C — The C6 Knowledge Graph **as built** (ground truth)

This is what actually runs today (Postgres + optional Apache AGE). Your recommendations must be implementable as an **additive migration** on top of this — existing rows and the existing personal-data path must be preserved.

### C.1 Storage model
- Authoritative storage is **relational**: `graph.kg_nodes` and `graph.kg_edges` tables in a dedicated `graph` schema. Apache AGE (`create_graph('wellbe')`) is loaded *optionally* for Cypher traversal/visualization, but the relational tables are the source of truth for hot-path queries.
- **Row-Level Security** isolates tenants: every node/edge carries `patient_id`, and RLS policies (`patient_isolation_nodes`, `patient_isolation_edges`) restrict rows to `current_setting('app.patient_id')`.
- A dedicated DB role `wellbe_graph` has read access to `evidence.evidence_links` and `processing.extracted_facts`, and write access to the `graph` schema only.

### C.2 `graph.kg_nodes` (as built)
Columns: `id (uuid pk)`, `patient_id`, `node_type`, `normalized_key`, `display_label`, `status`, `thread_ids (uuid[])`, `embedding_id`, `metadata (jsonb)`, `first_seen_at`, `last_seen_at`, `schema_version`, `created_at`, `updated_at`.

CHECK constraints:
```
node_type IN ('ConditionHypothesis','Symptom','Medication','LabResult','Procedure',
              'VitalSign','Allergy','Immunization','SocialFactor','FamilyHistory','Other')
status    IN ('active','resolved','superseded','merged')
```
Unique index on `(patient_id, normalized_key)`. Index on `(patient_id, node_type)`.

### C.3 `graph.kg_edges` (as built)
Columns: `id`, `from_node_id (fk kg_nodes)`, `to_node_id (fk kg_nodes)`, `edge_type (fk edge_types.code)`, `potential_score (float 0–1)`, `score_version`, `score_inputs (jsonb)`, `needs_rescore (bool)`, `thread_ids (uuid[])`, `patient_id`, `schema_version`, timestamps.

CHECK: `potential_score BETWEEN 0 AND 1`; `from_node_id != to_node_id` (no self-edges).

### C.4 `graph.edge_types` (as built — the controlled vocabulary)
A lookup table with `code`, `display_name`, `category`, where `category IN ('causal','correlation','temporal','therapeutic','adverse','contradiction','refinement')`. Seeded edge codes:

| code | category |
|---|---|
| `may_explain` | causal *(strongest allowed — the safety ceiling)* |
| `associated_with` | correlation |
| `co_occurs_with` | correlation |
| `temporal_sequence` | temporal |
| `treats` | therapeutic |
| `alleviates` | therapeutic |
| `worsens` | adverse |
| `contradicts` | contradiction |
| `refines` | refinement |
| `supersedes` | refinement |

### C.5 Edge scoring as built (`PotentialScoreComputer`, version 1)
- `potential_score ∈ [0,1]` is an **internal quality/provenance metric**, explicitly **not** a diagnostic confidence.
- Inputs come from C5 evidence links typed `PRIMARY (1.0) / CORROBORATING (0.6) / CONTRADICTING (-0.4) / CONTEXTUAL (0.2)`, each multiplied by a `confidence`.
- Algorithm: weighted sum / max-possible, minus a `0.3` contradiction penalty if any contradicting evidence is present, clamped to `[0,1]`.
- A background auto-linking worker recomputes edges flagged `needs_rescore`.

---

## Part D — The **target design** (what the new vision wants C6 to reach)

From the design spec (`docs/system-design/knowledge_graph.md`, `core_objects.md`). Note these use a richer, lower-case vocabulary that **diverges** from the built code (see Part E).

### D.1 New node types to add
- `investigation` — a structured research process node.
- `theory` — a safe hypothesis node (never a diagnosis).

### D.2 New edge types to add
| edge type | meaning |
|---|---|
| `evidence_for` | a fact or source supports a `theory` |
| `evidence_against` | a fact or source weakens a `theory` |
| `investigates` | an `investigation` is examining an entity or thread |
| `relevance_link` | a **personal** fact relates to an **External Evidence Graph** claim — *context only*, never importing the external claim |

### D.3 The External Evidence Graph (C16) — must be **separate**
External medical knowledge lives in a **separate graph**, never blended into the personal graph. It holds `external_evidence_source` nodes (guidelines, papers, case reports, explainers, anecdotes), each with a **source-quality tier**:

| Tier | Source type | Permitted use |
|---|---|---|
| Tier 1 | Clinical guidelines, official bodies | Strongest external reference |
| Tier 2 | Peer-reviewed papers, systematic reviews | Useful, still contextual |
| Tier 3 | Case reports, early research | Signal only; not general proof |
| Tier 4 | Medical blogs, expert explainers | Educational context only |
| Tier 5 | Forums, anecdotes, social posts | Anecdotal; never evidence about the user |

Personal facts connect to external sources **only** through `relevance_link` edges. An external claim is never asserted as a fact about the user, and never enters the personal subgraph.

### D.4 The Investigation object (C14) — fields (design)
`id`, `owner_type (individual|clinician|shared|institution|research)`, `linked_health_thread_ids[]`, `primary_question`, `status (open|monitoring|waiting_for_data|ready_for_visit|handed_off|closed)`, `scope (flags)`, `participants[] (each under a Grant)`, `evidence_bundle_ids[]`, `active_theory_ids[]`, `missing_context_items[]`, `pending_item_ids[]`, `safety_flags[]`, `last_reviewed_at`, `next_review_due_at`, `outputs`. A thread may carry **many** investigations.

### D.5 The Theory object (C15) — fields (design)
`id`, `created_by (individual|clinician|system_suggested_question)`, `linked_investigation_id`, `theory_text`, `theory_type (symptom_trigger|medication_effect|lifestyle_factor|environmental_factor|clinical_condition_question|care_process_gap)`, `evidence_for[]`, `evidence_against[]`, `missing_data[]`, `external_source_ids[]`, `status (unreviewed|needs_more_data|partially_supported|not_supported_by_current_data|contradicted_by_current_data|discuss_with_clinician|clinician_reviewed)`, `safety_level (low|needs_clinician_context|urgent_symptom_present|blocked_due_to_diagnostic_claim)`.

---

## Part E — The divergence you must help reconcile

The **as-built C6** (Part C) and the **target design** (Part D) do **not** currently agree. Any recommendation must explicitly resolve these:

1. **Node-type naming/scheme.** Built = PascalCase clinical enum (`Symptom`, `LabResult`, …). Design = lower-case richer taxonomy (`symptom`, `investigation`, `theory`, …). Adding `investigation`/`theory` means altering the `ck_node_type` CHECK constraint — but the consultant should advise whether to (a) extend the existing enum in place, (b) migrate to a reference table like `edge_types`, or (c) split process/meta nodes (`investigation`, `theory`) from clinical-entity nodes entirely.
2. **Edge vocabulary.** Built `edge_types` categories are `causal/correlation/temporal/therapeutic/adverse/contradiction/refinement`. The new `evidence_for/against`, `investigates`, `relevance_link` edges don't map cleanly to those categories — a new category (e.g. `evidential`, `process`, `external`) is likely required.
3. **External graph separation mechanism.** Built graph is single-tenant-per-patient via RLS, all nodes carry `patient_id`. External evidence is *not* patient-owned. So the external graph cannot live in the same RLS-scoped tables without violating the model. The consultant must recommend the separation mechanism (separate schema? separate database? an `is_external`/`scope` partition with different RLS? a distinct AGE graph?).
4. **`relevance_link` crossing the boundary.** A `relevance_link` connects a `patient_id`-scoped personal node to a non-patient external node. Today `kg_edges` requires both endpoints in `kg_nodes` and enforces `patient_id`. The consultant must specify how a cross-boundary edge is represented without (a) breaking RLS, (b) importing the external claim, or (c) letting external content count as personal evidence.

---

## Part F — The three research questions (the deliverable)

These are reproduced verbatim from the open decision records. **Your output should answer each, with options + a recommendation.**

### F.1 — External Evidence Graph separation & relevance-link semantics (WEL-130)
> How should the External Evidence Graph (C16) be separated from the personal Knowledge Graph (C6) and Evidence & Provenance Service (C5), and how are relevance links scored and constrained so external claims never become facts about the user?
> 1. Physical/logical separation: separate store, separate schema in the same store, or namespaced subgraph — and how is cross-contamination structurally prevented?
> 2. How is `source_quality_tier` (Tier 1–5) assigned, stored, and surfaced, and can it ever be upgraded by usage?
> 3. How is a `relevance_link` scored (confidence) and what prevents an external claim from being asserted as a personal fact?
> 4. How does C5 provenance treat external sources differently from personal sources (so external claims are never counted as evidence about the user)?

### F.2 — Investigation object model & coupling to the thread state machine (WEL-128)
> How should the Investigation object (C14) be modeled and persisted relative to the Health Thread (C7), and how do Investigation status transitions couple to Health Thread state transitions?
> 1. Is an Investigation a separate aggregate with its own lifecycle (open / monitoring / waiting_for_data / ready_for_visit / handed_off / closed) and a many-to-one link to threads, or a sub-state embedded in the thread?
> 2. Which component owns the rule that an Investigation may not `close` unless its linked thread(s) meet closure criteria — C14, C7, or a shared policy?
> 3. How do investigation-level safety flags propagate to thread state (e.g. force `escalated`)?
> 4. What is the event contract between C14 and C7 (does C14 consume `thread.state_changed`, emit `investigation.state_changed`, or both)?

### F.3 — Theory evaluation model & non-diagnostic safety routing (WEL-129)
> How should the Theory object (C15) be evaluated against personal data and external evidence to produce evidence-for / evidence-against / missing-data and a status — without ever crossing into diagnosis — and how does that output route through the Safety & Governance Gate (C10)?
> 1. What is the authoritative theory status taxonomy and what transitions are permitted?
> 2. Where is a Theory stored relative to Six Memories (C8) — a Pattern Memory entry, a first-class object, or both?
> 3. What C10 rules block a theory output from asserting a diagnosis or a ranked differential, and what triggers `discuss_with_clinician` / urgent routing?
> 4. How are external sources (C16) attached as evidence without importing their claims as facts about the user?

---

## Part G — Hard constraints any answer must respect

These are non-negotiable (from WellBe's safety/identity bible). An option that violates any of these is out of scope:

- **G1 — Never diagnose.** No node, edge, status, or output may assert a diagnosis, a ranked differential, or a disease claim. `may_explain` is the strongest causal edge; `causes`, `diagnoses`, `confirms_diagnosis`, `rules_out`, `proves` are prohibited at schema, service, and test layers.
- **G2 — External = context, never fact.** External-evidence content may never be written as a fact about the user, never counted as personal evidence in C5, and never blended into the personal graph. The only personal↔external connection is a `relevance_link`.
- **G3 — No orphan claims.** Every personal derived fact still traces to a raw source. The retrofit must not weaken this for the existing personal path.
- **G4 — Closure safety.** Thread/investigation closure rules (e.g. no closure on a single normal test, an unresolved symptom stays visible) must not be bypassable through the Investigation or Theory objects.
- **G5 — Additive, non-destructive.** The migration must add types/edges/structures without dropping or mutating existing `kg_nodes`/`kg_edges` rows; existing C6 tests must continue to pass unchanged.
- **G6 — Tenant isolation preserved.** RLS by `patient_id` on personal data must remain intact; the external graph must not be reachable through personal RLS scope as if it were personal data.
- **G7 — Individual is controller.** Any participant/owner concept (e.g. clinician-owned investigation) exists only under an explicit, scoped, revocable grant; default state grants no external party access.

---

## Part H — Output format we need back

For **each** of the three questions (F.1, F.2, F.3), please return:

1. **Approaches considered** — 2–4 concrete, named options, each with: how it works, pros, cons, and the evidence/precedent it's based on (cite sources: papers, standards like FHIR/SNOMED/openEHR, graph-DB patterns, clinical-informatics literature, comparable systems).
2. **Recommended approach** — one clear pick, with the reasoning, and how it satisfies the constraints in Part G (call them out by ID, e.g. "satisfies G2 because…").
3. **Trade-offs accepted** — what we give up by choosing it.
4. **Implementation notes** — concrete enough to turn into a schema migration and service contract (table/column/constraint shape, edge representation, event names, where enforcement lives).
5. **Open risks / what could go wrong** — especially any safety risk relative to G1–G2.

We will paste your output verbatim into the three decision records, write a proposed decision, and our team will approve before implementation. **Please cite every source** — recommendations not grounded in a citable source can't be used to close the decision.

---

## References (internal — for our team, not required for you)

- Identity & loop: `docs/system-design/platform_identity.md`, `docs/system-overview.md`
- Graph design (target): `docs/system-design/knowledge_graph.md`
- Object specs: `docs/system-design/core_objects.md`
- Component map: `docs/architecture/component-map.md`
- Safety: `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`
- As-built C6: `backend/packages/c6_graph/`, `db/migrations/versions/006_c6_graph_schema.py`
- Decision records to fill: `external-evidence-graph-separation.md`, `investigation-object-and-thread-coupling.md`, `theory-object-evaluation-and-safety.md`
