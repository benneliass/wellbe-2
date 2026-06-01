# Decision: Continuity Pending Item Ledger, durable timers, and closure safety net

**Status:** Open
**Date opened:** 2026-06-01
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

<!-- To be filled verbatim when the user provides research. Agents may not self-research. -->

_Research received: (pending)_

## Approaches considered

<!-- Written by agent only after research is provided, grounded strictly in that research. -->

## Decision

<!-- Proposed by agent after research, approved by user. -->

## Trade-offs accepted

<!-- Filled on decision. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
