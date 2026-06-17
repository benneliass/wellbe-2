# Decision: Visit Packet composition, source-linking, scoped-share/revocation, and C10 gating

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-160  
**Blocks:** WEL-68 [Build Visit Packet generator with source-linked summary and scoped share/export]

---

## Question

For the user-controlled clinician Visit Packet (Home pill `prep`):
1. **Composition** — what is included in a packet, and how is every claim source-linked back to its evidence (C5) so there are no orphan claims?
2. **Scoped share/export + revocation** (C1) — what is the grant model for sharing/exporting a packet (audience, purpose, duration), and what are the exact revocation semantics?
3. **C10 gating** — how does the generated summary pass the Safety & Governance Gate (do-not-diagnose, panic-language, provenance, bias) before it can be shared?

## Context

Touches C7 (Health Thread Engine), C5 (Evidence & Provenance), C10 (Safety & Governance Gate), C1 (Trust & Consent) — see `docs/architecture/component-map.md`. The packet is the first WellBe output that leaves the personal core for a third party, so a wrong decision on share scoping, revocation, or C10 gating is a safety/privacy regression that is expensive or impossible to reverse once a packet has been shared externally. Personal-first and grant-scoped guardrails apply (`.cursor/rules/wellbe-vision-guardrails.mdc`).

## Research provided

_Research received: YYYY-MM-DD_

<!-- Agent-run research (model, date) to be recorded verbatim here per research-protocol Section I.
     This Spike touches C10 — the user must confirm before any agent-run research is executed. -->

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
