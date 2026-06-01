# Decision: Continuity Pending Item Ledger, durable timers, and closure safety net

**Status:** Proposed
**Date opened:** 2026-06-01
**Research received:** 2026-06-01
**Date approved:** (fill on approval)
**Approved by:** User
**Jira Spike:** WEL-137
**Blocks:** WEL-67 — Build Pending Item Ledger with durable timers and referral/visit lifecycle trackers

---

## Question

How should the C9 Pending Item Ledger model durable timers, referral/result lifecycle, and the normal-test safety net using Temporal, driven by the C7 `thread.state_changed` event, so that a stale or late-firing timer can never force an unsafe Health Thread transition?

Specifically:
1. What is the persistence model for the pending item ledger (table shape, lifecycle states, relationship to a thread)?
2. How do Temporal workflows map to pending items — one workflow per thread, per pending item, or per follow-up policy?
3. How does C9 consume `thread.state_changed` (signal-with-start? dedicated consumer?) and how are timers started/replaced/cancelled on transitions?
4. When a timer fires, how does C9 request a transition through the C7 `transition_thread` command such that a stale timer is safely rejected/no-oped?
5. How is the normal-test safety net enforced (a single normal test must not close a thread)?

## Context

Affected core component: Continuity & Closure Engine (C9), tightly coupled to the Health Thread Engine (C7). The approved C7 decision (`health-thread-state-machine-enforcement.md`) explicitly decoupled C9 via the `thread.state_changed` outbox event and made C9 the owner of durable timers, but did not specify the ledger/timer model itself. The cluster currently has no Temporal deployment, so this also informs infrastructure. Getting the timer/race model wrong risks closing threads on a single normal test, losing pending follow-ups across restarts, or letting stale timers race the state machine — all safety-relevant continuity failures.

## Research provided

_Source: provided research report `wellbe_c8_c9_c11_research_report_2026-06-01.docx` (GPT-5.5 Pro for WellBe review, dated 2026-06-01), section "C9 Continuity & Closure Engine — WEL-137 / WEL-67". Recorded as a faithful summary; external source labels [S1]–[S20] are the report's own cited-source register._

### Source findings the report relied on (C9)

- **Temporal timers are appropriate for long waits.** Temporal's Python timer docs state a workflow can sleep for months and timers persist across worker/service downtime [S8]; the timer guide emphasizes workers consume no resources while timers wait [S9]. The report maps this to pending follow-up and referral/result tracking.
- **Signal-With-Start fits idempotent timer reconciliation.** Signal-With-Start starts a workflow if none exists with the given workflow ID, otherwise signals the existing one [S10]; this fits lazily creating/updating timer workflows from replayed outbox events.
- **Signal handlers still need application-level idempotency.** Temporal recommends custom idempotency keys for signals and warns about handler race conditions [S11]; C9 must carry `event_id`, `transition_seq`, `pending_item_id`, and `timer_epoch` through signals and workflow state.
- **Non-determinism must live in Activities.** Database reads and C7 command calls must happen in Activities, not workflow replay code [S12].
- **FHIR Task / ServiceRequest lifecycle precedents.** FHIR Task represents status-tracked work that can be controlled by a workflow engine [S4]; ServiceRequest distinguishes the clinical/service request from task-execution tracking [S5]. The report concludes C9 should keep the pending-item ledger separate from imported orders/referrals/results.
- **Transactional outbox requires idempotent consumers.** The outbox relay can publish more than once, so consumers must dedupe [S16]; C9 must dedupe `thread.state_changed` by `event_id` and order by `(thread_id, transition_seq)` per the C7 contract.
- **Temporal needs persistence and is a critical internal component.** The official Helm chart deploys server components only and requires external persistence [S15]; self-hosted Temporal should not be exposed publicly [S13, S14].

### WellBe constraints the report says dominate the design (C9)

- C7 is the only authority for thread lifecycle transitions; C9 consumes `thread.state_changed` and C7 does not synchronously call C9.
- C9 may request a transition only through `transition_thread` with `expected_version`, `idempotency_key`, evidence refs, and guard metadata.
- Stale timer commands must be rejected/no-oped by C7 and absorbed by C9 without retry storms.
- A single normal test must never close a thread; if symptoms persist, the thread stays active or watchful-waiting with explicit follow-up criteria.
- Temporal is referenced in config but not deployed in the Helm chart; WEL-67 must account for that infrastructure gap.

## Approaches considered

_Each approach is taken from the report's "Approaches considered" for C9 and grounded only in that report. Sub-question references: (1) ledger persistence model; (2) workflow→pending-item mapping; (3) `thread.state_changed` consumption; (4) race-safe transition request; (5) normal-test safety net._

### Approach 1 — One Temporal workflow per thread (sub-questions 2, 3)

A `ThreadContinuityWorkflow(thread_id)` owns all pending items/timers for the thread. Precedent: saga/process-manager per aggregate. **Pros:** easy to reason about one thread's continuity; natural place to process ordered `thread.state_changed` signals; coordinates timers/cancellations across items. **Cons:** long-lived threads with many items create large workflow histories; one bad workflow state affects all items; replacing a single timer is less isolated; Continue-As-New + signal dedupe become mandatory early. The report rates it useful for later thread-level orchestration but too coarse as the MVP timer unit.

### Approach 2 — One Temporal workflow per pending item (sub-questions 1–5) — recommended

Each active pending item runs `c9-pending-{pending_item_id}`; it waits for its due time and handles reschedule/cancel/resolve signals, calling Activities to emit due events or request C7 transitions. Precedent: durable timer per business object, FHIR Task-like execution tracking [S4], Temporal durable timers [S8, S9]. **Pros:** clean isolation; natural idempotency boundary; easy to cancel/replace one timer; small workflow history; unknown due dates can sit in the ledger without starting a timer; good fit for referrals, results, follow-ups, normal-test safety items, post-visit checks. **Cons:** more workflows; thread-level policies require a consumer/reconciler to update multiple workflows; requires deterministic workflow ID and careful signal idempotency. The report rates this the best MVP fit when combined with a dedicated outbox consumer + ledger reconciliation.

### Approach 3 — One workflow per follow-up policy (sub-question 2)

Workflows represent policies (normal-test follow-up, referral tracking, result-pending), each scanning many items. Precedent: batch scheduler / policy engine. **Pros:** fewer workflows; centralizes policy logic. **Cons:** poor isolation; complex scans; harder per-item audit/idempotency; a policy workflow can become a hidden source of state separate from the ledger; less natural for user-facing pending-item objects. The report does **not** recommend it for a safety-bearing MVP — policy code should decide what items exist, but timers should remain per-item.

### Approach 4 — Relational poller fallback instead of Temporal (sub-questions 1, 2)

Store due times in Postgres and poll due rows with a scheduled job/Dramatiq worker. Precedent: simple job scheduler. **Pros:** easy local dev; no Temporal cluster dependency; adequate for non-safety reminders. **Cons:** weaker durability/clock-skew/retry/observability semantics; custom exactly-once/no-op logic; can miss/duplicate timers during outages; contradicts the already-decided Temporal direction. The report rates it acceptable only as a clearly marked local-dev/non-production degraded mode — **it must not satisfy WEL-67 acceptance for safety-bearing pending follow-ups.**

## Decision

**(Proposed — pending user approval.)** Persist C9 continuity state in a Postgres `c9.pending_items` ledger (the operational source of truth for continuity, never for clinical facts or thread state) and run **one Temporal workflow per active pending item** (report Approach 2) using deterministic workflow IDs (`c9-pending-{pending_item_id}`) and Signal-With-Start. A **dedicated C9 outbox consumer** consumes `thread.state_changed`, dedupes by `event_id`, orders by `(thread_id, transition_seq)`, reconciles ledger rows, and starts/signals/cancels pending-item workflows. When a timer fires, the workflow calls Activities that re-read the ledger, verify `timer_epoch` and item version, then request any thread transition **only** through C7 `transition_thread` with `expected_version`, `idempotency_key`, evidence refs, and explicit guard metadata; C7 stale-version, invalid-edge, and safety-guard rejections are **terminal no-ops** for that timer epoch (no retry storm). The **normal-test safety net** is represented at two layers: (a) a C9 `normal_test_safety_net` pending item that keeps follow-up visible and blocks any C9 closure request, and (b) C7 guard context (`closure_basis_single_normal_test`, `symptoms_persist`) on every C9-generated transition request — C9 never requests closure based on a single normal test. **WEL-67 is not production-ready until Temporal is deployed in-cluster** with persistence, namespace, internal-only UI/access, workers, metrics, and backup/restore.

## Trade-offs accepted

- Many workflows accepted in exchange for per-item isolation and small histories.
- C9 duplicates some thread context (`latest_observed_thread_transition_seq`, `thread_status_version`) in the ledger only as stale-command protection — never as authoritative thread state.
- C9 may lag C7 (event-driven); C7 guards remain the safety authority; C9 reconciles eventually and absorbs stale-timer no-ops.
- Business rejections are not retried; only transient transport errors retry. C7 stale/guard rejections mark the timer action `no_op_rejected` and stop.
- No production fallback to Dramatiq/Redis timers; a relational poller is allowed only for local non-safety development or ledger smoke tests while Temporal Helm work is completed.

## Implementation notes

_All schema/DDL, topology, and tests below are the report's recommendation, recorded for the implementer._

### Ledger persistence model (report DDL, reformatted)

Pending items may have unknown owner/contact and unknown due date.

```sql
CREATE SCHEMA IF NOT EXISTS c9;
CREATE TYPE c9.pending_item_type AS ENUM (
  'result_pending', 'referral_pending', 'follow_up_due', 'repeat_test_due',
  'post_visit_plan_check', 'normal_test_safety_net', 'user_next_step', 'care_team_next_step');
CREATE TYPE c9.pending_item_status AS ENUM (
  'draft', 'active', 'waiting_external', 'scheduled', 'due', 'overdue',
  'in_progress', 'result_received', 'resolved', 'cancelled', 'superseded', 'no_due_date');
CREATE TABLE c9.pending_items (
  pending_item_id uuid PRIMARY KEY,
  patient_id uuid NOT NULL,
  primary_thread_id uuid NOT NULL,
  item_type c9.pending_item_type NOT NULL,
  status c9.pending_item_status NOT NULL,
  title text NOT NULL,
  next_action_code text NULL,
  due_at timestamptz NULL,
  due_precision text NOT NULL DEFAULT 'unknown'
    CHECK (due_precision IN ('unknown', 'date', 'datetime', 'relative_policy')),
  owner_ref jsonb NULL,
  contact_ref jsonb NULL,
  source_ref jsonb NOT NULL,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  investigation_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
  latest_observed_thread_transition_seq bigint NULL,
  latest_observed_thread_status_version bigint NULL,
  blocks_c9_closure_request boolean NOT NULL DEFAULT false,
  normal_test_safety_net boolean NOT NULL DEFAULT false,
  symptoms_persist_state text NOT NULL DEFAULT 'unknown'
    CHECK (symptoms_persist_state IN ('unknown', 'reported_persistent', 'reported_resolved', 'not_applicable')),
  timer_epoch bigint NOT NULL DEFAULT 0,
  workflow_id text NULL UNIQUE,
  workflow_run_id text NULL,
  version bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz NULL,
  cancelled_at timestamptz NULL,
  idempotency_key text NOT NULL UNIQUE,
  CHECK ((due_at IS NOT NULL) OR (status IN ('draft', 'active', 'waiting_external', 'no_due_date'))));
CREATE TABLE c9.pending_item_thread_links (
  pending_item_id uuid NOT NULL REFERENCES c9.pending_items(pending_item_id),
  thread_id uuid NOT NULL,
  relationship text NOT NULL CHECK (relationship IN ('primary', 'related', 'blocked_by', 'blocks_follow_up')),
  PRIMARY KEY (pending_item_id, thread_id, relationship));
CREATE TABLE c9.pending_item_events (
  pending_item_event_id uuid PRIMARY KEY,
  pending_item_id uuid NOT NULL REFERENCES c9.pending_items(pending_item_id),
  event_type text NOT NULL,
  event_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  actor jsonb NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  idempotency_key text NOT NULL UNIQUE);
CREATE TABLE c9.consumed_thread_events (
  event_id uuid PRIMARY KEY,
  thread_id uuid NOT NULL,
  transition_seq bigint NOT NULL,
  consumed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (thread_id, transition_seq));
CREATE TABLE c9.timer_actions (
  timer_action_id uuid PRIMARY KEY,
  pending_item_id uuid NOT NULL REFERENCES c9.pending_items(pending_item_id),
  timer_epoch bigint NOT NULL,
  action_type text NOT NULL CHECK (action_type IN (
    'started', 'rescheduled', 'cancelled', 'fired', 'c7_transition_requested',
    'c7_transition_accepted', 'no_op_stale', 'no_op_c7_rejected', 'failed_transient')),
  c7_transition_id uuid NULL,
  c7_rejection_code text NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (pending_item_id, timer_epoch, action_type));
```

### Workflow topology (report)

- Workflow ID: `c9-pending-{pending_item_id}`; task queue `c9-continuity`.
- Input: `pending_item_id`, `patient_id`, `primary_thread_id`, `timer_epoch`, `due_at`, `item_version`.
- Signals: `reconcile_timer(...)`, `cancel_timer(...)`, `resolve_item(...)`, each carrying `event_id`, `pending_item_id`, `item_version`, `timer_epoch`.
- Workflow keeps a set of processed signal idempotency keys [S11]; for long-lived items use Continue-As-New only after handler completion, carrying the dedupe window forward. Deterministic time/timer APIs only; DB reads, C7 commands, C12 emits, and C5 checks run in Activities [S12].

### `thread.state_changed` consumption (report)

Read outbox/Redis Stream → validate schema version + access fields → insert `event_id` into `c9.consumed_thread_events` (duplicate = no-op) → enforce per-thread ordering by `transition_seq` (park + request replay on gaps) → reconcile ledger rows per target status (`active`/`watchful_waiting`/`explained` ensure timers exist; `closed` cancel/archive non-applicable timers but keep history and never delete rows; `reopened` re-evaluate unresolved + safety items; safety-flagged transitions create/update follow-up items) → for each item with a due date, Signal-With-Start the deterministic workflow ID with key `thread_event:{event_id}:pending:{pending_item_id}:epoch:{timer_epoch}`.

### Timer-fire protocol (report)

Workflow records `fired` via Activity → Activity re-reads `c9.pending_items FOR UPDATE` → if resolved/cancelled/superseded, or `timer_epoch` changed, or `due_at` moved into the future → record `no_op_stale` and return success → if due, set `due`/`overdue` and emit `c9.pending_item.due` → if policy says transition, call C7 `transition_thread` with `expected_version = latest_observed_thread_status_version`, `idempotency_key = c9:pending:{pending_item_id}:epoch:{timer_epoch}:transition:{target_status}`, evidence refs, and `metadata.guard_context.{closure_basis_single_normal_test, symptoms_persist}` → on accept store transition ID + emit `c9.thread_transition.accepted`; on stale/invalid/guard rejection store `no_op_c7_rejected` with the C7 code and stop (no retry of business rejections; only transient network/DB failures retry with bounded activity retries + idempotency keys).

### Normal-test safety net (report)

Two layers: **C9 continuity layer** — create/maintain a `normal_test_safety_net` pending item when a normal result links to an unresolved/persistent-symptom thread without explicit symptom-resolution evidence; set `blocks_c9_closure_request = true`, `normal_test_safety_net = true`, `symptoms_persist_state` to `reported_persistent`/`unknown`; require explicit follow-up criteria, symptom-status check, or safe handoff before C9 considers any closure-like transition. **C7 authority layer** — every C9 transition request carries guard metadata; if closure-like and `closure_basis_single_normal_test = true` or `symptoms_persist != reported_resolved`, C7 rejects and C9 treats it as a terminal no-op. The dual representation lets C9 do continuity work while C7 stays the hard authority.

### Temporal in-cluster deployment recommendation (report — addresses the §2.4 infra gap)

For local kind/Helm, add Temporal explicitly rather than relying on `temporalHost: temporal:7233` pointing at a missing service. Minimum topology for safety-bearing flows: Temporal server via the official Helm chart (or a controlled internal wrapper); persistence backed by PostgreSQL (lowest-friction for local/kind) in a **separate Temporal DB/schema** from WellBe app schemas; namespace `wellbe-continuity-local` (kind) / `wellbe-continuity` (shared); internal DNS `temporal-frontend.<ns>.svc.cluster.local:7233`, no public exposure [S13]; internal-only Web UI; worker deployment (`continuity-worker`/`temporal-worker`) on task queue `c9-continuity` with health checks, metrics, graceful shutdown; persistence credentials via K8s secrets; backup/restore + migration procedure before production; a CI/kind smoke test proving a timer survives worker restart and fires after Temporal service restart. **Interim policy:** while Temporal is undeployed, build the ledger, DTOs, C13 non-timer surfaces, and local docker-compose Temporal tests — but do **not** ship safety-bearing due timers, normal-test follow-up automation, or closure-triggering timer behavior on Dramatiq/Redis as a substitute.

### C12/C13 events (report)

C9 emits lower-case dotted events: `c9.pending_item.created/updated/due/overdue/resolved/cancelled`, `c9.referral.status_changed`, `c9.result.received`, `c9.timer.no_op_stale`, `c9.timer.no_op_c7_rejected`. C12 owns notification copy; payloads carry source refs, item ID, thread ID, due date (if known), next-action code, and PHI-minimized summary fields.

### Test / acceptance criteria (report)

Late timer after a newer `status_version` → C7 rejects stale `expected_version`, C9 records `no_op_c7_rejected`, no retry storm; duplicate `thread.state_changed` deduped by `event_id`; out-of-order events parked until the missing `transition_seq` arrives/replays; worker restart during a one-month timer does not lose it; Temporal service restart does not lose timers (persistence); a normal result with persistent symptoms creates/maintains a safety-net item and never triggers closure; a normal-test closure request carries guard metadata and is rejected by C7; referral with unknown due date/owner represented via `no_due_date`/`waiting_external` with no timer until known; activity retries reuse the idempotency key (no duplicate C7 requests); Helm/kind acceptance test fails if `temporalHost` is configured but no Temporal frontend is reachable.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
