# Decision: Trust & Consent scope model and Share Grant schema

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-93  
**Blocks:** WEL-72 — Implement OIDC/passkey authentication and scoped consent-share domain model

---

## Question

What consent scope model should C1 (Trust & Consent Service) use — a flat list of named scopes, a hierarchical scope tree, or a resource-based ACL — and how should Share Grants be represented as database objects, enforced at the API boundary, and revoked with propagation?

Specifically:
1. What are the scope identifiers — flat named scopes (e.g. `thread:read`, `thread:share`) or a resource+action model?
2. How is a Share Grant represented — what fields, what lifecycle, what expiry/revocation model?
3. How is the cross-patient opt-in gate enforced in code — a feature flag per user, a separate consent scope, or a data-path guard in the API middleware?
4. How is revocation propagated — synchronous (invalidate on every request) or a revocation log with TTL-based cache invalidation?

## Context

C1 is the root of trust for the entire system. Every component from C2 through C13 enforces access using tokens and consent scopes issued by C1. It sits at layer L0 — nothing depends on anything below it; everything else depends on it. Getting the scope model wrong means either over-permissioning (privacy violation) or under-permissioning (product broken for users). Share Grant design directly affects the Visit Packet, scoped export, and care-team sharing features.

The tech stack has committed to ZITADEL as the OIDC/OAuth2 identity provider. Consent scopes and Share Grants are explicitly WellBe's own domain logic — not the IdP's — stored in Postgres and enforced at every C13 API call. Per `docs/system-design/platform_identity.md`, the deploying institution is a distribution channel, not a data controller: the individual owns their data and can revoke access at any time.

**Key constraint from the safety model:** The cross-patient opt-in gate must be off by default with no data path enabled unless each individual explicitly activates it. This is a hard guardrail, not a configuration option.

## Research provided

_Awaiting user research._

_Research received: —_

## Approaches considered

_To be written after research is received._

## Decision

_To be written after research is received and approved._

## Trade-offs accepted

_To be written after research is received and approved._

## Implementation notes

_To be written after approval._

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
