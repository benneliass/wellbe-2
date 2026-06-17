# Decision: Delta semantics for the "What Changed" view

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-163  
**Blocks:** WEL-56 [WB2-F018: Note and document delta view]

---

## Question

For the `delta` pill ("What changed?"), what are the delta semantics?
1. **What counts as a meaningful change** — new facts, status transitions, value deltas vs. baseline.
2. **Comparison window** — what time window is compared, and how is it chosen (fixed, since-last-visit, since-last-open)?
3. **Ordering/ranking** — how are deltas ordered for the user, calm and non-alarming, source-linked.

## Context

Touches C9 (Continuity & Closure Engine) and C4 (Processing) — see `docs/architecture/component-map.md`. Wrong delta semantics either hide real changes (a continuity failure — the thing WellBe exists to prevent) or manufacture noise/alarm (violating the calm, never-alarm guardrail).

## Research provided

_Research received: YYYY-MM-DD_

<!-- Agent-run research (model, date) recorded verbatim here per research-protocol Section I. -->

## Approaches considered

<!-- Written by agent after research, grounded only in the recorded research. -->

## Decision

<!-- Proposed by agent, approved by user. -->

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
