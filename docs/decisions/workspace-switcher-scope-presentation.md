# Decision: Workspace switcher presentation + scoping under C17

**Status:** Open  
**Date opened:** 2026-06-18  
**Date approved:** (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-184  
**Blocks:** WEL-182 [Workspace identity + switcher UI (personal + grant-scoped role workspaces)]

---

## Question

For the workspace identity + switcher UI:

1. How are the user's available workspaces enumerated and presented (personal always-present + grant-scoped role workspaces) without leaking the existence of grants the user should not see?
2. What exactly changes on switch (data scope, allowed actions, visible surfaces), and how is the active context made unambiguous?
3. How is the controller/grant invariant enforced in the UI so no institution-enabled or default cross-patient view can ever appear?
4. How does the active workspace compose with the session (WEL-151)?

## Context

The switcher is the UI boundary for the entire C17 audience model and touches **C17 (Workspace, Role & Grant Layer)**. Getting scoping wrong risks showing one context's data in another, implying institution control, or surfacing cross-patient views by default — all hard violations of the audience guardrails (`audience-guardrails.mdc`, `platform_identity.md`) and irreversible trust damage. The personal workspace must always be present and stand alone; every other workspace is grant-scoped, purpose-bound, and revocable, never institution-enabled by default.

## Research provided

<!-- Awaiting user-provided research. Agents may not self-research. -->

_Research received: (pending)_

## Approaches considered

<!-- Written after research is provided, grounded only in that research. -->

## Decision

<!-- Proposed after research; approved by user. -->

## Trade-offs accepted

<!-- Filled with the decision. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
