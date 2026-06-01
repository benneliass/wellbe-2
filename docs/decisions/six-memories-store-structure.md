# Decision: Six Memories store structure and authored-vs-derived population model

**Status:** Open
**Date opened:** 2026-06-01
**Date approved:** (fill on approval)
**Approved by:** User
**Jira Spike:** WEL-136
**Blocks:** WEL-70 — Build Story, Clinical, Pattern, Decision, Responsibility, and Equity memory models

---

## Question

How should the Six Memories store (C8) structure, partition, and populate each memory type (Story / Clinical / Pattern / Decision / Responsibility / Equity) — which are user-authored vs system-derived, and how do they read from the C6 knowledge graph and cite C5 provenance without becoming a competing source of truth?

Specifically:
1. Is each memory type a distinct table/schema, or one polymorphic store with a `memory_type` discriminator?
2. Which memory types are authored by the user, which are derived from C4/C5/C6, and which are hybrid?
3. How does a derived memory entry reference its source (C5 evidence links / C6 nodes) so it stays consistent and correctable, rather than copying facts?
4. How are corrections (C11) reflected in memory reads without mutating source data?

## Context

C8 sits at L4 and is read by C13 (and the future UI). Affected core component: Six Memories Store (C8), with hard dependencies on Evidence & Provenance (C5) and Knowledge Graph Store (C6). If memory entries duplicate facts instead of referencing C5/C6, we create a second source of truth that can silently diverge, violate the "no orphan claims" provenance rule, and make C11 corrections impossible to propagate. The authored-vs-derived split becomes a stable contract once C13 exposes memory surfaces, so guessing wrong is expensive.

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
