# Research Brief: C1 Deep Grant/Role Workspace Model

Prepared for: WellBe external research consultant workflow  
Date: 2026-06-01  
Owner: Ben Elias, individual data controller / product owner  
Related Jira Spike: WEL-131  
Blocked implementation: WEL-118 (deep Grant/Role model), WEL-119 (Clinician workspace), WEL-120 (Shared workspace), WEL-127 (C13 contracts)  
Decision record to complete after research: `docs/decisions/deep-grant-role-workspace-model.md`

---

## A. Why this research is required

The redesign expands WellBe from a personal shared health memory into a Patient-Centered Health Investigation OS with role-specific workspaces for individuals, caregivers, clinicians, care teams, institutions, and researchers.

This expansion touches C1 (Trust & Consent Service), the root of trust for the system, and introduces C17 (Workspace, Role & Grant Layer). The question is not whether other roles can use WellBe. The design says they can. The unresolved question is how the grant model should be structured so every non-individual workspace remains:

- user-controlled,
- least-privilege,
- purpose-bound,
- time-boxed,
- synchronously revocable,
- auditable,
- and incapable of granting default institutional or clinician control over individual data.

Agents may not answer this research question from model knowledge. Research results must be provided by the user or an external consultant.

---

## B. Canonical product constraints

These are non-negotiable and should be treated as requirements for the recommendation.

1. WellBe is a Patient-Centered Health Investigation OS. Its sovereign core is a Personal Shared Health Memory OS.
2. The individual is always the data controller.
3. Clinicians, care teams, institutions, and researchers may use role-specific workspaces only through explicit grants and governance.
4. Businesses and institutions may distribute WellBe, but deployment never confers data control.
5. No audience receives default access to an individual's data.
6. Cross-patient comparison is always opt-in, user-initiated, and never an institutional default.
7. Institution continuity intelligence, if present, must be aggregate-only, consented, and privacy-preserving.
8. Sharing must be scoped, purpose-bound, time-boxed, and revocable.
9. Every grant lifecycle event and every workspace access must be auditable.
10. Contributions from non-individual users must not silently become part of the permanent personal record.

Primary references:

- `docs/system-design/platform_identity.md`
- `docs/safety/privacy_and_consent_model.md`
- `docs/system-design/core_objects.md`
- `docs/architecture/component-map.md`
- `.cursor/rules/audience-guardrails.mdc`
- `.cursor/rules/wellbe-vision-guardrails.mdc`

---

## C. Current C1 implementation baseline

The current implemented C1 base already supports a narrower consent/share model.

Implemented tables in migration `001_c1_consent_schema.py`:

- `consent.consent_scopes`
- `consent.share_grants`
- `consent.revocation_log`
- `consent.patient_privacy_preferences`

Current model/service files:

- `backend/packages/c1_consent/src/wellbe_c1_consent/models.py`
- `backend/packages/c1_consent/src/wellbe_c1_consent/service.py`
- `backend/packages/contracts/src/wellbe_contracts/c1_consent/scopes.py`

Current capabilities:

- Resource/action consent scopes.
- Share grant lifecycle: `pending`, `active`, `expired`, `revoked`.
- Share grant fields for grantor/grantee, resource selector, thread IDs, actions, data categories, purpose, expiry, revocation, consent snapshot, token hash, metadata.
- Synchronous grant revocation path that updates the DB, inserts revocation log, clears scope cache, and emits `share_grant.revoked`.
- `patient_privacy_preferences` for cross-patient analysis opt-in, checked by `authorized_population_scope()`.

Known gaps relative to the redesign:

- No first-class workspace model.
- No first-class role model beyond coarse grantee type.
- No grant scope taxonomy for `visit-packet-only`, `specific-thread`, `labs+symptoms`, `wearable-trends-only`, `full-investigation`.
- No explicit `can_comment`, `can_export`, `can_invite`, or `contribution_becomes_permanent_record` columns.
- No institution aggregate-only enforcement model.
- No C12 audit service implementation covering every grant/workspace access.
- No API contract version for the deep Grant/Role model.

---

## D. Target objects from the redesign

### Workspace

A role-specific interface over shared primitives. Workspace types:

- Individual
- Clinician Case Investigation
- Shared Health Thread
- Institution Continuity
- Research Sandbox

A workspace can read or contribute to an individual's data only through an active Grant. The individual remains the data controller in every workspace.

### Role

The capacity in which a participant acts:

- individual / controller
- caregiver
- clinician
- care team
- institution
- researcher

A Role never confers data control. It only defines which Grants a participant may be offered.

### Share Grant / Deep Grant

A scoped, revocable permission that lets a recipient view or contribute to selected context for a specific purpose and time window.

Fields proposed by the redesign:

- `recipient_role`
- `purpose`
- `scope`
- `duration` / expiry
- `can_comment`
- `can_export`
- `can_invite`
- `contribution_becomes_permanent_record`
- `workspace_scope`

Institutions receive only aggregate, consented grants, never default individual-level access.

---

## E. Research questions to answer

Please answer these questions directly. Where possible, include recommended schema shape, policy evaluation flow, enforcement boundaries, and examples of allowed/denied access.

### Q1. Grant scope taxonomy and least-privilege enforcement

How should WellBe model grant scopes for:

- `visit-packet-only`
- `specific-thread`
- `labs+symptoms`
- `wearable-trends-only`
- `full-investigation`

Required answer:

- Recommended schema pattern.
- Whether scope should be represented as enum columns, policy rows, JSON selectors, join tables, or a hybrid.
- How to enforce least privilege at query time.
- How to prevent broad grants from accidentally including raw data or memories outside the intended scope.
- How this should compose with the existing `consent_scopes` table.

### Q2. Role and workspace model

How should Role and Workspace be represented relative to ShareGrant?

Required answer:

- Whether Role and Workspace should be first-class tables.
- How workspace membership should be modeled.
- How the same person acting in different roles should be represented.
- How individual/controller role differs structurally from caregiver/clinician/institution/researcher roles.
- Whether workspace access should always resolve through a grant row, even for the individual.

### Q3. Capability flags

How should WellBe enforce:

- `can_comment`
- `can_export`
- `can_invite`
- `contribution_becomes_permanent_record`

Required answer:

- Which flags are grant attributes vs workspace attributes vs policy rows.
- Where each flag is enforced: C1, C13 API middleware, C12 audit, C11 correction service, or downstream workspace service.
- Whether comments by clinicians/caregivers are record contributions, external annotations, or pending user-accepted corrections.
- How to prevent recipient contributions from silently mutating the user's permanent record.

### Q4. Institution access and aggregate-only enforcement

How should WellBe support Institution Continuity Intelligence without default individual access?

Required answer:

- How to model aggregate-only grants.
- How to prove individual-level rows cannot be queried under an institution grant.
- Whether institution grants should use a separate policy table, query role, materialized aggregate table, or privacy-preserving cohort layer.
- What consent evidence is required before any aggregate inclusion.
- What must be audited for each aggregate access.

### Q5. Research sandbox and cross-patient governance

How should Research Sandbox access compose with the existing cross-patient opt-in gate?

Required answer:

- Whether `patient_privacy_preferences.capability = cross_patient_analysis` is sufficient or must be extended.
- How protocol-level consent should be represented.
- How opt-out/revocation affects prior cohort inclusion.
- How to prevent clinician or institution users from enabling research/cross-patient access on behalf of individuals.

### Q6. Revocation, expiry, and cache invalidation

How should deep grants expire and revoke?

Required answer:

- Required lifecycle states and transitions.
- Whether post-visit auto-expiry should be a scheduled event, grant field, or workspace policy.
- Which caches must be invalidated synchronously.
- What revocation events must be emitted.
- What access checks must do after revocation but before async workers observe the event.

### Q7. Audit requirements

What audit events must C12 capture for the deep Grant/Role model?

Required answer:

- Minimum event names and payload fields.
- Which actions must be user-visible in audit history.
- How to audit denied access attempts.
- How to audit aggregate/institution access without leaking other users' data.

### Q8. API and contract versioning

What C13 contract shape should expose deep grants safely?

Required answer:

- API resource names and major endpoints.
- Stable DTO fields for Grant, Role, Workspace, WorkspaceAccessDecision.
- Versioning/backward compatibility approach from the existing ShareGrant contract.
- Error codes for denied, expired, revoked, insufficient-scope, and unsafe-contribution paths.

---

## F. Suggested output format from consultant

Please provide:

1. Executive recommendation.
2. Approaches considered.
3. Recommended schema model.
4. Query-time enforcement model.
5. Revocation/expiry model.
6. Audit event list.
7. API contract shape.
8. Example allow/deny scenarios.
9. Trade-offs accepted.
10. Open risks.

The answer will be recorded in `docs/decisions/deep-grant-role-workspace-model.md` under "Research provided" and used to propose a Decision for user approval.

---

## G. Hard constraints for the final decision

The final implementation must not:

- grant clinicians default access,
- grant institutions individual-level access by default,
- allow institutions to enable aggregate analytics without each individual's consent,
- allow researchers to access cohort data without explicit opt-in and governance,
- allow recipients to invite others unless explicitly granted,
- allow comments/contributions to become permanent record without explicit policy,
- rely only on cache TTL for revocation,
- or bypass C12 audit.

