# Decision: Correction Service layered, source-linked, non-mutating overlay model

**Status:** Open
**Date opened:** 2026-06-01
**Date approved:** (fill on approval)
**Approved by:** User
**Jira Spike:** WEL-138
**Blocks:** WEL-71 — Build source-linked non-mutating Correction Service for facts and memories

---

## Question

How should the C11 Correction Service capture user corrections as layered, source-linked overlays written through C5 that never mutate the C2 Raw Context Vault or C4 extracted facts, and how do downstream reads (C6 / C8 / C13) resolve the corrected view deterministically?

Specifically:
1. What is the data model for a correction (overlay record, target reference, correction type, actor, timestamp)?
2. How does a correction attach to its target via C5 evidence links (the existing `evidence_links.correction_id` hook) without altering the target?
3. What is the deterministic read-resolution rule when a raw/derived value and one or more correction overlays disagree?
4. How are corrections audited (C12) and how do they interact with C7 reopen/relabel transitions?

## Context

Affected core component: Correction Service (C11), writing through Evidence & Provenance (C5), constrained by Raw Context Vault immutability (C2) and no-orphan-provenance (C5). The approved `raw-context-vault-immutability-enforcement.md` and `evidence-provenance-no-orphan-enforcement.md` decisions forbid mutating raw or derived data; migration 005 already added a nullable `evidence_links.correction_id` and `'correction_service'` provenance basis as a preparatory hook. If corrections are modeled as in-place edits or as un-provenanced overlays, we break immutability, lose the C12 audit trail, and create ambiguity about which layer wins on read. This is a trust-critical primitive and hard to retrofit once C13 exposes corrections.

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
