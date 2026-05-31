# Decision: Research Sandbox / cohort comparison consent and governance model

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-133  
**Blocks:** WEL-123 (Research Sandbox / cohort comparison)

---

## Question

What consent, de-identification, and protocol-governance model permits **opt-in cross-patient/cohort comparison** while guaranteeing no default institutional access and no re-identification?

Specifically:
1. What is the explicit, per-study opt-in flow and how is it separated from normal product consent (C1)?
2. What de-identification / aggregation guarantees apply, and how is k-anonymity or equivalent enforced before any cohort result is shown?
3. What protocol-governance gate must a cohort query pass, and who can define a cohort?
4. What C10 rules prevent re-identification, cohort-of-one leakage, and any institution-default access?

## Context

Cross-patient comparison is explicitly the highest-risk surface in the bible — allowed only as a user-initiated, opt-in, governed feature (`wellbe-vision-guardrails.mdc`). It touches C1 (consent) and C10 (safety). This supersedes the old WB2-F032 "avoid for MVP" framing by replacing avoidance with a governed opt-in design. Getting consent or de-identification wrong is an irreversible privacy harm.

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
