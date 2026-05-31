# Decision: Deep Grant/Role model and multi-audience workspace access

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-131  
**Blocks:** WEL-118 (deep Grant/Role), WEL-119 (Clinician workspace), WEL-120 (Shared workspace), WEL-127 (C13 contract)

---

## Question

How should the deep **Grant/Role** model extend the existing Trust & Consent Service (C1) and ShareGrant to support multi-audience workspaces (Individual, Clinician Case Investigation, Shared Health Thread, Institution Continuity, Research Sandbox) without weakening personal-first control?

Specifically:
1. What is the grant scope taxonomy (visit-packet-only / specific-thread / labs+symptoms / wearable-trends-only / full-investigation) and how is least-privilege enforced at query time?
2. How are `can_comment`, `can_export`, `can_invite`, and `contribution_becomes_permanent_record` enforced, and how do recipient contributions enter (or not enter) the append-only record?
3. How is institution access constrained to aggregate-only + consented (no individual-level default), and where is that enforced?
4. How do grants expire/revoke (time-boxed, post-visit auto-expiry) and how is every access audited via C12?

## Context

C17 is the architectural mechanism for the entire multi-audience expansion and extends C1, the highest-blast-radius trust component. A weak grant model would allow institutional overreach or default access — a direct violation of the bible (`platform_identity.md`, `audience-guardrails.mdc`). The grant contract is consumed by every workspace and by C13. C1 is a Done foundation component, so the extension boundary must be decided before the C1 retrofit and before any workspace story.

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
