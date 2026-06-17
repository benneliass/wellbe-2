# Decision: Ask WellBe answer-engine semantics (grounding, C10 gating, provenance, scope)

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-168  
**Blocks:** WEL-166 [Ask WellBe answer engine (C10-gated, thread/graph-grounded Q&A)]

---

## Question

For "Ask WellBe" (the answer engine behind the Home entry point WEL-157), how should free-text questions be answered safely?
1. **Grounding scope** — what data an answer may draw on (the user's own threads/graph only, source-linked) and how out-of-corpus knowledge is handled.
2. **C10 gating** — do-not-diagnose, never-alarm, provenance, and bias enforcement on generated answers.
3. **Provenance/citation contract** — how each answer cites the user's own sources.
4. **Out-of-scope / uncertain-question handling** — refusal/redirect semantics, and when to route to triage or a clinician.

## Context

Touches C10 (Safety & Governance Gate — mandatory before any user-facing AI output) plus C7/C6/C5 (threads, graph, provenance) and likely C14 (Investigation). The "Ask WellBe" entry point is already shipped (WEL-157), so an unresearched answer engine is the highest-risk gap in the build-out: a user can already type a question into live UI. See `docs/architecture/component-map.md`, `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`.

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
