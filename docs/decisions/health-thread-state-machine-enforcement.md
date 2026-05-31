# Decision: Health Thread state machine transition enforcement pattern

**Status:** Proposed  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-92  
**Blocks:** WEL-64 — Implement Health Thread object, lifecycle state machine, and subgraph linking

---

## Question

How should the Health Thread state machine enforce lifecycle transitions — as pure Python domain-model enforcement, as Postgres-level constraints/triggers, or as Temporal workflow state?

Specifically:
1. Which layer owns the "invalid transition" rejection — domain model, DB constraint, or API middleware?
2. How are side effects triggered on a valid transition — synchronous (in-process), transactional outbox, or Temporal signal?
3. What is the persistence model for the current thread state — a `status` column, an event-sourced log, or a combination?
4. Does the state machine need to coordinate directly with C9's durable Temporal timers at transition time, or is that decoupled through events?

## Context

C7 (Health Thread Engine + State Machine) is the central product object at layer L3. Every component above it — C8 Six Memories, C9 Continuity & Closure Engine, C10 Safety & Governance Gate, C13 API & Contract Layer — reads or writes thread state. The stack has already committed to Python (backend), Postgres (primary store), Temporal (durable workflows), and a transactional outbox + Redis Streams for events. The state machine states and allowed transitions are fully defined in `docs/system-design/health_thread_state_machine.md`.

What is **not** decided is which layer enforces transitions, how side effects are made durable, and what the persistence model looks like. Guessing wrong here is expensive: C8, C9, and C13 will all be built on top of whatever contract C7 establishes, and the event schema emitted on `thread.state_changed` becomes a stable contract that is hard to change later.

## Research provided

### Project context

WellBe is a **Personal Shared Health Memory OS** — a user-controlled memory layer for unresolved health concerns. Its core product promise:

> Help a person carry their health context forward until an issue is resolved, explained, monitored, or safely handed off.

The operating loop is: **Capture → Connect → Clarify → Close → Correct**

Everything in the system is organized around **Health Threads** — one thread per unresolved concern. A thread is a living container holding: patient's own words, timeline, symptoms, test results, referrals, pending items, corrections, and a shareable summary.

---

### What C7 is and why it matters

**C7 — Health Thread Engine + State Machine** sits at layer L3 (the middle of the stack). It is the central organizing object that everything above depends on:

- C8 (Six Memories) organizes memory *around* each thread
- C9 (Continuity & Closure Engine) tracks open loops *per* thread
- C10 (Safety Gate) evaluates AI output *in context of* a thread
- C13 (API layer) exposes thread state as the primary resource

Everything below C7 feeds *into* it:
- C5 (Evidence & Provenance) provides source-linked facts
- C6 (Knowledge Graph) provides typed, scored edges between entities

---

### The state machine (already defined)

The states and transitions are fully specified in `docs/system-design/health_thread_state_machine.md`:

| State | Allowed next states |
|---|---|
| `draft` | `active_unresolved`, `archived` |
| `active_unresolved` | `waiting_for_result`, `referred`, `watchful_waiting`, `escalated`, `explained`, `chronic_monitoring` |
| `waiting_for_result` | `active_unresolved`, `explained`, `escalated`, `chronic_monitoring` |
| `referred` | `active_unresolved`, `waiting_for_result`, `explained`, `chronic_monitoring` |
| `watchful_waiting` | `active_unresolved`, `escalated`, `explained`, `chronic_monitoring` |
| `escalated` | `active_unresolved`, `waiting_for_result`, `referred`, `explained` |
| `explained` | `closed`, `chronic_monitoring`, `active_unresolved` |
| `chronic_monitoring` | `active_unresolved`, `escalated`, `closed` |
| `closed` | `reopened` |
| `reopened` | `active_unresolved` |

**Safety rules baked in:**
- The system cannot close a thread because a single test is normal
- The system cannot mark a diagnosis as final
- If symptoms persist after a normal test, thread stays active or watchful-waiting
- User correction can reopen or relabel a thread at any time

---

### The technology stack (already decided)

| Concern | Choice |
|---|---|
| Backend language | Python 3.13 |
| Backend framework | FastAPI + Pydantic v2 |
| Primary datastore | PostgreSQL 17 |
| Durable workflows | Temporal (for long-running, must-not-lose-progress flows) |
| Lightweight jobs | Dramatiq + Redis |
| Events | Transactional outbox (Postgres) + Redis Streams |
| Graph store | Apache AGE (Cypher on Postgres) + pgvector |

**Key event already named:** `thread.state_changed` — emitted on every valid transition. This event is a stable contract consumed by C8, C9, C12, and C13.

---

### Research: recommended decision

Adopt a C7-owned domain transition command, backed by Postgres defensive enforcement, persisted as current status plus append-only transition log, and propagated through a transactional outbox. C9 should react to `thread.state_changed` events and own Temporal timers; C7 should not synchronously call C9 or make Temporal the source of truth for thread lifecycle state.

**In one sentence:** C7 is the authority for lifecycle transitions; Postgres prevents corrupted writes; the outbox makes state-change events durable; Temporal reacts downstream for continuity timers.

---

### Research: direct answers to the four questions

**1. Which layer owns invalid transition rejection?**
Primary owner: Python C7 domain/application service. Secondary guard: Postgres transition guard trigger/constraint-table defense. API middleware is not an owner — it validates request shape, auth, and idempotency, and maps domain errors to HTTP responses; it does not duplicate the lifecycle graph.

**2. How are side effects triggered on valid transition?**
Use the transactional outbox. In one Postgres transaction: update `health_threads.status`, increment `status_version`, insert `thread_state_transitions`, and insert an `outbox_events` row with `event_type = thread.state_changed`. Consumers process the event asynchronously and idempotently.

**3. What is the persistence model?**
Combination: `health_threads.status` is the canonical current state for reads; `health_threads.status_version` supports ordering and concurrency; `thread_state_transitions` is the append-only lifecycle history; `outbox_events` is the durable integration queue.

**4. Does C7 coordinate directly with C9 Temporal timers?**
No. C7 emits `thread.state_changed`. C9 consumes it and starts, signals, updates, cancels, or replaces Temporal timers from its own event consumer. Temporal may later call C7 through a command, but Temporal is not the lifecycle state owner.

---

### Research: implementation pattern

**Command boundary**

```python
transition_thread(
    thread_id: UUID,
    target_status: HealthThreadStatus,
    actor: ActorRef,
    reason_code: str,
    evidence_refs: list[EvidenceRef],
    idempotency_key: str,
    expected_version: int | None = None,
    metadata: dict = {},
) -> ThreadTransitionResult
```

**Domain validation — two separate layers**

```
edge validity:  explained -> closed is structurally allowed
guard validity:  explained -> closed is rejected if closure is based only on one normal test
                explained -> closed is rejected if symptoms persist unresolved
                any AI-generated final-diagnosis claim is rejected or downgraded
                closed -> reopened is allowed for user correction
```

**Transaction flow**

```
begin transaction
1. load health_threads row FOR UPDATE
2. check idempotency_key
3. validate expected_version if provided
4. domain validates current_status -> target_status (edge check)
5. domain evaluates safety/context guards
6. update health_threads.status and increment status_version
7. insert thread_state_transitions row
8. insert outbox_events row with event_type = 'thread.state_changed'
9. commit
```

**Persistence objects**

- `health_threads` — canonical current status, `status_version`, `status_changed_at`
- `thread_state_transitions` — append-only history with actor, `reason_code`, `evidence_refs`, `safety_flags`, `idempotency_key`, `correlation_id`, `transition_seq`
- `outbox_events` — durable integration events with `aggregate_id`, `aggregate_version`, `event_type`, `schema_version`, `payload`, `published_at`
- `health_thread_allowed_transitions` — DB-level lookup table of structurally allowed edges for trigger enforcement

**`thread.state_changed` event contract**

```json
{
  "event_id": "uuid",
  "event_type": "thread.state_changed",
  "schema_version": 1,
  "occurred_at": "2026-05-31T10:15:00Z",
  "thread_id": "uuid",
  "patient_id": "uuid",
  "from_status": "active_unresolved",
  "to_status": "waiting_for_result",
  "transition_seq": 7,
  "actor": {"type": "user | clinician | system | workflow | admin", "id": "uuid-or-null"},
  "reason_code": "result_pending",
  "idempotency_key": "client-or-system-key",
  "correlation_id": "request-or-workflow-correlation-id",
  "evidence_refs": [{"type": "lab_order", "id": "uuid"}],
  "safety_flags": [],
  "metadata": {"source_component": "C13", "expected_followup_policy": "result_followup"}
}
```

Consumers should use `(thread_id, transition_seq)` for ordering, not Redis global ordering. For deduplication, consumers should store `event_id` or `(thread_id, transition_seq, event_type)`.

**C9 / Temporal handling**

```
on thread.state_changed:
  if event already processed: ack/no-op
  signal_with_start workflow_id = "thread-continuity:{thread_id}"
      signal = "thread_state_changed"
      payload = event
  mark event processed
```

If a C9 timer fires and wants to move the thread, it must call C7 through the transition command. If the thread has already moved, C7 rejects or no-ops the stale timer command — this is the desired race-safe behavior.

---

### Research: references

- PostgreSQL 17 documentation: Constraints and triggers — https://www.postgresql.org/docs/17/ddl-constraints.html
- PostgreSQL 17 documentation: SELECT / row locking clauses — https://www.postgresql.org/docs/17/sql-select.html
- AWS Prescriptive Guidance: Transactional outbox pattern — https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- Temporal documentation: Python workflow timers — https://docs.temporal.io/develop/python/workflows/timers
- Temporal documentation: Workflow message passing — https://docs.temporal.io/encyclopedia/workflow-message-passing
- Temporal documentation: Workflows and determinism/replay model — https://docs.temporal.io/workflows

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| Pure Python domain model only | Rejected | Correct for business semantics, but does not protect against direct DB writes, migration bugs, or future bypasses. |
| Postgres-only constraints/triggers | Rejected | Good as a guardrail, but poor for contextual health-safety rules, user-facing errors, C10 policy checks, evidence-aware closure rules, and versioned domain logic. |
| API middleware enforcement | Rejected | Middleware should not know lifecycle semantics. It authenticates, authorizes, validates request shape, and maps domain errors — it does not duplicate the lifecycle graph. |
| Temporal workflow as state owner | Rejected | Durable, but makes current product state opaque, harder to query, and coupled to workflow availability, replay, and versioning. |
| Synchronous in-process side effects | Rejected | Creates partial-failure and retry problems across C8, C9, C12, and C13. |
| Transactional outbox | **Accepted** | Makes state change and event emission atomic with the DB transaction; supports retryable, idempotent downstream processing. |
| `status` column only | Rejected | Too little auditability and weak event reconstruction. |
| Event-sourced log only | Rejected | Overkill for C7 current-state reads; complicates C13/API and C10 reads. |
| `status` column + append-only transition log | **Accepted** | Fast current-state reads plus durable lifecycle history. |

## Decision

C7 will enforce Health Thread lifecycle transitions through a domain-owned `transition_thread` command implemented in Python. All components that change thread lifecycle state must call this command; no component may directly patch `health_threads.status`.

Postgres will provide defensive integrity enforcement for allowed lifecycle edges, using a status value constraint/lookup table plus a transition guard trigger. The database guard exists to catch bypasses and corrupted writes, not to replace the domain model.

Every valid transition will be persisted in one Postgres transaction by: updating the current `health_threads.status`, inserting an append-only `thread_state_transitions` row, and inserting a `thread.state_changed` row into the transactional outbox. External side effects will be handled asynchronously by outbox consumers.

The current lifecycle state will be stored directly on `health_threads.status` for simple reads and queries. The transition log will provide lifecycle history, auditability, reconstruction support, and the basis for the emitted event contract.

C9 will not be called synchronously by C7. C9 will subscribe to `thread.state_changed` and start, signal, update, cancel, or replace Temporal timers from its own event consumer. Temporal workflows may initiate future C7 transition commands, but C7 remains the only authority that validates and commits status changes.

## Trade-offs accepted

- Accept eventual consistency between C7 status commits and downstream side effects (C8, C9, C12, C13 react via outbox, not synchronously).
- Accept duplicate enforcement in Python and Postgres as intentional defence-in-depth — the overhead is worth the safety guarantee.
- Reject pure event sourcing for now — current status is directly queryable, accepting that replay-based reconstruction is not a first-class capability at MVP.
- Reject direct synchronous integration with Temporal to avoid reintroducing dual-write failure modes in the transition path.

## Implementation notes

**Rules for WEL-64:**
- No raw status patching — every lifecycle mutation goes through `transition_thread`
- Every committed status change has exactly one `thread_state_transitions` row
- Every transition row has exactly one outbox event
- Every event has a stable `event_id` and `transition_seq`
- Consumers are idempotent
- C9 owns timers; C7 owns lifecycle state

**Required test coverage:**

```
domain tests:
  - every allowed edge succeeds
  - every disallowed edge fails
  - closure based only on one normal test fails
  - persistent symptoms prevent closure
  - closed -> reopened succeeds for user correction

database tests:
  - direct invalid status update is rejected by trigger
  - allowed transition table matches Python graph
  - transition_seq is unique per thread

concurrency tests:
  - two simultaneous transitions cannot both commit from same version
  - stale expected_version returns conflict
  - repeated idempotency_key returns same result

outbox tests:
  - status update and outbox insert commit together
  - rollback emits no event
  - duplicate event delivery is safe

C9 tests:
  - waiting_for_result starts/replaces timer
  - leaving waiting_for_result cancels timer
  - stale timer firing cannot force invalid transition
```

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
