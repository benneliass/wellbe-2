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
