# Decision: Correction Service layered, source-linked, non-mutating overlay model

**Status:** Approved
**Date opened:** 2026-06-01
**Research received:** 2026-06-01
**Date approved:** 2026-06-01
**Approved by:** User
**Jira Spike:** WEL-138
**Blocks:** WEL-71 — Build source-linked non-mutating Correction Service for facts and memories

---

## Question

How should the C11 Correction Service capture user corrections as layered, source-linked overlays written through C5 that never mutate the C2 Raw Context Vault or C4 extracted facts, and how do downstream reads (C6 / C8 / C13) resolve the corrected view deterministically?

Specifically:
1. What is the data model for a correction (overlay record, target reference, correction type, actor, timestamp)?
2. How does a correction attach to its target via C5 evidence links (the existing `evidence_links.correction_id` hook) without altering the target?
3. What is the deterministic read-resolution rule when a raw/derived value and one or more correction overlays disagree?
4. How are corrections audited (C12) and how do they interact with C7 reopen/relabel transitions?

## Context

Affected core component: Correction Service (C11), writing through Evidence & Provenance (C5), constrained by Raw Context Vault immutability (C2) and no-orphan-provenance (C5). The approved `raw-context-vault-immutability-enforcement.md` and `evidence-provenance-no-orphan-enforcement.md` decisions forbid mutating raw or derived data; migration 005 already added a nullable `evidence_links.correction_id` and `'correction_service'` provenance basis as a preparatory hook. If corrections are modeled as in-place edits or as un-provenanced overlays, we break immutability, lose the C12 audit trail, and create ambiguity about which layer wins on read. This is a trust-critical primitive and hard to retrofit once C13 exposes corrections.

## Research provided

_Source: provided research report `wellbe_c8_c9_c11_research_report_2026-06-01.docx` (GPT-5.5 Pro for WellBe review, dated 2026-06-01), section "C11 Correction Service — WEL-138 / WEL-71". Recorded as a faithful summary; external source labels [S1]–[S20] are the report's own cited-source register._

### Source findings the report relied on (C11)

- **Model correction as revision/derivation, not overwrite.** PROV-O provides `prov:wasRevisionOf` and qualified revision to describe a newer entity related to an earlier one [S1]; close to WellBe's overlay model, except WellBe keeps the old layer visible in audit and applies deterministic read resolution.
- **Provenance and audit have different jobs.** FHIR Provenance records how information came to be in its current state, while AuditEvent records events as they occur [S2, S7]; C11 needs both — provenance links for resolved data and C12 events for correction actions.
- **Provenance can target any resource/version.** FHIR Provenance supports target references and multiple provenance records per target [S2]; this supports multiple correction overlays targeting the same fact, memory entry, graph node, pending item, or thread label.
- **Bitemporal modeling clarifies correction time.** Bitemporal history separates the time a fact is true in the world from when the system recorded/learned it [S19]; C11 should capture both effective/valid-time and `created_at`/`applied_at` transaction time.
- **Materialized resolved views must be disposable.** Materialized-view precedent says the view is a specialized, rebuildable cache, not directly updated by application code [S18]; C11 resolved projections may exist for performance, but the correction log + C5 links are the source of truth.

### WellBe constraints the report says dominate the design (C11)

- C11 never mutates C2 raw events, C4 extracted facts, C5 evidence links, C6 graph rows, C8 memory entries, or C12 audit rows.
- C11 writes through C5 and uses the existing `evidence_links.correction_id` hook.
- Clinician/caregiver proposals under grants remain pending contributions until controller acceptance.
- Downstream C6, C8, and C13 reads must resolve the corrected view deterministically.
- A correction may request C7 `closed -> reopened` or relabel transitions, but only through `transition_thread`.

## Approaches considered

_Each approach is taken from the report's "Approaches considered" for C11 and grounded only in that report. Sub-question references: (1) correction data model; (2) attach via `evidence_links.correction_id` without altering the target; (3) deterministic read-resolution; (4) C12 audit + C7 reopen/relabel interaction._

### Approach 1 — In-place edits to facts/memories (sub-question 1)

Update the existing fact/memory/graph/pending-item row on correction. Precedent: standard CRUD. **Pros:** simple reads, easy UI model. **Cons:** violates C2/C4 immutability, C5 provenance, C12 audit, and the WellBe correction philosophy; erases what was previously believed and why; worsens clinical safety review and user trust. **Rejected** by the report.

### Approach 2 — Dedicated correction overlay table joined through C5 evidence links (sub-questions 1, 2, 3, 4) — recommended

Store correction records in `c11.corrections` + `c11.correction_targets`; create C5 evidence links with `correction_id` to attach the overlay to its raw correction event and target/source context. Precedent: PROV revision/derivation [S1], FHIR Provenance target/entity model [S2], event-sourced corrective events. **Pros:** preserves immutability; clear correction object + audit trail; uses the existing C5 hook; allows deterministic read resolution and supersession; works for raw-derived mismatches, missing context, stale data, and role proposals. **Cons:** every read path must use the resolver; more joins; needs strong idempotency + tests. The report rates this the best fit.

### Approach 3 — Fully bitemporal fact-version store (sub-questions 1, 3)

Convert facts/memory claims to bitemporal versions with valid-time and transaction-time ranges. Precedent: bitemporal data modeling [S19]. **Pros:** excellent historical queries ("what was believed on a date vs true for a date"). **Cons:** large retrofit; risks implying C4/C6 fact-version tables are mutable/current-state unless carefully append-only; more complex than needed for MVP overlays. The report's verdict: **use bitemporal fields inside C11 overlays, but do not retrofit the whole stack now.**

### Approach 4 — Resolve only at the C13 boundary (sub-question 3)

Store corrections in C11 but apply them only when API responses are composed at C13. Precedent: edge-layer presentation overlays. **Pros:** centralizes user-facing behavior; minimal C6/C8 change. **Cons:** C6 rescoring and C8 memory reads would still use uncorrected data; downstream services diverge; violates the requirement that corrections change what C8 reads and C6 scores. **Rejected as the sole mechanism** — C13 should enforce/expose resolved views, but the resolver must be **shared** with C6 and C8.

## Decision

**(Proposed — pending user approval.)** Implement C11 as an **append-only correction-overlay service in schema `c11`** (report Approach 2). A correction consists of a raw C2 correction event, a `c11.corrections` row, one or more `c11.correction_targets` rows, and C5 evidence links created through the C5 write gate with `correction_id` set, `linked_by = 'correction_service'`, and `confidence_basis = 'correction_service'`. **Corrections never update or delete their targets.** Only `applied` corrections participate in resolved reads; role-authored proposals stay `pending_controller_acceptance` until accepted by the controller. The **deterministic resolution rule** is, in order: target specificity (more-specific `field_path` beats whole-object) → applied-only status → explicit supersession chain → authority rank → correction semantic rank → latest valid/effective time → latest applied transaction time → final lexicographic `correction_id` tie-break (ULID/UUIDv7 preferred). Provide **one shared resolver** (`c11.resolved_target_overlays_v` + application-service library) used by C6, C8, and C13; materialized resolved projections are allowed only as rebuildable caches. A correction may request C7 reopen/relabel only through `transition_thread`; it never patches thread state directly, and a C7 rejection does not roll back a valid data correction.

## Trade-offs accepted

- Every downstream read path must use the shared resolver — extra work, but it prevents three divergent corrected views.
- Correction status is separate from source truth; the original fact stays source-linked even when an applied overlay changes the resolved display.
- Controller authority is privileged: clinician/caregiver corrections are contributions until accepted, preserving personal-first controller identity at the cost of some workflow friction.
- Latest-wins is **not** the first rule; recency applies only after explicit supersession, authority, specificity, and semantic rank — avoiding arbitrary race outcomes.
- Materialized corrected views may be stale; they must be invalidated by correction events and rebuildable from C11 + C5.

## Implementation notes

_All schema/DDL, the resolution rule, worked examples, events, and tests below are the report's recommendation, recorded for the implementer._

### Correction data model (report DDL, reformatted)

```sql
CREATE SCHEMA IF NOT EXISTS c11;
CREATE TYPE c11.correction_type AS ENUM (
  'replace_value', 'mark_incorrect', 'add_missing_context', 'mark_stale',
  'withdraw_from_current_view', 'relabel_thread', 'merge_duplicate',
  'split_context', 'change_evidence_weight');
CREATE TYPE c11.correction_status AS ENUM (
  'draft', 'pending_controller_acceptance', 'applied', 'superseded', 'rejected', 'withdrawn');
CREATE TYPE c11.actor_authority AS ENUM (
  'controller', 'controller_accepted_proposal', 'delegated_controller',
  'role_proposed', 'system_suggested');
CREATE TABLE c11.corrections (
  correction_id uuid PRIMARY KEY,
  patient_id uuid NOT NULL,
  status c11.correction_status NOT NULL,
  correction_type c11.correction_type NOT NULL,
  actor_authority c11.actor_authority NOT NULL,
  actor_ref jsonb NOT NULL,
  grant_id uuid NULL,
  role_binding_id uuid NULL,
  raw_correction_event_id uuid NOT NULL,
  rationale text NULL,
  proposed_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  accepted_by_controller_actor jsonb NULL,
  accepted_at timestamptz NULL,
  applied_at timestamptz NULL,
  effective_at timestamptz NULL,
  valid_time_range tstzrange NULL,
  supersedes_correction_id uuid NULL REFERENCES c11.corrections(correction_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL UNIQUE,
  CHECK (jsonb_typeof(proposed_payload) = 'object'),
  CHECK (
    (status = 'pending_controller_acceptance' AND actor_authority IN ('role_proposed', 'system_suggested'))
    OR status <> 'pending_controller_acceptance'));
CREATE TABLE c11.correction_targets (
  correction_target_id uuid PRIMARY KEY,
  correction_id uuid NOT NULL REFERENCES c11.corrections(correction_id),
  target_kind text NOT NULL CHECK (target_kind IN (
    'c2_raw_event', 'c4_extracted_fact', 'c5_evidence_link',
    'c6_kg_node', 'c6_kg_edge', 'c7_thread_label',
    'c8_memory_entry', 'c9_pending_item', 'c14_investigation', 'c15_theory')),
  target_id uuid NOT NULL,
  target_version text NULL,
  field_path text NULL,
  base_value_hash text NULL,
  proposed_value_hash text NULL,
  semantic_rank smallint NOT NULL DEFAULT 50,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (correction_id, target_kind, target_id, coalesce(field_path, '')));
CREATE TABLE c11.correction_resolution_events (
  resolution_event_id uuid PRIMARY KEY,
  correction_id uuid NOT NULL REFERENCES c11.corrections(correction_id),
  target_kind text NOT NULL,
  target_id uuid NOT NULL,
  field_path text NULL,
  resolution_action text NOT NULL CHECK (resolution_action IN (
    'became_active', 'superseded_prior', 'lost_precedence', 'removed_from_current_view',
    'rejected_pending', 'withdrawn_by_controller')),
  prior_active_correction_id uuid NULL,
  new_active_correction_id uuid NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL UNIQUE);
```

### C5 attachment protocol (report)

**Controller-authored:** capture the correction request/user text as a new raw C2 event (preserves the user's words as evidence) → insert `c11.corrections` + `c11.correction_targets` in an append-only transaction → call the C5 write gate to create evidence links for the correction object (primary link to the C2 raw correction event; contextual links to the target's existing evidence links/graph nodes; contradicting links when the correction says an existing value is wrong; all correction-created links set `correction_id`, `linked_by = 'correction_service'`, `confidence_basis = 'correction_service'`) → emit C5 `evidence.corrected` where applicable → emit C11/C12 correction events and trigger C6 rescore via `c11.correction.applied` (+ compatibility `correction.applied` if existing worker contracts require it).

**Clinician/caregiver proposal:** create the raw proposal event + C11 rows with `status = 'pending_controller_acceptance'`; create provenance links but exclude from the resolved view; on controller acceptance append an acceptance event, set a new applied correction row (or transition the proposal row to `applied` via an append-only status-event pattern), and emit the same applied events. Restrict any in-C11 status updates to C11 correction-lifecycle rows only — never update targets.

### Deterministic read-resolution rule (report)

For a given `(patient_id, target_kind, target_id, field_path)`:

1. Start with the base target as originally sourced through C5/C6/C8/C9; do not alter it.
2. Gather all `c11.correction_targets` matching the target. A more-specific `field_path` wins over a whole-object correction for that field; whole-object corrections still apply to fields without a more-specific correction.
3. Exclude corrections not in `status = 'applied'`.
4. Collapse explicit supersession chains (if B supersedes A, A is inactive for the overlapping target/field/effective range).
5. Authority rank: 100 controller-authored; 90 controller-accepted proposal; 80 delegated controller within grant; 20 role-proposed annotation (only in a non-resolved annotation view, if ever allowed); 10 system-suggested. The resolved user-facing view includes rank ≥80 unless product policy narrows it.
6. Semantic rank for conflicting types on the same field: `withdraw_from_current_view`/`mark_incorrect` outrank `replace_value`; `replace_value` outranks `add_missing_context`; `mark_stale` affects currency/display without necessarily replacing value; `add_missing_context` is additive unless it directly conflicts with a replacement.
7. Valid/effective time: most recent `effective_at` / valid-time lower bound wins when specificity, status, authority, and semantic rank are equal.
8. Transaction time: later `applied_at` wins when valid/effective time is equal or absent.
9. Final tie-break: lexical order of `correction_id` (use ULID/UUIDv7 so the tie-break is stable and roughly time-ordered; never rely on wall-clock alone).

Return both base and overlay metadata: `resolved_value`, `resolved_state`, `active_correction_id`, inactive correction IDs, provenance refs, and a resolution explanation code.

### Worked examples (report)

- **Two user corrections to the same value:** A replaces a med dose; B later supersedes A and replaces the same field → B active (explicit supersession beats recency); A inactive but auditable.
- **Clinician proposal vs controller correction:** proposal stays `pending_controller_acceptance`, excluded from resolved view; on acceptance it becomes `controller_accepted_proposal` and participates.
- **Correction to a derived multi-source fact:** target is the derived fact field, with contextual links to all source evidence links; resolver overlays the derived display value while C6 rescoring can reduce/reverse edge weight via the contradicting correction link.
- **Missing data:** stored as `add_missing_context`, linked to the raw correction event, exposed as an additive overlay rather than pretending it was in the original record.
- **Stale data:** `mark_stale` changes current display state while preserving the original entry + provenance.
- **Reopen a thread:** C11 applies the correction, emits `c11.correction.applied`, and calls C7 `transition_thread(closed -> reopened, ...)` with correction evidence refs + idempotency key; if C7 rejects (stale version/invalid context), C11 records the rejection and keeps the data correction applied — thread state stays C7-owned.

### Resolved view sketch (report)

```sql
CREATE VIEW c11.applied_correction_candidates_v AS
SELECT
  c.patient_id, ct.target_kind, ct.target_id, ct.field_path,
  c.correction_id, c.correction_type, c.actor_authority,
  CASE c.actor_authority
    WHEN 'controller' THEN 100
    WHEN 'controller_accepted_proposal' THEN 90
    WHEN 'delegated_controller' THEN 80
    WHEN 'role_proposed' THEN 20
    WHEN 'system_suggested' THEN 10
  END AS authority_rank,
  ct.semantic_rank, c.effective_at, lower(c.valid_time_range) AS valid_from,
  c.applied_at, c.supersedes_correction_id, c.proposed_payload
FROM c11.corrections c
JOIN c11.correction_targets ct ON ct.correction_id = c.correction_id
WHERE c.status = 'applied';
```

The final `resolved_target_overlays_v` should use a deterministic ordering expression and a recursive CTE (or materialized supersession table) to remove superseded corrections. If performance requires materialization, use a rebuildable projection table with `source_correction_version`, invalidated on every C11 `applied`/`superseded`/`withdrawn` event.

### Audit and event model (report)

C11 emits PHI-minimized C12 events with required authority/grant fields: `c11.correction.requested`, `.proposed`, `.accepted`, `.applied`, `.superseded`, `.rejected`, `.withdrawn`, `.resolution_changed`. C5 continues to emit `evidence.corrected` when an evidence relationship is affected. C6 scoring workers consume `c11.correction.applied` (or the existing compatibility `correction.applied` if already wired). C8 invalidates/re-resolves memory reads on the same applied event.

### C7 reopen/relabel integration (report)

Request C7 transitions only when the correction changes thread-lifecycle semantics (adds persistent symptoms to a closed thread; says the label/main concern was wrong; invalidates the basis for closure; links a pending result/referral missing from the closed thread). Protocol: apply the data correction through C11/C5 → build the C7 request with evidence refs to the correction + source chain → use `expected_version` from the latest C7 thread row read by the C11 activity/service → idempotency key `c11:correction:{correction_id}:transition:{target_status}` → C7 accepts/rejects; C11 records the outcome and never patches `health_threads.status`.

### Test / acceptance criteria (report)

A correction request creates a C2 raw event, C11 rows, C5 links with `correction_id`, and C12 audit events with no update to any raw/C4 row; DB roles/triggers reject C11 attempts to update/delete C2 raw or C4 facts; a visible corrected C13 response includes both the active-correction source and the original source refs (no orphan claims); two corrections on the same fact resolve deterministically including explicit supersession; a clinician proposal does not alter the resolved view until acceptance; a missing-data correction is additive and does not rewrite the original; a stale correction changes display state while preserving history/provenance; `evidence.corrected` and `c11.correction.applied` redelivery are idempotent by correction/event ID; C6 rescore is triggered by applied corrections and replayable without duplicate edges; C8 reads change after a correction without mutating C8 rows; a reopen correction calls `transition_thread` and direct status updates are proven impossible; resolver property tests generate random correction sets and prove stable output regardless of input order.

---

## Cross-component integration notes (from the report's shared sections)

These notes apply to all three records (recorded here because C11's resolver is the shared seam):

- **Shared read-resolution contract:** C11's resolver is a small, versioned service/library used by C6, C8, and C13, returning `{target_ref, base_state, resolved_state, active_correction_id, inactive_correction_ids, resolution_rule_version, source_refs (SourceRefV2...), explanation_code}`. C8 never implements its own correction precedence; C6 uses the resolver before scoring; C13 uses the same resolver before emitting DTOs.
- **C8/C9 seam:** Responsibility Memory is a C8 surface over C9 pending items — C8 stores the entry + pointer; C9 stays authoritative for status/due/owner/timer; C9 events invalidate Responsibility Memory projections.
- **C9/C7 seam:** C9 is a process manager for durable time, not a lifecycle owner; a C7 stale/guard rejection is success from C9's view.
- **C11/C7 seam:** data overlay and lifecycle transition are separately auditable so a C7 rejection does not roll back a valid data correction.
- **C10/C13 seam:** any generated memory summary, pending-item narrative, correction explanation, or pattern/theory summary passes C10 before C13 returns it; non-AI raw DTOs still require C1/C17 access predicate + C12 audit.
- **Sequencing recommendation:** build the C11 resolver + overlay write path first (defines the read-time semantics C8 and C6 share); build the C8 base store + pointer model second; deploy Temporal in Helm/kind before safety-bearing C9 timers.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
