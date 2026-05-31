# Decision: Safety Gate evaluation contract for AI output

**Status:** Open  
**Date opened:** 2026-06-01  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-134  
**Blocks:** WEL-74 — Implement layered Safety Gate service with deterministic rules, NeMo Guardrails, and Llama Guard

---

## Question

What is the approved C10 Safety & Governance Gate evaluation contract for user-facing AI output in the Patient-Centered Health Investigation OS?

Specifically:
1. Which deterministic rule classes must run before any model-based guardrail layer?
2. What provenance, source-quality, clinical-review marker, and uncertainty obligations are required for each risk tier?
3. How are engine risk tiers declared, validated, and enforced fail-closed before output reaches the user?
4. What outputs must be blocked, rewritten, routed to urgent guidance, or allowed with obligations?
5. What audit events and payload fields must C12 receive for allowed, denied, rewritten, and failed evaluations?
6. What latency and degradation behavior is acceptable when external guardrail layers are unavailable?

## Context

C10 is the mandatory gate before any user-facing AI output across every WellBe workspace. The new Investigation OS adds higher-risk output producers: Theory evaluation, External Evidence relevance, Live Metrics safe escalation, cross-patient comparison, clinician workspaces, institution continuity, and research sandbox outputs. A weak C10 contract would allow one of those engines to bypass do-not-diagnose, provenance, source-quality, urgency, or review-state requirements, undermining the platform's central safety guarantee.

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
