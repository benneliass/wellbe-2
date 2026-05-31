# Decision: Trust & Consent scope model and Share Grant schema

**Status:** Proposed  
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

### Executive summary (C1)

ZITADEL handles authentication and issues coarse OIDC/OAuth capability scopes. WellBe owns health-data access policy in its own Postgres tables (consent rows, share grant ACL rows, revocation log). Token scopes are treated as capability hints; the real consent evaluation happens against WellBe policy rows. Consent semantics are never delegated to the IdP.

### Q1 — Consent scope model

**Recommended approach:** flat named API scopes at the token level + resource/action ACL rows in WellBe Postgres as the source of truth.

Token scopes (coarse capability, issued by ZITADEL):
```
thread:read, thread:write, thread:share
vault:write
memory:read, memory:write
consent:manage, share_grant:manage
audit:read
```

WellBe policy rows (resource/action access, fine-grained):
```
subject_id, resource_type, resource_id (nullable), action,
data_category, purpose, grant_source,
valid_from, valid_until, revoked_at, policy_version
```

C13 does a first-pass token scope check (e.g. `thread:read` present?), then C1 evaluates the real consent/share policy against WellBe rows. Wildcard scopes (e.g. `thread:*`) are reserved for internal service roles only — not for user-facing grants, where over-authorization risk is too high.

### Q2 — Share Grant schema and lifecycle

**Recommended lifecycle:**
```
pending → active → expired
pending → revoked
active  → revoked
```

**Recommended fields:**
```
id, grantor_id, grantee_user_id (nullable), grantee_identifier_hash,
grantee_type (user | clinician | email_invite | org), status,
resource_selector, thread_ids (jsonb or join table),
actions (read_summary | read_evidence | comment | export | ...),
data_categories (thread_summary | raw_docs | labs | memories | ...),
purpose, expires_at, accepted_at, revoked_at, revoked_by,
revocation_reason, created_at, created_by, last_accessed_at,
consent_snapshot_id, grant_token_hash (nullable), policy_version,
metadata (jsonb)
```

Default: share only explicitly selected `thread_ids`. All-threads sharing requires a distinct user choice with UI displaying the blast radius. Old grant history is never physically mutated — lifecycle columns are updated and a revocation event is appended.

### Q3 — Cross-patient opt-in gate

**Recommended approach:** separate named consent setting + runtime data-path guard (not a simple boolean).

```
patient_privacy_preferences
  patient_id
  capability = cross_patient_analysis
  status = disabled | enabled | revoked
  enabled_at, revoked_at, purpose,
  consent_text_version, policy_version
```

Runtime rule: no cross-patient query path may execute unless ALL of: feature is globally enabled, requesting patient has opted in, query purpose is allowed, query uses approved de-identified/aggregate path, and query layer calls the explicit `authorized_population_scope(actor, purpose)` guard function. A boolean/cache field may exist as a materialised read model but is never the source of truth.

### Q4 — Revocation propagation

**Recommended approach:** synchronous invalidation for Share Grants.

```
revoke grant transaction:
  UPDATE share_grants.revoked_at/status
  INSERT consent_revocation_log row
  INSERT outbox event consent.share_grant_revoked
  synchronously delete/rekey Redis cache entry
  COMMIT
```

C13 checks C1 grant state from DB or a revocation-aware Redis cache on every API request that uses a Share Grant. JWT expiry alone is insufficient for health-data sharing revocation. HIPAA allows revocation except for actions already taken in reliance on the authorization; GDPR requires withdrawal support while preserving the lawfulness of prior processing.

### References

- OAuth 2.0 Authorization Framework, RFC 6749 — https://www.rfc-editor.org/info/rfc6749/
- ZITADEL OIDC/OAuth claims documentation — https://zitadel.com/docs/apis/openidoauth/claims
- HHS HIPAA FAQ: revoking authorization — https://www.hhs.gov/hipaa/for-professionals/faq/474/can-an-individual-revoke-his-or-her-authorization/index.html
- PostgreSQL 17 Row Security Policies — https://www.postgresql.org/docs/17/ddl-rowsecurity.html

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| Pure OIDC token scopes only | Rejected | Token bloat, no queryable consent history, over-authorization risk as new actions are added |
| Hierarchical wildcard scope tree (e.g. `thread:*`) | Rejected | Too easy to over-authorize future actions in user-facing grants |
| Flat named API scopes + WellBe Postgres policy rows | **Accepted** | C13 coarse capability check + real consent evaluation against WellBe rows; durable, queryable consent history |
| Boolean flag for cross-patient gate | Rejected | No audit trail, no per-capability granularity, easy to accidentally enable |
| Separate consent setting + runtime data-path guard | **Accepted** | Explicit opt-in per capability; runtime enforcement cannot be bypassed by a stale cache |
| Eventually consistent revocation (TTL cache) | Rejected | Unacceptable for health data — a revoked share must be immediately honoured |
| Synchronous revocation (cache-bust on every revoke) | **Accepted** | Appropriate for health data; slight overhead is justified by user trust and HIPAA posture |

## Decision

C1 will use ZITADEL for authentication and coarse OIDC/OAuth capability scopes, while WellBe-owned Postgres consent, share-grant, and revocation tables are the source of truth for health-data access. C13 performs a first-pass token scope check; C1 performs the real consent/share evaluation against WellBe policy rows. Share Grants carry an explicit lifecycle (`pending → active → expired/revoked`), resource/action selectors, and are revoked synchronously with immediate cache invalidation. Cross-patient access is off by default and requires a separate per-user opt-in consent setting plus a `authorized_population_scope()` runtime data-path guard — no cross-patient query may bypass this guard.

## Trade-offs accepted

- Dual-layer authorization (OIDC scopes + WellBe policy rows) is more work than pure token scopes, but prevents token bloat and provides a durable, queryable consent history.
- Synchronous revocation adds a Redis cache-busting dependency on every Share Grant revocation, but is appropriate for health data.
- Wildcard scopes are forbidden for user-facing grants — new actions must be named explicitly, which requires intentional schema evolution.

## Implementation notes

- One function `authorized_population_scope(actor, purpose)` must be defined before any cross-patient service path is built. No ad hoc joins over patient data are permitted.
- Share Grant `thread_ids` default to explicit selection. The all-threads option requires a UI that clearly shows blast radius.
- Consent and Share Grant writes must go through the transactional outbox — events: `consent.scope_granted`, `consent.scope_revoked`, `share_grant.created`, `share_grant.accepted`, `share_grant.revoked`, `cross_patient_opt_in.enabled`, `cross_patient_opt_in.revoked`.
- The `consent_snapshot_id` on Share Grant rows allows auditors to see exactly what consent text was active when the grant was created.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
