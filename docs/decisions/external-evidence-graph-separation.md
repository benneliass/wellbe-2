# Decision: External Evidence Graph separation and relevance-link semantics

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-XXX (pending creation)  
**Blocks:** External Evidence Graph + Research Watch (C16) story; External Research Relevance engine story

---

## Question

How should the **External Evidence Graph** (C16) be separated from the personal Knowledge Graph (C6) and Evidence & Provenance Service (C5), and how are **relevance links** scored and constrained so external claims never become facts about the user?

Specifically:
1. Physical/logical separation: separate store, separate schema in the same store, or namespaced subgraph — and how is cross-contamination structurally prevented?
2. How is `source_quality_tier` (Tier 1–5) assigned, stored, and surfaced, and can it ever be upgraded by usage?
3. How is a `relevance_link` scored (confidence) and what prevents an external claim from being asserted as a personal fact?
4. How does C5 provenance treat external sources differently from personal sources (so external claims are never counted as evidence about the user)?

## Context

The vision's core safety stance is that external medical knowledge is *context, never fact about the user*. Blending the external graph into C6, or letting C5 score external claims as personal evidence, would break that guarantee and the "no orphan claims" provenance rule. C5 and C6 are both in-flight/Done foundation components, so the separation boundary and relevance-link contract must be settled before C16 is built and before any retrofit touches C5/C6.

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
