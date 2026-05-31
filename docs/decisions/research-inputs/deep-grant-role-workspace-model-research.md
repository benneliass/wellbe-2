# Deep Grant/Role Workspace Model Research

_Verbatim text extraction from consultant .docx received 2026-06-01._

C1 Deep Grant/Role Workspace Model — Research Analysis and Results

Prepared for: WellBe external research consultant workflow
Date: 2026-06-01
Owner: Ben Elias, individual data controller / product owner
Related Jira Spike: WEL-131
Decision record target: docs/decisions/deep-grant-role-workspace-model.md

This file preserves the full research analysis and results produced in the chat response. No sections, schema blocks, examples, trade-offs, risks, or citations from the response have been intentionally removed.

1. Executive recommendation

Adopt a hybrid ABAC deep-grant model: first-class Role, Workspace, and Grant records; stable scope codes for product/API clarity; versioned policy rows for scope semantics; normalized selector join tables for query enforcement; and JSON only for signed consent snapshots or tightly validated selector DSL. This fits the WellBe constraint that a role never confers data control, while allowing C1 to evaluate subject attributes, object labels, requested action, purpose, workspace, time, and environment in one decision. NIST’s ABAC model is the closest public access-control reference: authorization is determined by evaluating subject, object, operation, and environment attributes against policy. Source: https://csrc.nist.gov/pubs/sp/800/162/upd2/final

The most important design choice is: workspace membership must never be data access. Membership only means “this role can be present in this workspace.” Every read, search, comment, export, invite, contribution, aggregate query, and research query must resolve through C1 to an active grant or controller entitlement, then through C12 audit before data leaves the service boundary. FHIR Consent is a useful analogue because it supports computable consent rules, including actor, action, purpose, data reference, security label, and period; FHIR Security Labels are useful for object-side enforcement because access decisions can use labels plus provenance and resource metadata. Source: https://fhir.hl7.org/fhir/consent.html

The recommended decision is:

Keep consent.share_grants as the grant header, extend it for deep grants, and add new tables for roles, workspaces, grant scopes, scope policy profiles, grant capabilities, contribution lifecycle, institution aggregate governance, research protocols, and C12 audit. Do not implement this as “RBAC plus JSON selectors.” That would make clinician/institution defaults too easy to introduce and too hard to prove safe.

2. Approaches considered

Approach A — Add fields to current share_grants only

This is the fastest path, but it is not safe enough. Adding recipient_role, workspace_id, scope, and booleans directly to share_grants would work for simple shares, but it would leave too much meaning inside application code and JSON. It would also make full-investigation dangerous, because a future developer could accidentally interpret it as “all rows for this patient.”

Reject. Use share_grants as the header only.

Approach B — Role-based workspace access

This would make clinician, caregiver, institution, or researcher workspace membership imply some access by default.

Reject. It violates the canonical constraint that roles never confer data control and no audience receives default access.

Approach C — Existing consent_scopes only

The existing model is a good base for resource/action scopes, but it does not represent workspaces, actor roles, aggregate-only access, research protocols, contribution lifecycle, or complex selectors like “wearable trends only.”

Reject as the full model, but retain it as the atomic scope catalog.

Approach D — Hybrid ABAC grant model

Use first-class roles and workspaces, explicit grant rows, versioned scope policy profiles, normalized selectors, object labels, query-time policy evaluation, synchronous revocation, and C12 audit.

Recommend. It is the only approach that can remain user-controlled, least-privilege, purpose-bound, time-boxed, revocable, auditable, and institution-safe.

3. Recommended schema model

3.1 Core C17/C1 tables

Use separate tables, even if implemented inside the existing C1 package at first.

access.role_types (
  role_type text primary key, -- individual_controller, caregiver, clinician, care_team, institution, researcher
  description text,
  may_receive_grant_types text[] not null,
  may_control_data boolean not null default false
);

Only individual_controller should have may_control_data = true.

access.role_bindings (
  role_binding_id uuid primary key,
  actor_id uuid not null,
  role_type text not null references access.role_types(role_type),
  subject_user_id uuid null,       -- set for individual_controller only
  organization_id uuid null,       -- set for clinician/care_team/institution/researcher where relevant
  credential_ref text null,
  status text not null,            -- pending, active, suspended, revoked
  verified_at timestamptz null,
  created_at timestamptz not null
);

The same human can have multiple role_bindings. A physician who is also a parent caregiver must have two role bindings and must choose the active role per session. C1 decisions should never infer access from actor_id alone.

workspace.workspaces (
  workspace_id uuid primary key,
  workspace_type text not null, -- individual, clinician_case_investigation, shared_health_thread, institution_continuity, research_sandbox
  controller_model text not null, -- single_individual, multi_individual_consent_derived, aggregate_only
  subject_user_id uuid null,      -- present for single-individual workspaces
  created_by_role_binding_id uuid not null,
  policy_profile_id uuid not null,
  default_expiry_policy jsonb not null default '{}',
  status text not null,           -- active, archived, suspended
  created_at timestamptz not null
);

workspace.workspace_memberships (
  membership_id uuid primary key,
  workspace_id uuid not null references workspace.workspaces(workspace_id),
  role_binding_id uuid not null references access.role_bindings(role_binding_id),
  status text not null, -- invited, active, suspended, removed
  invited_by_role_binding_id uuid null,
  created_at timestamptz not null,
  unique (workspace_id, role_binding_id)
);

Membership gives UI presence only. It must not authorize data access.

3.2 Extend current consent.share_grants

Keep share_grants as the canonical grant lifecycle table and add deep-grant fields:

consent.share_grants (
  grant_id uuid primary key,
  grant_type text not null, -- controller_entitlement, delegated_individual, workspace_share, institution_aggregate, research_sandbox
  grantor_user_id uuid not null,
  recipient_role_binding_id uuid null,
  workspace_id uuid null,
  status text not null, -- draft, pending, active, suspended, expired, revoked, superseded, rejected
  purpose_code text not null,
  effective_at timestamptz not null,
  expires_at timestamptz null,
  revoked_at timestamptz null,
  revoked_by_role_binding_id uuid null,
  revocation_reason text null,
  consent_snapshot_hash text not null,
  policy_version_id uuid not null,
  authz_epoch bigint not null default 1,
  aggregate_only boolean not null default false,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

For the individual’s own workspace access, use a non-share grant_type = controller_entitlement row or equivalent C1 entitlement record. This keeps the access decision path and audit uniform without implying that the user “granted themselves” revocable access.

3.3 Scope policy tables

Use public scope codes, but put semantics in versioned policy rows.

consent.scope_profiles (
  scope_profile_id uuid primary key,
  scope_code text not null, -- visit-packet-only, specific-thread, labs+symptoms, wearable-trends-only, full-investigation
  version int not null,
  description text not null,
  allowed_workspace_types text[] not null,
  allowed_role_types text[] not null,
  requires_explicit_resource_set boolean not null default false,
  includes_raw_data boolean not null default false,
  default_export_allowed boolean not null default false,
  status text not null,
  unique (scope_code, version)
);

consent.scope_profile_items (
  scope_profile_item_id uuid primary key,
  scope_profile_id uuid not null references consent.scope_profiles(scope_profile_id),
  consent_scope_id uuid not null references consent.consent_scopes(scope_id),
  resource_type text not null,
  data_category text not null,
  action text not null,
  include_security_labels text[] not null default '{}',
  exclude_security_labels text[] not null default '{}',
  requires_selector_type text null -- packet_id, thread_id, category_window, derived_view, aggregate_metric
);

This composes directly with the existing consent_scopes table: consent_scopes remains the atomic resource/action/data-category vocabulary, while scope_profiles group those atoms into product-level scope templates.

3.4 Grant scope instances

A grant should not store only scope = 'labs+symptoms'. It must store the profile version and concrete selectors.

consent.grant_scope_instances (
  grant_scope_id uuid primary key,
  grant_id uuid not null references consent.share_grants(grant_id),
  scope_profile_id uuid not null references consent.scope_profiles(scope_profile_id),
  selector_type text not null, -- packet_snapshot, thread, category_time_window, derived_view, full_investigation_policy, aggregate_cohort, research_protocol
  selector_hash text not null,
  time_start timestamptz null,
  time_end timestamptz null,
  raw_data_allowed boolean not null default false
);

consent.grant_scope_resources (
  grant_scope_resource_id uuid primary key,
  grant_scope_id uuid not null references consent.grant_scope_instances(grant_scope_id),
  resource_type text not null,
  resource_id uuid not null
);

consent.grant_scope_categories (
  grant_scope_category_id uuid primary key,
  grant_scope_id uuid not null references consent.grant_scope_instances(grant_scope_id),
  data_category text not null
);

consent.grant_scope_labels (
  grant_scope_label_id uuid primary key,
  grant_scope_id uuid not null references consent.grant_scope_instances(grant_scope_id),
  label_type text not null, -- include, exclude
  security_label text not null
);

JSON selectors may be stored in metadata or selector_payload, but only after validation against a WellBe-owned selector schema. Never evaluate arbitrary JSON as SQL. The enforcement predicates should be compiled into normalized rows or precomputed resource sets.

3.5 Capability model

Represent capabilities as policy rows, not just booleans, but expose stable booleans in DTOs.

consent.grant_capabilities (
  grant_capability_id uuid primary key,
  grant_id uuid not null references consent.share_grants(grant_id),
  capability text not null, -- read, comment, export, invite, contribute, view_aggregate, run_analysis
  allowed boolean not null,
  constraints jsonb not null default '{}',
  requires_controller_acceptance boolean not null default false,
  unique (grant_id, capability)
);

For contribution permanence, do not use a raw boolean as the enforcement primitive. Use a lifecycle policy:

consent.grant_contribution_policies (
  grant_id uuid primary key references consent.share_grants(grant_id),
  contribution_mode text not null,
  -- external_annotation_only,
  -- pending_controller_acceptance,
  -- direct_write_allowed_for_controller_only
  allowed_target_categories text[] not null default '{}',
  requires_c11_review boolean not null default true
);

4. Q1 — Grant scope taxonomy and least-privilege enforcement

Recommended scope taxonomy

Scope code

Enforcement meaning

visit-packet-only

Read-only access to a precomputed packet snapshot or immutable packet resource set. Does not imply access to source memories or raw documents unless each source is explicitly included in the packet resource set.

specific-thread

Access only to a named health thread and explicitly attached artifacts. No sibling threads, global memory search, or underlying raw records unless attached and selected.

labs+symptoms

Access to lab observations, diagnostic reports if explicitly included, symptom logs, and derived summaries in a defined time window. Excludes notes, private memories, raw wearable streams, and unrelated documents by default.

wearable-trends-only

Access only to derived trend tables or trend artifacts, such as weekly sleep/HRV/activity summaries. Excludes raw wearable time series.

full-investigation

Broadest individual-level investigation scope, but still policy-bounded. It must be an enumerated list of included categories and excluded security labels, not a wildcard. Raw memories, private journals, sensitive labels, hidden items, and future unknown categories remain excluded unless the user explicitly adds them.

Schema pattern

Use a hybrid:

Stable scope code in scope_profiles.scope_code; versioned policy rows in scope_profile_items; normalized selector rows in grant_scope_*; consent_scopes as the atomic capability vocabulary; JSON only for signed consent snapshots or validated selector payloads.

This mirrors FHIR Consent’s distinction between consent metadata, computable rules, actor/action/purpose/data/period, and references to source consent evidence. Source: https://fhir.hl7.org/fhir/consent.html

Query-time enforcement

Every data query should flow:

C13 request
  -> active role binding
  -> workspace membership check
  -> C1 grant lookup
  -> grant status/time/purpose/capability check
  -> scope profile expansion
  -> object label/category/resource selector check
  -> C12 audit outbox write
  -> authorized query/view/search execution

At query time, C1 should return an AccessPredicate, not just allow=true. Example:

{
  "allow": true,
  "grant_id": "g_123",
  "grant_version": 7,
  "allowed_actions": ["read", "comment"],
  "resource_filter": {
    "resource_ids": ["packet_456"],
    "data_categories": ["visit_packet"],
    "exclude_security_labels": ["private_memory", "hidden", "raw_wearable"]
  },
  "obligations": ["no_export", "audit_each_view"],
  "expires_at": "2026-06-15T23:59:59Z"
}

Downstream services must use that predicate through authorized views, RLS, stored functions, or a C1 decision token that is introspected before execution. Search and agent retrieval must also filter by grant resource IDs, categories, and labels before prompt construction. A scoped clinician workspace must not use the individual’s full memory context in the background.

Preventing accidental broad access

full-investigation must never compile to WHERE patient_id = ?. It should compile to an allowlist of resource families and a denylist of security labels. Unknown future data categories should be denied until a new scope profile version includes them. FHIR Security Labels are a useful precedent here because they attach privacy/security metadata to resources and are intended to be used by access-control decision engines. Source: https://build.fhir.org/security-labels.html

5. Q2 — Role and workspace model

Role and Workspace should be first-class tables

Yes. Role and Workspace should be first-class because they answer different questions:

Role: in what capacity is this actor acting?

Workspace: in what interface and governance context is the actor operating?

Grant: what data/action/purpose/time permission has the individual granted?

Do not collapse these into share_grants.grantee_type. That would make it impossible to distinguish the same person acting as caregiver, clinician, researcher, or individual controller.

Workspace membership

Model membership separately from grants. A user may be a workspace member and still have no data access. This supports safe invite flows, pending grants, and audit of denied access attempts.

actor -> role_binding -> workspace_membership -> grant -> access decision

Same person in different roles

Use separate role_bindings:

actor_id = alice
  role_binding_1 = caregiver for Ben
  role_binding_2 = clinician at Clinic A
  role_binding_3 = researcher at University B

The session must carry one active role_binding_id. C13 should reject requests that do not declare a role binding for workspace actions.

Individual/controller role

The individual/controller role is structurally different:

It is bound to subject_user_id.

It can create, accept, revoke, and audit grants.

It can approve or reject proposed contributions.

It is the only ordinary role that can create permanent personal record changes without another user’s acceptance flow.

Caregiver, clinician, care team, institution, and researcher roles are recipient roles. They may be offered grants, but they never become data controllers.

Should individual access resolve through a grant row?

Yes, but model it as grant_type = controller_entitlement, not as a revocable share grant. This gives uniform C1/C12 enforcement and audit while preserving the product truth that the individual is the controller.

6. Q3 — Capability flags

Recommended enforcement split

Capability

Stored as

Enforced by

can_comment

grant_capabilities plus workspace policy max

C1 decision, C13 middleware, workspace service, C12 audit

can_export

grant_capabilities with export constraints

C1, C13 export endpoint, C12, downstream export worker

can_invite

grant_capabilities plus role/workspace policy

C1, C13 invite endpoint, workspace membership service, C12

contribution_becomes_permanent_record

Do not enforce as simple boolean; use grant_contribution_policies.contribution_mode

C1, C11 correction/contribution service, C12, personal record write service

Comments and contributions

Clinician and caregiver comments should default to external workspace annotations, not personal record mutations. A comment may be linked to a thread, visit packet, lab result, or symptom timeline, but it should live in a workspace annotation table with provenance and should not silently enter the permanent memory.

A clinician/caregiver correction should become a proposed record contribution:

workspace.workspace_annotations (
  annotation_id uuid primary key,
  workspace_id uuid not null,
  grant_id uuid not null,
  author_role_binding_id uuid not null,
  target_resource_type text not null,
  target_resource_id uuid not null,
  body text not null,
  status text not null, -- active, hidden, deleted
  created_at timestamptz not null
);

c11.proposed_record_contributions (
  contribution_id uuid primary key,
  workspace_id uuid not null,
  grant_id uuid not null,
  proposed_by_role_binding_id uuid not null,
  target_record_type text not null,
  target_record_id uuid null,
  proposed_change jsonb not null,
  status text not null, -- pending_controller_review, accepted, rejected, withdrawn
  reviewed_by_role_binding_id uuid null,
  reviewed_at timestamptz null,
  provenance_id uuid null
);

When accepted, C11 creates a versioned permanent record update with provenance. FHIR Provenance is the right public analogue: it records the entities and agents involved in creating, revising, deleting, or signing a resource, while AuditEvent records access/use events. Source: https://build.fhir.org/provenance.html

Preventing silent permanent mutation

Enforce with three boundaries:

Database: non-controller role sessions have no direct write path to permanent personal memory tables.

Service: C13 routes all non-controller contribution requests through C11.

Policy: C1 denies contribution_mode = direct_write unless the active role is individual_controller.

Audit: C12 records contribution.proposed, contribution.accepted, contribution.rejected, and personal_record.updated.

7. Q4 — Institution access and aggregate-only enforcement

Model aggregate-only grants separately

Institution continuity should require two layers:

Individual aggregate inclusion consent
The individual consents to be included in a specific aggregate program, purpose, data category set, cohort policy, and time window.

Institution aggregate access grant
The institution receives access only to materialized aggregate metrics or privacy-preserving query functions, not source rows.

institution.aggregate_inclusion_consents (
  inclusion_consent_id uuid primary key,
  user_id uuid not null,
  institution_id uuid not null,
  purpose_code text not null,
  data_categories text[] not null,
  cohort_policy_id uuid not null,
  effective_at timestamptz not null,
  expires_at timestamptz null,
  revoked_at timestamptz null,
  consent_snapshot_hash text not null,
  status text not null
);

institution.aggregate_grants (
  aggregate_grant_id uuid primary key,
  grant_id uuid not null references consent.share_grants(grant_id),
  institution_id uuid not null,
  cohort_definition_id uuid not null,
  metric_set_id uuid not null,
  min_cohort_size int not null,
  privacy_mechanism text not null, -- k_threshold, suppression, differential_privacy, expert_reviewed
  export_allowed boolean not null default false
);

institution.materialized_aggregate_metrics (
  metric_result_id uuid primary key,
  cohort_definition_id uuid not null,
  metric_code text not null,
  time_bucket tstzrange not null,
  consented_subject_count int not null,
  value jsonb not null,
  privacy_mechanism text not null,
  generated_at timestamptz not null
);

Proving individual rows cannot be queried

Use a hard data-plane separation:

Institution runtime DB role has SELECT only on institution.materialized_aggregate_metrics or approved stored functions.

Institution runtime DB role has no privileges on personal memory, clinical event, note, lab, wearable raw, or thread tables.

RLS defense-in-depth denies raw patient schemas for institution roles.

C13 institution endpoints accept only aggregate metric/cohort identifiers, not patient identifiers.

CI migration tests assert that the institution DB role cannot select from individual-level schemas.

C12 audits every aggregate query.

HHS de-identification guidance is a useful floor: information is not individually identifiable only if it does not identify an individual and there is no reasonable basis to believe it can be used to identify one; HHS also distinguishes de-identification methods such as Expert Determination and Safe Harbor, and warns that identifiers in free text must be removed just as in structured fields. Source: https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html

Recommended aggregate layer

Use a separate materialized aggregate/cohort layer plus a separate institution DB role. Do not let institution grants run live SQL over raw rows, even with RLS, because aggregate filters can become drill-down or differencing attacks.

Required protections:

minimum cohort size,

cell suppression,

no patient list export,

no free-text group-by,

query budget or differential privacy for repeated analytics,

no drill-down below threshold,

aggregate result lineage to consented inclusion rows,

revocation-aware cohort refresh.

NIST’s privacy-enhancing cryptography work is also relevant for future phases if WellBe needs secure multi-party computation, private set intersection, zero-knowledge proofs, or homomorphic encryption across institutions, but the first implementation should be materialized aggregate tables plus strict policy controls. Source: https://csrc.nist.gov/Projects/pec

Consent evidence required

Before aggregate inclusion, C1 must have active evidence of:

individual/controller action,

institution identity,

purpose,

data categories,

cohort policy,

time window,

withdrawal/revocation effect,

consent snapshot hash,

policy version,

no revocation.

Distribution by an institution must not count as consent.

Aggregate audit

Each aggregate access should audit:

institution ID,

human actor role binding,

workspace ID,

aggregate grant ID,

cohort definition ID and hash,

metric set,

purpose,

query parameters,

result time bucket,

consented subject count,

minimum threshold,

privacy mechanism,

export status,

decision ID,

audit event ID.

Do not audit or display other users’ identities in an individual’s audit history.

8. Q5 — Research sandbox and cross-patient governance

patient_privacy_preferences.capability = cross_patient_analysis is necessary but not sufficient. Treat it as a global prerequisite gate, not as research consent.

Add protocol-level governance:

research.protocols (
  protocol_id uuid primary key,
  title text not null,
  sponsor_org_id uuid not null,
  governance_status text not null, -- draft, approved, suspended, retired
  review_body_ref text null,       -- IRB/privacy board/internal governance
  purpose_code text not null,
  data_categories text[] not null,
  allowed_transformations text[] not null,
  retention_policy jsonb not null,
  export_policy jsonb not null,
  consent_form_hash text not null,
  created_at timestamptz not null
);

research.protocol_consents (
  protocol_consent_id uuid primary key,
  protocol_id uuid not null references research.protocols(protocol_id),
  user_id uuid not null,
  status text not null, -- active, revoked, expired
  effective_at timestamptz not null,
  expires_at timestamptz null,
  revoked_at timestamptz null,
  revocation_effect text not null, -- future_only, remove_from_active_cohorts, purge_identifiable_sandbox_rows
  consent_snapshot_hash text not null,
  signed_by_role_binding_id uuid not null
);

research.sandbox_grants (
  sandbox_grant_id uuid primary key,
  grant_id uuid not null references consent.share_grants(grant_id),
  protocol_id uuid not null,
  sandbox_workspace_id uuid not null,
  researcher_role_binding_id uuid not null,
  allowed_queries jsonb not null,
  export_allowed boolean not null default false
);

The Common Rule requires informed consent before involving a human subject in covered research unless an exception or waiver applies, and it permits broad consent only for specified storage, maintenance, and secondary research uses of identifiable private information or biospecimens. Source: https://www.hhs.gov/ohrp/regulations-and-policy/regulations/45-cfr-46/index.html

Revocation and prior cohort inclusion

When a user revokes research consent:

stop new collection and new identifiable inclusion immediately,

remove from active cohort refreshes,

invalidate sandbox caches,

block future research queries that would include the subject,

apply the protocol’s disclosed revocation effect to already-derived outputs.

OHRP guidance recognizes that withdrawal handling should be planned and described in the protocol/consent materials, and that use of already collected data may depend on the protocol and regulatory context. WellBe should encode this explicitly rather than leave it to ad hoc research operations. Source: https://www.hhs.gov/ohrp/sites/default/files/ohrp/policy/subjectwithdrawal.pdf

Preventing clinicians/institutions from enabling research access

Only the individual/controller session can set cross-patient research preferences or protocol consent. C13 should reject attempts from clinician, care team, institution, or researcher role bindings with:

WB_AUTHZ_ROLE_NOT_ALLOWED

WB_RESEARCH_CONTROLLER_CONSENT_REQUIRED

A caregiver should also be denied unless WellBe later implements a formal legal representative model.

9. Q6 — Revocation, expiry, and cache invalidation

Lifecycle states

Recommended states:

draft
requested
pending
active
suspended
expired
revoked
superseded
rejected
cancelled

Allowed transitions:

draft -> requested -> pending -> active
pending -> rejected | cancelled
active -> suspended -> active
active -> expired
active -> revoked
active -> superseded
pending -> expired
suspended -> revoked | expired

Expiry model

Post-visit auto-expiry should be represented as both:

a workspace policy, such as visit_end + 72h, and

a concrete expires_at field on the grant at activation time.

A scheduled job should update state to expired and emit events, but access checks must deny if now() >= expires_at even before the scheduled job runs.

Synchronous revocation

On revoke, C1 must synchronously:

update share_grants.status = revoked,

set revoked_at, revoked_by, revocation_reason,

increment authz_epoch,

insert revocation_log,

write C12 audit/outbox event,

invalidate C1 decision caches,

invalidate workspace/search/agent/export caches,

emit revocation events.

Async workers can clean up snapshots, exports, search sessions, and materialized membership, but async delivery must not be required for denial.

Caches to invalidate

At minimum:

C1 grant decision cache,

C1 scope/resource-set cache,

C13 token/introspection cache,

workspace membership effective-access cache,

search/vector retrieval filters,

agent memory context cache,

visit packet signed links,

export jobs and download URLs,

annotation/contribution permission cache,

research sandbox cohort cache,

institution aggregate cohort cache,

population-analysis authorization cache.

Required events

share_grant.created
share_grant.activated
share_grant.suspended
share_grant.expired
share_grant.revoked
share_grant.superseded
grant_scope.changed
grant_capability.changed
workspace_access.cache_invalidated
export_token.revoked
research_protocol_consent.revoked
research_cohort_membership.removed
institution_aggregate_inclusion.revoked

After revocation but before async workers observe events, every access check must hit the authoritative C1 state or a synchronously updated revocation index. Do not rely on cache TTL.

10. Q7 — Audit requirements

FHIR AuditEvent is a strong model for C12: it covers security-relevant events such as access-control decisions, policy changes, and data manipulation that exposes data, and it records who, what, where, when, and why. It also notes that audit records may inform patients about uses of their data but must themselves be access-controlled because they are sensitive. Source: https://build.fhir.org/auditevent.html

Minimum C12 event names

Grant lifecycle:

grant.requested
grant.created
grant.activated
grant.updated
grant.suspended
grant.expired
grant.revoked
grant.superseded
grant.denied

Workspace:

workspace.created
workspace.archived
workspace.member.invited
workspace.member.added
workspace.member.removed
workspace.access.allowed
workspace.access.denied
workspace.search.performed
workspace.resource.viewed

Capabilities:

comment.created
comment.deleted
export.requested
export.generated
export.downloaded
export.denied
invite.requested
invite.created
invite.denied

Contribution lifecycle:

contribution.proposed
contribution.accepted
contribution.rejected
contribution.withdrawn
personal_record.updated_from_contribution

Institution aggregate:

aggregate_inclusion.consent_created
aggregate_inclusion.consent_revoked
aggregate_cohort.built
aggregate_query.allowed
aggregate_query.denied
aggregate_export.generated

Research:

research_preference.updated
research_protocol.created
research_protocol.approved
research_protocol_consent.created
research_protocol_consent.revoked
research_cohort.included
research_cohort.removed
research_query.allowed
research_query.denied
research_export.generated

Policy/security:

policy_profile.changed
grant_scope_policy.changed
authz_cache.invalidated
unsafe_contribution.denied

Minimum payload fields

{
  "event_id": "uuid",
  "event_name": "workspace.resource.viewed",
  "occurred_at": "timestamp",
  "actor_id": "uuid",
  "actor_role_binding_id": "uuid",
  "actor_role_type": "clinician",
  "actor_org_id": "uuid|null",
  "controller_user_id": "uuid|null",
  "workspace_id": "uuid",
  "workspace_type": "clinician_case_investigation",
  "grant_id": "uuid|null",
  "grant_version": 7,
  "purpose_code": "care_investigation",
  "scope_codes": ["labs+symptoms"],
  "capability": "read",
  "resource_type": "lab_result",
  "resource_id_hash": "hash|null",
  "data_categories": ["labs"],
  "decision": "allow|deny",
  "reason_code": "ok|grant_revoked|insufficient_scope|...",
  "policy_version_id": "uuid",
  "request_id": "uuid",
  "session_id": "uuid",
  "client_id": "string",
  "ip_hash": "hash",
  "user_agent_hash": "hash",
  "result_count": 1,
  "export_id": "uuid|null",
  "cohort_definition_hash": "hash|null",
  "privacy_threshold": "integer|null",
  "audit_visibility": "user_visible|security_only|admin_only"
}

User-visible audit history

User-visible:

grant creation, activation, expiry, revocation,

workspace membership changes,

views/searches of personal data,

exports/downloads,

comments,

invitations,

contribution proposals and accepted record changes,

research consent/inclusion/removal,

institution aggregate use summaries.

Security/admin-only:

internal cache invalidations,

service-to-service retries,

raw policy compiler events,

low-level token introspection events.

Denied access attempts

Denied attempts should be audited with the attempted action, actor, role, workspace, grant if any, safe resource selector hash, and denial reason. The response to the caller should avoid confirming whether a hidden resource exists.

Aggregate audit without leaking other users’ data

For institutions, C12 should log cohort ID/hash, metric ID, result count bucket, threshold, and privacy mechanism. It should not log or display other individuals’ identifiers. In an individual’s audit view, show: “Institution X included your consented data in aggregate metric Y under program Z,” not who else was included.

11. Q8 — API and contract versioning

OAuth Rich Authorization Requests are a useful shape reference because they support structured authorization details rather than flat scopes, can coexist with legacy scopes during migration, and require invalid unknown authorization-detail types or fields to be rejected. Source: https://www.rfc-editor.org/rfc/rfc9396.html UMA is also conceptually relevant because it centers resource-owner-controlled sharing policies across resource servers and clients. Source: https://docs.kantarainitiative.org/uma/ed/uma-core-2.0-02.html

Recommended API resources

Use /v2 or a media-type version. Do not silently extend v1 ShareGrant semantics.

GET    /v2/role-bindings
POST   /v2/role-bindings/{id}/activate-session-role

POST   /v2/workspaces
GET    /v2/workspaces/{workspace_id}
GET    /v2/workspaces/{workspace_id}/members
POST   /v2/workspaces/{workspace_id}/members/invitations
DELETE /v2/workspaces/{workspace_id}/members/{membership_id}

POST   /v2/grants
GET    /v2/grants/{grant_id}
POST   /v2/grants/{grant_id}/activate
POST   /v2/grants/{grant_id}/revoke
POST   /v2/grants/{grant_id}/supersede
POST   /v2/grants/{grant_id}/evaluate

POST   /v2/workspace-access-decisions
POST   /v2/workspaces/{workspace_id}/comments
POST   /v2/workspaces/{workspace_id}/exports
POST   /v2/contributions
POST   /v2/contributions/{contribution_id}/accept
POST   /v2/contributions/{contribution_id}/reject

POST   /v2/institution/aggregate-grants
POST   /v2/institution/aggregate-queries
GET    /v2/institution/aggregate-queries/{query_id}

POST   /v2/research/protocols
POST   /v2/research/protocols/{protocol_id}/consents
POST   /v2/research/sandboxes/{workspace_id}/queries

GET    /v2/audit/events

Stable DTO: Grant

{
  "id": "uuid",
  "schema_version": "2.0",
  "grant_type": "workspace_share",
  "status": "active",
  "grantor_user_id": "uuid",
  "recipient": {
    "actor_id": "uuid",
    "role_binding_id": "uuid",
    "role_type": "clinician",
    "organization_id": "uuid"
  },
  "workspace": {
    "workspace_id": "uuid",
    "workspace_type": "clinician_case_investigation"
  },
  "purpose_code": "care_investigation",
  "scope": [
    {
      "scope_code": "labs+symptoms",
      "scope_profile_version": 3,
      "selector_type": "category_time_window",
      "time_start": "2025-01-01T00:00:00Z",
      "time_end": "2026-06-01T00:00:00Z",
      "data_categories": ["labs", "symptoms"],
      "raw_data_allowed": false
    }
  ],
  "capabilities": {
    "can_read": true,
    "can_comment": true,
    "can_export": false,
    "can_invite": false
  },
  "contribution_policy": {
    "mode": "pending_controller_acceptance",
    "requires_c11_review": true
  },
  "aggregate_only": false,
  "effective_at": "timestamp",
  "expires_at": "timestamp",
  "revoked_at": null,
  "policy_version_id": "uuid",
  "consent_snapshot_hash": "hash",
  "authz_epoch": 7
}

Stable DTO: Role

{
  "role_binding_id": "uuid",
  "actor_id": "uuid",
  "role_type": "clinician",
  "subject_user_id": null,
  "organization_id": "uuid",
  "credential_ref": "npi:...",
  "status": "active",
  "verified_at": "timestamp",
  "may_receive_grant_types": ["workspace_share"]
}

Stable DTO: Workspace

{
  "workspace_id": "uuid",
  "workspace_type": "clinician_case_investigation",
  "controller_model": "single_individual",
  "subject_user_id": "uuid",
  "status": "active",
  "policy_profile_id": "uuid",
  "default_expiry_policy": {
    "type": "visit_end_plus_duration",
    "duration": "P7D"
  },
  "created_by_role_binding_id": "uuid",
  "created_at": "timestamp"
}

Stable DTO: WorkspaceAccessDecision

{
  "decision_id": "uuid",
  "allow": true,
  "reason_code": "ok",
  "workspace_id": "uuid",
  "role_binding_id": "uuid",
  "grant_id": "uuid",
  "grant_version": 7,
  "action": "read",
  "purpose_code": "care_investigation",
  "effective_scope": {
    "scope_codes": ["labs+symptoms"],
    "data_categories": ["labs", "symptoms"],
    "resource_ids": [],
    "exclude_security_labels": ["private_memory", "raw_wearable"]
  },
  "obligations": ["no_export", "audit_each_view"],
  "expires_at": "timestamp",
  "audit_event_id": "uuid"
}

Backward compatibility

Keep existing v1 ShareGrant endpoints and contract.

Introduce v2 Grant as the deep model.

Migrate v1 grants into v2 internally with scope_code = legacy-resource-selector.

Default all new capabilities to false unless explicitly granted.

Do not let v1 clients create institution, research, permanent contribution, invite, or export grants.

Require new v2 clients to send schema_version, scope_profile_version, and explicit capabilities.

Reject unknown v2 fields in authorization details rather than ignoring them.

Error codes

WB_AUTHZ_DENIED
WB_AUTHZ_GRANT_PENDING
WB_AUTHZ_GRANT_EXPIRED
WB_AUTHZ_GRANT_REVOKED
WB_AUTHZ_INSUFFICIENT_SCOPE
WB_AUTHZ_INSUFFICIENT_CAPABILITY
WB_AUTHZ_PURPOSE_MISMATCH
WB_AUTHZ_ROLE_NOT_ALLOWED
WB_AUTHZ_WORKSPACE_MEMBERSHIP_REQUIRED
WB_AUTHZ_RESOURCE_OUT_OF_SCOPE
WB_AUTHZ_EXPORT_NOT_ALLOWED
WB_AUTHZ_INVITE_NOT_ALLOWED
WB_AUTHZ_AGGREGATE_ONLY_GRANT
WB_AUTHZ_PRIVACY_THRESHOLD_NOT_MET
WB_AUTHZ_COHORT_CONSENT_REQUIRED
WB_AUTHZ_CROSS_PATIENT_OPT_IN_REQUIRED
WB_AUTHZ_PROTOCOL_CONSENT_REQUIRED
WB_AUTHZ_UNSAFE_CONTRIBUTION
WB_AUTHZ_CONTRIBUTION_REQUIRES_CONTROLLER_ACCEPTANCE
WB_AUTHZ_POLICY_VERSION_STALE
WB_AUTHZ_AUDIT_REQUIRED_UNAVAILABLE

Error responses should include decision_id and audit_event_id when available, but should not reveal hidden resource existence.

12. Example allow/deny scenarios

Visit packet

Allowed: A clinician with an active visit-packet-only grant opens the packet snapshot before expires_at.

Denied: The same clinician queries the patient’s raw memory store to “see context behind the packet.” Reason: WB_AUTHZ_RESOURCE_OUT_OF_SCOPE.

Specific thread

Allowed: A caregiver with specific-thread and can_comment=true comments on the “migraine investigation” thread.

Denied: The caregiver opens a sibling “fertility” thread. Reason: WB_AUTHZ_INSUFFICIENT_SCOPE.

Labs + symptoms

Allowed: A clinician reads CBC labs and symptom logs within the grant’s time range.

Denied: The clinician reads private journal entries mentioning symptoms. Reason: WB_AUTHZ_RESOURCE_OUT_OF_SCOPE, because narrative memory is not in the labs+symptoms resource family.

Wearable trends only

Allowed: A care team sees weekly sleep trend summaries.

Denied: The care team downloads minute-level heart-rate samples. Reason: WB_AUTHZ_INSUFFICIENT_SCOPE.

Full investigation

Allowed: A clinician reads investigation timeline, accepted documents, labs, symptom threads, and summaries covered by the scope profile.

Denied: The clinician reads hidden memories, private notes, or future data categories not enumerated in the profile. Reason: WB_AUTHZ_INSUFFICIENT_SCOPE.

Export

Denied: A clinician with read/comment access clicks export. Reason: WB_AUTHZ_EXPORT_NOT_ALLOWED.

Invite

Denied: A caregiver invites another family member without can_invite=true. Reason: WB_AUTHZ_INVITE_NOT_ALLOWED.

Contribution permanence

Allowed: A clinician proposes “add diagnosis discussion note” as a correction.

Denied: The proposal directly mutates the permanent personal record. Reason: WB_AUTHZ_CONTRIBUTION_REQUIRES_CONTROLLER_ACCEPTANCE.

Institution continuity

Allowed: Institution views “average time-to-follow-up for consented cohort, n=84.”

Denied: Institution asks for the patient list behind the metric. Reason: WB_AUTHZ_AGGREGATE_ONLY_GRANT.

Denied: Institution runs a filter that produces n=3 where the threshold is 20. Reason: WB_AUTHZ_PRIVACY_THRESHOLD_NOT_MET.

Research sandbox

Allowed: Researcher runs an approved protocol query over users who have both cross-patient opt-in and protocol consent.

Denied: Researcher includes a user who has global cross-patient opt-out. Reason: WB_AUTHZ_CROSS_PATIENT_OPT_IN_REQUIRED.

Denied: Institution admin enables research participation for employees/patients. Reason: WB_RESEARCH_CONTROLLER_CONSENT_REQUIRED.

13. Trade-offs accepted

This model adds tables and policy complexity, but it creates provable separation between role, workspace presence, grant, scope, and capability.

Materialized aggregate tables may lag real-time data, but they are safer than live institution queries over raw individual records.

full-investigation becomes less convenient than “all patient rows,” but this is necessary to prevent accidental raw-memory disclosure.

Defaulting clinician/caregiver contributions to annotations or pending corrections adds user review friction, but it prevents silent mutation of the permanent personal record.

Research revocation may have nuanced treatment for already-derived non-identifying aggregate outputs; the protocol and consent evidence must disclose and encode that behavior.

14. Open risks

The largest implementation risk is incomplete object labeling. If memories, labs, documents, wearable data, summaries, and generated artifacts do not carry consistent data categories, security labels, provenance, and source links, C1 cannot enforce least privilege reliably.

The second major risk is agent leakage. Workspace agents must not retrieve from full personal memory and then redact after generation. They must retrieve only from authorized resource sets before prompt construction.

Aggregate analytics still carries re-identification and differencing risk. Minimum cell sizes, suppression, query budgets, privacy review, and careful cohort design are required.

Exports cannot be technically revoked after download. WellBe can watermark, audit, constrain, and contractually prohibit reuse, but revocation can only stop future WellBe-mediated access.

Narrow grants can hide clinically relevant context. The UI should make “request additional scope” easy, but the default must remain least privilege.

I used the brief as the canonical source for the internal WellBe constraints; I did not inspect the private repository files named in the brief.

15. Source list

NIST SP 800-162 ABAC: https://csrc.nist.gov/pubs/sp/800/162/upd2/final

FHIR Consent: https://fhir.hl7.org/fhir/consent.html

FHIR Security Labels: https://build.fhir.org/security-labels.html

FHIR Provenance: https://build.fhir.org/provenance.html

HHS HIPAA De-identification Guidance: https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html

NIST Privacy-Enhancing Cryptography: https://csrc.nist.gov/Projects/pec

HHS Common Rule, 45 CFR 46: https://www.hhs.gov/ohrp/regulations-and-policy/regulations/45-cfr-46/index.html

OHRP Subject Withdrawal Guidance PDF: https://www.hhs.gov/ohrp/sites/default/files/ohrp/policy/subjectwithdrawal.pdf

FHIR AuditEvent: https://build.fhir.org/auditevent.html

RFC 9396 OAuth 2.0 Rich Authorization Requests: https://www.rfc-editor.org/rfc/rfc9396.html

UMA 2.0 Core: https://docs.kantarainitiative.org/uma/ed/uma-core-2.0-02.html

