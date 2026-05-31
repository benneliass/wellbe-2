# Decision: Investigation object model and coupling to the Health Thread state machine

**Status:** Proposed — awaiting user approval  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-128  
**Blocks:** WEL-112 (Investigation object, C14); relates to WEL-64 (C7 build-forward)

---

## Question

How should the **Investigation** object (the new "Investigate" loop step, C14) be modeled and persisted relative to the Health Thread (C7), and how do Investigation status transitions couple to Health Thread state transitions?

Specifically:
1. Is an Investigation a separate aggregate with its own lifecycle (open / monitoring / waiting_for_data / ready_for_visit / handed_off / closed) and a many-to-one link to threads, or a sub-state embedded in the thread?
2. Which component owns the rule that an Investigation may not `close` unless its linked thread(s) meet closure criteria — C14, C7, or a shared policy?
3. How do investigation-level safety flags propagate to thread state (e.g. force `escalated`)?
4. What is the event contract between C14 and C7 (does C14 consume `thread.state_changed`, emit `investigation.state_changed`, or both)?

## Context

C7 is already in flight (WEL-64) and is the central L3 object every higher component depends on. The expanded vision adds C14 Investigation as the engine of the "Investigate" loop step. Coupling these two state machines incorrectly is expensive: the thread closure-safety rules (no closure on a single normal test, no final diagnosis) must not be bypassable through an investigation, and the event schema between C14 and C7 becomes a stable contract consumed by C8, C9, C10, and C13. Because WEL-64 is in flight, the build-forward strategy depends on this decision.

## Research provided

_Research received: 2026-05-31_ — external consultant report, archived verbatim at [research-inputs/wellbe_c6_kg_retrofit_report.md](research-inputs/wellbe_c6_kg_retrofit_report.md). Section 3 addresses this decision. Source basis: HL7 FHIR Task and CarePlan (independent workflow resources with own state/owner) [S13, S14]; FHIR Provenance / DetectedIssue [S1, S15]; domain-event / aggregate patterns (Microsoft, microservices.io, Fowler) [S16, S17, S18].

## Approaches considered

_Based only on the provided research (report §3.2)._

1. **Embed Investigation as a sub-state inside the Health Thread.** Simple single-aggregate join path. Cons: the vision allows many investigations per thread (and one investigation spanning threads); embedding a lifecycle-heavy object entangles C7 thread state with C14 workflow state and makes safety invariants hard to test independently. FHIR Task/CarePlan precedent favors separate workflow objects [S13, S14].
2. **Separate Investigation aggregate (C14) with a thread join table + C6 graph projection (recommended).** Clean lifecycle boundaries; supports many-to-many investigation↔thread; lets C14 evolve without changing C7's schema; C6 answers graph questions without owning lifecycle. Cons: requires cross-aggregate policy + events and careful closure/safety propagation; more schema/test surface. Grounded in domain-event patterns [S16, S17, S18] and FHIR Task workflow-status model [S13].
3. **Pure C6 graph node, no separate C14 table.** Minimal relational change, easy graph queries. Cons: C6 is not a workflow/lifecycle/grant/closure-policy owner; JSON metadata is a poor home for lifecycle invariants; risks graph traversal mutating business state (architectural inversion). FHIR represents workflow state explicitly, not in graph metadata [S13, S14].
4. **Delegate to a generic workflow engine.** Strong timers/retries/audit for waiting states and reviews. Cons: overkill for WEL-135, obscures health-specific safety rules (closure safety, grants, non-diagnostic outputs still need product policy), adds operational dependency. A workflow engine is a plausible later detail, not needed for the first additive retrofit [S13].

## Decision

_Proposed (report §3.3, §6.2):_ Model **Investigation as a first-class C14 aggregate** with its own lifecycle (`open / monitoring / waiting_for_data / ready_for_visit / handed_off / closed`), **many-to-many** links to C7 Health Threads via a join table, participant grants, structured safety flags, and a **C6 `Investigation` projection node** (+ optional `investigates` edges to personal entity nodes). **C7 remains authoritative** for thread lifecycle and closure criteria; **C14 owns** investigation status. A shared `InvestigationThreadCouplingPolicy` plus a bidirectional event contract enforces that **C14 cannot close an investigation unless linked threads meet C7 closure criteria**, and that investigation safety flags propagate to C7 escalation via events (C14 requests, C7 decides). Thread coupling is **not** represented as a graph edge until/unless C7 introduces a first-class `HealthThread` node type (no fake thread nodes in WEL-135).

Satisfies the hard constraints: **G1** (statuses are workflow state, never `diagnosed`/`ruled_out`/`confirmed`), **G2** (external context only via C16 relevance links / C15 theory context), **G3** (derived facts in outputs still point to C5 provenance), **G4** (C14 closure gated by C7 snapshot; work-done-but-thread-unresolved uses `handed_off`/`monitoring`/`waiting_for_data`), **G5** (additive), **G6** (investigation rows + projection nodes RLS-scoped by `patient_id`), **G7** (participants exist only under C1/C17 grants; FHIR Consent computable-rule precedent [S3]).

## Trade-offs accepted

- Eventual consistency between C14 and C7 (events/commands, not one giant transaction).
- More policy code (shared coupling policy to prevent divergent closure logic).
- Graph is a projection, not source of truth (some queries join C14 for authoritative status).
- Thread-as-node deferred — current C6 uses `thread_ids` arrays, not first-class HealthThread nodes.

## Implementation notes

_From report §3.5 (verbatim DDL in the archived report)._

- **Tables (schema `c14`):** `investigations` (patient_id, owner_type, owner_grant_id, primary_question, status CHECK, scope jsonb, evidence_bundle_ids[], active_theory_ids[], missing_context_items, pending_item_ids[], safety_flags jsonb, last/next_review, outputs, status_reason, created_by/grant); `investigation_threads` (PK investigation_id+thread_id, relationship primary/secondary/related); `investigation_participants` (actor_id, role, grant_id, status active/revoked/expired). RLS on all via `app.patient_id`.
- **C6 projection:** on create, write a `kg_nodes` row `node_type='Investigation'`, `normalized_key='investigation:'||id`, status active→resolved on close, `thread_ids` = linked threads, metadata = investigation_status/owner_type/safety_flag_count/last_reviewed_at (no participant secrets, no external claim text); add `investigates` edges from the Investigation node to personal entity nodes.
- **Closure rule:** `CloseInvestigationCommand` → C14 loads linked threads → asks C7 for `ThreadClosureSnapshot[]` → `InvestigationThreadCouplingPolicy.evaluate_close(...)` → deny w/ unmet criteria, or set `closed` + emit `investigation.closed.v1`. C14 never computes symptom-resolution / single-normal-test sufficiency — that is C7's.
- **Status transitions:** matrix per §3.5.4 (e.g. `handed_off → {monitoring, closed}`; `closed → open` only via explicit additive reopen; closure only when thread policy permits).
- **Safety-flag propagation:** structured flags (`flag_type`, `severity`, `source`, `requires_thread_state`, `message_key`); C14 emits `investigation.safety_flag_raised.v1`; C7 decides escalation and emits `thread.state_changed.v1`; C14 requests but never mutates thread state directly.
- **Event contract (both directions, transactional outbox):** C14 emits `investigation.{created,linked_to_thread,unlinked_from_thread,state_changed,safety_flag_raised,safety_flag_cleared,pending_item_added,pending_item_resolved,ready_for_visit,handed_off,closed,reopened}.v1`; C14 consumes `thread.{state_changed,closure_criteria_changed,pending_item_changed,corrected}.v1`, `consent.grant_revoked.v1`, `theory.safety_level_changed.v1`; C7 consumes `investigation.{safety_flag_raised,state_changed,closed,handed_off}.v1`.
- **Open risks:** divergent closure logic (C7 owns snapshots); stale UI from event lag (read authoritative C14/C7 for critical actions); grant revocation propagation (consume `consent.grant_revoked.v1`); safety-flag loops (idempotency keys + causal-chain IDs); thread hidden by closed investigation (C7 visibility independent of C14 closure).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
