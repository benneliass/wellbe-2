# Decision: Deep Grant/Role model and multi-audience workspace access

**Status:** Approved  
**Date opened:** 2026-05-31  
**Date approved:** 2026-06-01  
**Approved by:** User  
**Jira Spike:** WEL-131  
**Blocks:** WEL-118 (deep Grant/Role), WEL-119 (Clinician workspace), WEL-120 (Shared workspace), WEL-127 (C13 contract)

---

## Question

How should the deep **Grant/Role** model extend the existing Trust & Consent Service (C1) and ShareGrant to support multi-audience workspaces (Individual, Clinician Case Investigation, Shared Health Thread, Institution Continuity, Research Sandbox) without weakening personal-first control?

Specifically:
1. What is the grant scope taxonomy (visit-packet-only / specific-thread / labs+symptoms / wearable-trends-only / full-investigation) and how is least-privilege enforced at query time?
2. How are `can_comment`, `can_export`, `can_invite`, and `contribution_becomes_permanent_record` enforced, and how do recipient contributions enter (or not enter) the append-only record?
3. How is institution access constrained to aggregate-only + consented (no individual-level default), and where is that enforced?
4. How do grants expire/revoke (time-boxed, post-visit auto-expiry) and how is every access audited via C12?

## Context

C17 is the architectural mechanism for the entire multi-audience expansion and extends C1, the highest-blast-radius trust component. A weak grant model would allow institutional overreach or default access — a direct violation of the bible (`platform_identity.md`, `audience-guardrails.mdc`). The grant contract is consumed by every workspace and by C13. C1 is a Done foundation component, so the extension boundary must be decided before the C1 retrofit and before any workspace story.

## Research provided

_Research received: 2026-06-01_ - external consultant report, archived verbatim at [research-inputs/deep-grant-role-workspace-model-research.md](research-inputs/deep-grant-role-workspace-model-research.md) (source `.docx` alongside it).

The report recommends a hybrid ABAC deep-grant model: first-class Role, Workspace, and Grant records; stable scope codes for product/API clarity; versioned policy rows for scope semantics; normalized selector join tables for query enforcement; and JSON only for signed consent snapshots or tightly validated selector DSL.

The core research conclusion is that workspace membership must never be data access. Membership only means a role can be present in a workspace. Every read, search, comment, export, invite, contribution, aggregate query, and research query must resolve through C1 to an active grant or controller entitlement, then through C12 audit before data leaves the service boundary.

The report recommends keeping `consent.share_grants` as the grant lifecycle header, extending it for deep grants, and adding new tables for roles, workspaces, grant scopes, scope policy profiles, grant capabilities, contribution lifecycle, institution aggregate governance, research protocols, and audit. It explicitly rejects "RBAC plus JSON selectors" because that would make clinician/institution defaults too easy to introduce and too hard to prove safe.

Important implementation requirements from the report:

- Role and Workspace are first-class, separate concepts. Role answers "in what capacity is this actor acting"; Workspace answers "in what interface and governance context"; Grant answers "what data/action/purpose/time permission did the individual grant."
- The same human can have multiple role bindings and must choose an active role per session. C1 decisions must never infer access from `actor_id` alone.
- Workspace membership is modeled separately from grants and gives UI presence only. It must not authorize data access.
- The individual/controller access path should use a `controller_entitlement` grant type or equivalent C1 entitlement record, preserving one authorization and audit path without implying the user granted themselves revocable access.
- Scope codes (`visit-packet-only`, `specific-thread`, `labs+symptoms`, `wearable-trends-only`, `full-investigation`) are stable public codes, but their semantics live in versioned `scope_profiles` and normalized `grant_scope_*` selector rows. `full-investigation` must never compile to `WHERE patient_id = ?`; it must compile to explicit allowed resource families plus denied labels/categories.
- C1 should return an `AccessPredicate`, not only `allow=true`, including grant id/version, resource filters, allowed actions, obligations, and expiry. Search, agent retrieval, exports, and downstream services must apply the predicate before data retrieval or prompt construction.
- Capability flags are policy rows. `can_comment`, `can_export`, and `can_invite` are enforced by C1, C13, workspace services, and C12 audit. Contribution permanence is not a boolean; use contribution lifecycle policy such as `external_annotation_only`, `pending_controller_acceptance`, or controller-only direct write.
- Clinician/caregiver comments default to workspace annotations, not personal record mutations. Proposed changes enter C11 as pending contributions and become permanent only after controller acceptance.
- Institution access requires aggregate inclusion consents plus institution aggregate grants over materialized aggregate metrics or approved stored functions. Institution runtime roles must not have privileges on individual-level schemas, and C13 institution endpoints must not accept patient identifiers.
- Research sandbox access requires both the global cross-patient prerequisite and protocol-level consent. Clinicians, institutions, and researchers cannot enable research participation on behalf of individuals.
- Revocation must be synchronous: update grant state, increment authorization epoch, insert revocation log, write C12 audit/outbox, invalidate C1/C13/workspace/search/agent/export/research/institution caches, and deny from authoritative C1 state before async workers observe events.
- C12 audit must capture grant lifecycle, workspace membership/access/search/view, comments, exports, invites, contribution lifecycle, institution aggregate use, research consent/query/export, and policy/security events.
- C13 should expose the deep model through v2 resources or media-type versioning, keep v1 ShareGrant compatible, default all new capabilities false, reject unknown v2 authorization fields, and use explicit authorization error codes.

The report lists trade-offs: added schema/policy complexity; safer but potentially lagging materialized aggregate tables; `full-investigation` less convenient than all-row access; added user review friction for non-controller contributions; nuanced research revocation behavior for already-derived aggregate outputs. It names open risks: incomplete object labeling, agent retrieval leakage, aggregate re-identification/differencing, non-revocable downloaded exports, and narrow grants hiding clinically relevant context.

## Approaches considered

Approach A: Add fields to current `share_grants` only - adds `recipient_role`, `workspace_id`, scope, and booleans directly to `share_grants`. Pro: fastest path for simple shares. Con: too much meaning remains in application code and JSON, and `full-investigation` could be misread as all patient rows. Research recommendation: reject; use `share_grants` as the header only.

Approach B: Role-based workspace access - clinician, caregiver, institution, or researcher workspace membership implies data access by default. Pro: simple mental model and fewer policy joins. Con: violates the canonical constraint that roles never confer data control and no audience receives default access. Research recommendation: reject.

Approach C: Existing `consent_scopes` only - uses the current resource/action scope model for all deep-grant semantics. Pro: reuses a working C1 foundation. Con: does not represent workspaces, actor roles, aggregate-only access, research protocols, contribution lifecycle, or selectors such as wearable trends only. Research recommendation: reject as the full model, but retain it as the atomic scope catalog.

Approach D: Hybrid ABAC grant model - first-class roles and workspaces, explicit grant rows, versioned scope policy profiles, normalized selectors, object labels, query-time policy evaluation, synchronous revocation, and C12 audit. Pro: remains user-controlled, least-privilege, purpose-bound, time-boxed, revocable, auditable, and institution-safe. Con: more tables, policy compilation, object labeling, and integration work. Research recommendation: adopt.

## Decision

Adopt the hybrid ABAC deep-grant model: keep `consent.share_grants` as the lifecycle header, add first-class role binding and workspace tables, add versioned scope profiles plus normalized grant scope selector tables, model capabilities and contribution permanence as policy rows, require every workspace data action to resolve through C1 into an `AccessPredicate` and C12 audit, and enforce institution/research access through aggregate-only/protocol-governed layers with no default individual-level access.

## Trade-offs accepted

If approved, this accepts the following trade-offs from the research:

- More schema and policy complexity in exchange for provable separation between role, workspace presence, grant, scope, and capability.
- Materialized aggregate tables may lag real-time individual data, but they are safer than live institution queries over raw individual records.
- `full-investigation` is intentionally less convenient than "all patient rows"; it remains an allowlist plus denylist, not a wildcard.
- Clinician/caregiver contributions require annotation or controller-acceptance workflows by default, adding friction to prevent silent permanent record mutation.
- Research revocation requires protocol-encoded treatment for already-derived aggregate outputs.

## Implementation notes

If approved, implementation should:

- Add forward migrations for `access`, `workspace`, institution aggregate, and research protocol tables; do not edit applied migrations.
- Extend `backend/packages/c1_consent/` with role binding, workspace membership, grant policy/profile, grant scope selector, capability, contribution policy, and access-decision services.
- Keep existing v1 `ShareGrant` behavior compatible; expose the deep model through v2 contracts in `backend/packages/contracts/src/wellbe_contracts/c1_consent/` and C13 (`WEL-127`).
- Add an `AccessPredicate` / `WorkspaceAccessDecision` DTO with allow/deny, reason code, grant id/version, action, purpose, resource filters, obligations, expiry, and audit id.
- Require active role binding in workspace sessions. C13 should reject workspace requests that do not declare an active role binding.
- Ensure workspace membership alone never authorizes data access.
- Enforce `full-investigation` through explicit resource families and denied labels/categories, never `WHERE patient_id = ?`.
- Add C12 audit event emission for grant lifecycle, workspace access, denied access, export/invite/comment, contribution lifecycle, aggregate queries, and research protocol consent/query events.
- Enforce institution access through aggregate-only tables/functions and separate runtime DB privileges. Add tests proving institution roles cannot select individual-level schemas.
- Enforce research access through both `patient_privacy_preferences.capability = cross_patient_analysis` and protocol-level consent; deny all non-controller attempts to enable research/cross-patient participation.
- Make revocation deny synchronously from authoritative C1 state or synchronously updated revocation index before async workers run.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
