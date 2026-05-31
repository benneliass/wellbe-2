# Decision: Investigation object model and coupling to the Health Thread state machine

**Status:** Open  
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

_Research results must be provided by the user. Agents may not self-research._

_Research received: YYYY-MM-DD_

## Approaches considered

<!-- Filled after research is provided. -->

## Decision

<!-- Proposed after research, approved by user. -->

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
