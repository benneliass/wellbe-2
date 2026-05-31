# Decision: Health Thread state machine transition enforcement pattern

**Status:** Open  
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

### The open questions (what needs research)

The states are defined. The tech is decided. What is NOT decided:

**1. Which layer enforces "invalid transition" rejection?**
- Option A: Pure Python domain model — the `HealthThread` object raises an exception if the transition is invalid
- Option B: Postgres constraint/trigger — the DB rejects invalid state values at write time
- Option C: Both (defence in depth)

**2. How are side effects made durable on a valid transition?**

When a thread moves from `active_unresolved` to `waiting_for_result`, several things need to happen: a `thread.state_changed` event must be emitted, C12 (audit log) must record it, C9 (Continuity Engine) may need to start a durable timer. If any of these fail mid-way, what happens?
- Option A: Synchronous in-process — all side effects happen in the same function call
- Option B: Transactional outbox — the state change and event emission are atomic in one DB transaction; workers consume the event
- Option C: Temporal activity — the transition itself is a Temporal workflow step, making it durable and replayable

**3. What is the persistence model for current state?**
- Option A: `status` column on the `health_threads` table — simple, direct, queryable
- Option B: Event-sourced log only — current state is derived by replaying events, never stored directly
- Option C: Combination — `status` column as a materialised view of the event log (best of both)

**4. Does C9 (durable timers) couple directly to C7 at transition time?**

C9 needs to start a timer when a thread enters `waiting_for_result` (e.g., "follow up in 7 days if no result"). Does C9 subscribe to the `thread.state_changed` event asynchronously, or does C7 call into C9 synchronously at transition time?

---

### What the decision must cover

A single, concrete implementation pattern for C7 that answers all four sub-questions above. The decision will unblock WEL-64 and all Stories that depend on it: WEL-65 (API contracts), WEL-67 (Continuity & Closure), WEL-70 (Six Memories), WEL-74 (Safety Gate).

_Research received: 2026-05-31_

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
