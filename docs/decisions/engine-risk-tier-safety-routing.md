# Decision: Per-engine safety risk tiers and Safety Gate routing

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-134  
**Blocks:** WEL-74 (C10 Safety & Governance Gate risk-tier extension)

---

## Question

How should **per-engine safety risk tiers** be defined and wired into the Safety & Governance Gate (C10) — what controls differ per tier, and how is the tier enforced before any user-facing output?

Specifically:
1. What is the authoritative tier assignment (lower: timeline/missing-context; medium: confounder/contradiction; medium-high: theory; high: external research, live-metric; very high: cross-patient) and where is it stored?
2. What concrete controls differ per tier (e.g. mandatory human-readable uncertainty, source-tier display, clinician-review marker, urgent routing, output blocking)?
3. How does C10 receive the engine's tier and refuse to emit if a higher-tier output lacks the required controls?
4. How are new engines forced to declare a tier (fail-closed default to highest)?

## Context

The expanded vision adds several higher-risk engines (theory, external research, live-metric, cross-patient). C10 is the single hardest architectural rule — the safety gate before any AI output. Without a tier-aware routing contract, higher-risk engines could emit through the same path as low-risk ones. C10 is already specced (WEL-74); this decides how the tier dimension extends it. Wrong design weakens the central safety guarantee for every workspace.

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
