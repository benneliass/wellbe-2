# Decision: MVP onboarding consent + identity flow on top of C1

**Status:** Open  
**Date opened:** 2026-06-18  
**Date approved:** (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-183  
**Blocks:** WEL-181 [MVP onboarding / first-run flow: welcome, consent capture, baseline profile & goals]

---

## Question

For the MVP first-run onboarding flow, on top of the C1 Trust & Consent model:

1. Which consent scopes must be captured up front, and which are deferred to point-of-use?
2. What minimal baseline identity + profile data is collected, and what is optional/skippable?
3. How does identity bootstrap compose with the real session (ZITADEL / WEL-151)?
4. What are the resume/idempotency semantics if onboarding is abandoned mid-flow?

## Context

Onboarding is the first consent surface a new individual ever sees, and it touches **C1 (Trust & Consent Service)** — the root of trust that everything reading or writing user data calls. Capturing the wrong scopes (too broad violates personal-first/consent-scoped; too narrow makes core features silently fail), or making consent implicit/non-revocable, would be a trust-defining and expensive-to-reverse mistake once real users exist. The flow must keep the individual as controller and let a single user with no organizational affiliation complete onboarding alone.

## Research provided

<!-- Awaiting user-provided research. Agents may not self-research. -->

**Research brief for the external observer:** [`research-briefs/WEL-183-onboarding-consent-identity-research-brief.md`](research-briefs/WEL-183-onboarding-consent-identity-research-brief.md) — self-contained context, questions, and deliverable instructions. Findings come back as the file `WEL-183-onboarding-research-findings.md` and are recorded verbatim here.

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
