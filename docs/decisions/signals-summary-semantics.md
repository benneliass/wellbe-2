# Decision: Home signals summary / health-adaptive UI semantics (computation + never-alarm framing)

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-167  
**Blocks:** WEL-91 [Implement health-adaptive UI with state-driven design tokens, never-alarm rule, and a11y]

---

## Question

For the Home "signals" summary / health-adaptive UI (the "Your signals look steady · N of N systems in range" line, currently hard-coded mock), how should a live health-status summary be computed and framed?
1. **Signal computation** — which signals/systems are summarized and how status ("in range / steady") is derived (C4 Processing).
2. **Never-alarm framing** — how an aggregate health-status line is phrased to avoid both false reassurance and alarm (C10).
3. **Confidence/uncertainty** — how confidence is surfaced.
4. **Missing/stale data** — what is shown when inputs are missing or out of date.

## Context

Touches C4 (Processing — signal computation) and C10 (never-alarm framing of a user-facing derived health judgment). The status line is currently mock data in `apps/web/lib/meta.ts`; going live turns it into a derived health-status claim. See `docs/architecture/component-map.md`, `docs/safety/safety_model.md`. Relates to WEL-43 (WB2-F040 Health-adaptive UI).

## Research provided

_Research received: YYYY-MM-DD_

<!-- Research recorded verbatim here per research-protocol Section I (user-provided or agent-run). -->

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
