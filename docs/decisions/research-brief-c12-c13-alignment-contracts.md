# Research Brief: Remaining C1-C6 Alignment Gates — C12 Audit/Notification and C13 Versioned Contracts

**Date prepared:** 2026-06-01  
**Prepared for:** External consultant / research reviewer  
**Prepared by:** WellBe agent  
**Research scope:** Two remaining research gates needed to finish the C1-C6 redesign alignment workstream.

This file contains both research assignments in one document:

1. **Assignment A — C12 Notification & Audit Service:** append-only audit log and closure-oriented notification contract.
2. **Assignment B — C13 API & Contract Layer:** versioned contract for Investigation, Theory, External Evidence, and deep Grant/Role/Workspace.

The goal is to produce implementation-ready recommendations that can be copied into Decision Records and approved before implementation continues.

---

## 0. Product Background

WellBe is now framed as a **Patient-Centered Health Investigation OS**. Its sovereign core is a **Personal Shared Health Memory OS**: a user-controlled memory layer that helps individuals carry health context forward until each concern is resolved, explained, monitored, or safely handed off.

The platform is personal-first:

- The individual is always the data controller.
- Clinicians, care teams, institutions, and researchers may use role-specific workspaces only through explicit, scoped, time-boxed, purpose-bound grants.
- No institution or clinician receives default access to individual data.
- Cross-patient comparison is always explicit opt-in and user-initiated.
- WellBe investigates, never diagnoses.
- Every derived claim must be source-linked.
- Every user-facing AI output must pass the Safety Gate (C10) before rendering.

The operating loop is:

```text
Capture -> Connect -> Investigate -> Clarify -> Close -> Correct
```

Core objects:

- **Health Thread:** living container for one unresolved or ongoing concern.
- **Investigation:** structured research process around one or more Health Threads: primary question, scope, participants under grant, linked Theories, evidence bundle, missing context, pending items, safety flags, and review cadence.
- **Theory:** user- or clinician-proposed explanation evaluated against available evidence. It is never a diagnosis, ranked differential, or disease claim. It carries evidence-for, evidence-against, missing-data, external-context links, status, and safety level.
- **External Evidence Source / External Claim:** non-personal medical or contextual source stored separately from personal data; it can be relevant context but never proof about the individual.
- **Workspace / Role / Grant:** the C17/C1 model that allows role-specific experiences while preserving individual control.

---

## 1. Relevant Core Components

The canonical component map defines these components:

| Component | Purpose |
|---|---|
| C1 Trust & Consent Service | Auth identity, consent scopes, share grants, revocation log, cross-patient opt-in gate. |
| C2 Raw Context Vault | Immutable, append-only store of every raw input with full provenance. |
| C3 Ingestion Layer | Source-type adapters writing into the Raw Context Vault; separate external-evidence ingestion into C16. |
| C4 Processing Pipeline | Extracts entities, facts, signals, Theory claims, and external claims. |
| C5 Evidence & Provenance Service | Links every derived fact back to source; enforces no orphan claims. |
| C6 Knowledge Graph Store | Typed nodes and evidence-weighted edges; supports Investigation/Theory objects without diagnosis edges. |
| C10 Safety & Governance Gate | Mandatory gate before user-facing AI output. |
| C12 Notification & Audit Service | Append-only audit trail of every event; user-facing notifications that are closure-oriented and low-alarm. |
| C13 API & Contract Layer | REST/OpenAPI surface, webhooks, and shared contracts; single boundary all surfaces and features call. |
| C14 Investigation Engine | Owns Investigation lifecycle/status, scope, participants, evidence bundles, review cadence. |
| C15 Theory Service | Owns Theory object, evidence-for/against/missing, safety level, never diagnosis. |
| C16 External Evidence Graph + Research Watch | Separate external source graph with source-quality tiers; relevance links only. |
| C17 Workspace, Role & Grant Layer | Role-specific workspaces and deep grant model. Extends C1. |

The remaining research asks focus on C12 and C13, but the answers must account for C1-C6 plus C10/C14-C17 because audit, notification, and contract boundaries cross all of them.

---

## 2. Current Implementation State

### C1 / C17 deep Grant, Role, Workspace

Already approved and partially implemented through `docs/decisions/deep-grant-role-workspace-model.md`.

Approved principles:

- Workspace membership is not data access.
- Every read/search/comment/export/invite/contribution/aggregate/research action resolves through C1 to an active grant or controller entitlement.
- C1 should return an `AccessPredicate`, not only `allow=true`.
- `can_comment`, `can_export`, `can_invite`, and contribution permanence are policy decisions, not raw booleans.
- Clinician/caregiver comments default to workspace annotations; proposed permanent changes go through C11/controller acceptance.
- Institution access is aggregate-only, consented, and must not expose patient identifiers.
- Research sandbox requires global cross-patient prerequisite plus protocol-level consent.
- Revocation must be synchronous and must produce C12 audit/outbox events.
- C12 must capture grant lifecycle, workspace membership/access/search/view, comments, exports, invites, contribution lifecycle, institution aggregate use, research consent/query/export, and policy/security events.
- C13 should expose the deep model through v2 resources or media-type versioning while keeping v1 ShareGrant compatible.

Implemented slices:

- `backend/packages/c1_consent/src/wellbe_c1_consent/deep_grants.py`
- `db/migrations/versions/009_c1_deep_grant_workspace_schema.py`
- tests for ABAC policy behavior.

### C2 Raw Context Vault

Implemented and verified:

- raw event store remains append-only;
- S3 raw blobs use object lock in GOVERNANCE mode;
- raw blob keys hash patient IDs rather than exposing raw patient UUIDs;
- local cluster uses `wellbe-raw-context-locked` bucket.

C12/C13 implication:

- audit events should not leak raw PHI or raw text;
- APIs should expose source references and hashes, not mutable raw record paths;
- access to raw context must be grant-scoped and audited.

### C3 / C4 / C5 external evidence and Theory retrofits

Implemented slices:

- `ExternalEvidenceIngestionService` writes external sources to C16-style external graph, not C2.
- `TheoryClaimExtractor` marks hypotheses as Theory claims, not personal facts.
- `ExternalClaimExtractor` preserves source-quality tier and external scope.
- `ExternalEvidencePolicy` prevents external evidence from becoming personal fact support.

C12/C13 implication:

- external evidence events must distinguish external source ingestion, external claim extraction, and relevance-to-personal-thread links;
- APIs must represent external evidence as context-only and expose source-quality tier;
- audit logs must capture relevance-link evaluation without converting external evidence into user-specific fact.

### C6 Knowledge Graph retrofit

Approved/implemented:

- Investigation and Theory node types are allowed.
- Diagnosis-like node/edge semantics remain prohibited.
- `may_explain` is the strongest causal edge allowed.
- `relevance_link` is forbidden inside the personal graph and belongs to external-context linking.

C12/C13 implication:

- graph contract must expose Investigation/Theory/relevance semantics without diagnosis claims;
- audit must record graph mutations and retrievals at the semantic level needed for traceability.

### C10 Safety Gate

Approved through:

- `docs/decisions/safety-gate-evaluation-contract.md`
- `docs/decisions/engine-risk-tier-safety-routing.md`

Implemented initial slice:

- C10 request/response DTOs in `backend/packages/contracts/src/wellbe_contracts/c10_safety/`
- deterministic-first evaluator in `backend/packages/c10_safety/`
- safety-gate service endpoint in `backend/apps/safety-gate/`
- local Helm/Tilt deployment for `kind-desktop`

Approved C10 requirements that directly affect C12/C13:

- Every user-facing AI or AI-assisted health output must pass C10 synchronously.
- C10 returns decisions: `allow`, `allow_with_obligations`, `rewrite_required`, `block`, `route_urgent`, `manual_review_required`, `fail_closed`.
- C10 emits C12 audit events for allowed, allowed-with-obligations, rewrite-required, rewritten, blocked, routed-urgent, manual-review-required, and fail-closed outcomes.
- C13 must refuse to render AI output unless a signed C10 render token is present and bound to the exact output hash.
- Full candidate text should not be placed on the event backbone by default.
- If blocked text is retained for safety QA, it must be encrypted in a restricted safety-review store and referenced by `secure_text_ref`.

---

## 3. Current Jira State

### WEL-75 — C12 Notification & Audit Service

**Summary:** Build append-only audit log and closure-oriented notification service (WB-DEV-017)  
**Status:** To Do  
**Priority:** Medium  
**Fix Version:** mvp  
**Labels:** `component:safety-model`, `impact:component-local`, `layer:infra`, `re-eval:needs-review`, `triage-2026-05-30-002`, `triage-2026-05-31-003`

Jira purpose:

> Implement an append-only audit log capturing all system event types, and a low-alarm, closure-oriented notification service that surfaces relevant updates to patients without creating anxiety-inducing alert patterns.

Jira acceptance criteria:

- Audit log records all event types defined in the event taxonomy with event type, actor id, target id, timestamp, payload hash.
- Audit log entries are immutable: append-only, no update/delete API.
- Notification service consumes relevant events and produces patient-facing notifications.
- Notifications follow closure-oriented tone: informational, never alarmist.
- Notification delivery is async; failures are retried with exponential backoff.
- Audit log queryable by patient id, event type, and time range.

Why research is required:

- C12 is a core component.
- WEL-75 defines foundational audit immutability, notification behavior, event payload shape, and safety UX.
- C12 now receives more sensitive events from C1/C17, C10, C14-C16, institution aggregate, and research sandbox surfaces.
- Guessing wrong could leak PHI, make audit incomplete, allow mutable audit records, or create anxiety-inducing notifications.

### WEL-127 — C13 Versioned Contracts

**Summary:** Version API contract for Investigation, Theory, External Evidence, and Grant (C13)  
**Status:** To Do  
**Priority:** Low  
**Fix Version:** post-mvp  
**Labels:** `component:workspace-grant`, `impact:cross-cutting`, `layer:feature-api`, `re-eval:clean`, `triage-2026-05-31-003`

Jira purpose:

> Extend and version the API & Contract Layer (C13) to expose the new primitives (Investigation, Theory, External Evidence relevance, deep Grant/Role/Workspace) as a backward-compatible contract version. Single contract boundary all workspaces and features call.

Known link:

- Blocked by / related to the resolved C1/C17 Spike WEL-131.
- Relates to WEL-65, the existing C13 MVP API surface.

Why research is required:

- C13 is a core component and the cross-component contract boundary.
- WEL-127 affects how all user-facing and workspace clients access Investigation, Theory, External Evidence, and grants.
- Contract design must preserve backward compatibility, enforce C1/C17 grants, require C10 render tokens, avoid institution default access, and represent context-only external evidence.
- Guessing wrong could lock in unsafe public API semantics across the platform.

---

# Assignment A — C12 Audit & Notification Contract

## A1. Research Question

What is the approved C12 audit and notification contract for the Patient-Centered Health Investigation OS?

Specifically:

1. What event names and payload fields are mandatory for C1-C17 events, especially C1/C17 grant events, C10 safety events, C14 Investigation events, C15 Theory events, C16 External Evidence events, and C13 render/API events?
2. What append-only immutability guarantees are required at database, service, API, and operational levels?
3. How should C12 hash, redact, encrypt, or reference sensitive payload data so audit is useful without storing unnecessary PHI?
4. Which events should create patient-facing notifications, and which must remain audit-only?
5. What closure-oriented notification tone rules prevent alarmist, diagnostic, or unsafe notification behavior?
6. How should notification retries, deduplication, escalation, quiet hours, delivery channels, and failure audit work?
7. How should C12 support grant revocation, C10 block/fail-closed events, urgent routing, institution aggregate events, research consent/query/export events, and external-evidence relevance events?
8. What query APIs are allowed for audit logs, and what access controls must apply?

## A2. What C12 Must Protect

C12 is not just a logging utility. It is part of the trust spine:

- It must prove that access, sharing, revocation, safety evaluation, output rendering, exports, and corrections happened under the right authority.
- It must not become a PHI leak.
- It must not create a second mutable source of truth.
- It must not create fear-inducing notifications.
- It must support patient agency by surfacing meaningful closure updates without becoming a clinical alerting system.

## A3. Event Families That Need Coverage

The consultant should propose event names and payload contracts for at least these families.

### C1 / C17 Trust, Consent, Role, Workspace, Grant

Events to consider:

- user authenticated/session started/session ended;
- grant created/updated/expired/revoked;
- grant scope evaluated;
- access allowed/denied;
- role binding created/deactivated;
- workspace membership added/removed;
- workspace viewed/searched;
- comment added;
- export requested/completed/denied;
- invite sent/accepted/revoked;
- contribution proposed/accepted/rejected;
- controller entitlement evaluated;
- institution aggregate inclusion consent changed;
- research protocol consent changed;
- cross-patient opt-in enabled/disabled.

Key constraints:

- Workspace membership alone never authorizes data access.
- Every non-owner read must reference grant id, active role, workspace, purpose, and access predicate hash.
- Revocation must be auditable and synchronous from C1 perspective.
- Institution events must be aggregate-only and never include patient identifiers in institution-facing paths.

### C2 Raw Context Vault

Events to consider:

- raw context event created;
- raw blob written;
- raw blob object-lock metadata recorded;
- append-only write rejected;
- raw context read/viewed/exported under grant;
- deduplication/idempotency result.

Key constraints:

- Raw input is immutable.
- Audit should store identifiers/hashes and source metadata, not raw PHI text by default.
- Reads/views/exports need access context and grant or controller entitlement.

### C3 Ingestion

Events to consider:

- adapter run started/completed/failed;
- manual/document/SMS/device/FHIR source imported;
- external evidence source ingested to C16 path;
- ingestion rejected due to invalid source quality, consent, adapter error, or provenance problem.

Key constraints:

- Personal ingestion writes to C2.
- External evidence does not write to C2 as personal raw data.
- Event payload should distinguish personal source ingestion from external source ingestion.

### C4 Processing

Events to consider:

- fact extracted;
- health signal created;
- Theory claim extracted;
- external claim extracted;
- extraction low confidence / requires review;
- OCR completed/failed;
- negative-evidence query created.

Key constraints:

- Extracted facts/signals must remain source-linked.
- Theory claims are not facts or diagnoses.
- External claims remain external-context scope.

### C5 Evidence & Provenance

Events to consider:

- evidence linked;
- evidence corrected;
- orphan claim rejected;
- relevance link created/evaluated;
- external evidence rejected as personal support.

Key constraints:

- No orphan claims.
- External evidence can be relevance/context only, never proof about the user.

### C6 Knowledge Graph

Events to consider:

- node created/updated;
- edge created/rejected;
- prohibited diagnostic edge rejected;
- Investigation/Theory graph projection changed;
- graph retrieval performed for an engine/API response.

Key constraints:

- No diagnosis-like node or edge semantics.
- `may_explain` is the strongest causal edge.
- `relevance_link` belongs to external-context linking, not personal graph evidence.

### C10 Safety Gate

Already approved C10 audit events:

- `ai_output.allowed`
- `ai_output.allowed_with_obligations`
- `ai_output.rewrite_required`
- `ai_output.rewritten`
- `ai_output.blocked`
- `ai_output.routed_urgent`
- `ai_output.manual_review_required`
- `ai_output.fail_closed`

The C12 research should decide:

- exact payload schema;
- visibility level (`user_visible`, `admin_only`, `security_only`);
- whether notification is generated;
- text-retention rules;
- retention period;
- query permissions;
- event correlation with C13 render token and C1 access predicate.

### C13 API / Render

Events to consider:

- API request accepted/denied;
- render token verified/rejected;
- output rendered;
- post-C10 text mismatch blocked;
- export/download delivered;
- webhook received/rejected;
- public/share link accessed/denied.

Key constraints:

- C13 must not render AI output without a valid C10 signed token bound to exact output hash.
- API access must enforce C1/C17 grants.
- Audit must allow later explanation of who saw what, under which grant, and why.

### C14 / C15 / C16 Investigation, Theory, External Evidence

Events to consider:

- Investigation created/updated/closed/reopened;
- participant added/removed under grant;
- evidence bundle created/changed;
- Theory created/updated/status changed;
- evidence-for/evidence-against/missing-data linked;
- external source added/tiered;
- external source relevance linked to a thread;
- research watch result found/ignored/suppressed;
- Tier 5 source hidden/surfaced in allowed sandbox.

Key constraints:

- Theory is never diagnosis.
- External source is context only.
- Research/cross-patient/institution surfaces require explicit consent/governance.

## A4. Notification Questions

C12 notifications should help users close loops without causing anxiety. The consultant should propose a notification taxonomy:

- Which audit events are notification-triggering?
- Which events are audit-only?
- Which events create digest entries rather than immediate notifications?
- Which events must always use pre-approved static text?
- Which events must pass through C10 before notification text is rendered?
- What urgency classes exist for notifications?
- How should orange/red/self-harm routing interact with notification delivery?
- What notification copy patterns are allowed and blocked?
- How should quiet hours, batching, deduplication, and throttling work?
- How should failed delivery be retried and audited?

Examples that likely need notification decisions:

- pending item due soon;
- referral/result status changed;
- user grant expiring soon;
- grant revoked;
- clinician added a comment;
- C10 blocked an unsafe output;
- urgent safe fallback route shown;
- external evidence watch found a possibly relevant source;
- Theory status changed;
- Investigation review cadence due;
- export completed;
- institution/research consent changed.

Tone constraints:

- Informational, never alarmist.
- No diagnosis or disease conclusion.
- No false reassurance.
- No panic language.
- No clinician blame.
- No hidden urgent risk.
- Every urgent notification must include a next step.
- Notifications should be phrased around closure and agency: what changed, why it matters, what the user can do next.

## A5. Audit Immutability Questions

The consultant should recommend technical controls:

- append-only database table design;
- no update/delete application API;
- database permissions that prevent application roles from updating/deleting audit rows;
- cryptographic payload hash strategy;
- optional hash chain or Merkle strategy;
- timestamp source and clock-skew handling;
- idempotency keys;
- correlation IDs and trace IDs;
- retention policy;
- PHI minimization;
- secure storage for restricted text, if needed;
- admin query limits and access controls;
- patient-visible audit summary versus internal/security audit.

## A6. Expected Deliverable for Assignment A

Please provide:

1. A recommended C12 event taxonomy with event names grouped by component.
2. A versioned audit payload schema for MVP.
3. A visibility model for audit events.
4. A PHI/text retention model.
5. An append-only technical design.
6. Notification-triggering rules.
7. Notification copy/tone rules with allowed and blocked examples.
8. Retry, deduplication, quiet-hour, batching, and failure handling rules.
9. Required C1/C10/C13 integration points.
10. MVP vs post-MVP scope.
11. Test plan and acceptance criteria.
12. Open risks and trade-offs.

---

# Assignment B — C13 Versioned API & Contract Boundary

## B1. Research Question

What is the approved C13 versioned contract strategy for exposing Investigation, Theory, External Evidence relevance, and deep Grant/Role/Workspace primitives without weakening personal-first control, provenance, or safety?

Specifically:

1. Should the new contract be exposed as `/v2`, media-type versioning, or resource-level versioning?
2. What contract objects are required for Investigation, Theory, External Evidence, Relevance Link, Workspace, Role, Grant, AccessPredicate, C10 render token, and C12 audit references?
3. How should C13 preserve backward compatibility for existing v1 Health Thread and ShareGrant behavior?
4. What fields must be required, optional, forbidden, or default-false?
5. What authorization and safety checks must C13 perform before returning data or rendering output?
6. What error codes should C13 return for grant denial, expired/revoked grant, C10 token missing/mismatch, provenance missing, external evidence overclaim, institution individual-data leakage, and cross-patient opt-in missing?
7. Which APIs are MVP, post-MVP, or deferred?
8. How should C13 OpenAPI and generated clients represent versioned contracts without causing unsafe client assumptions?

## B2. What C13 Must Protect

C13 is the single contract boundary all surfaces and features call. It must prevent:

- clients bypassing C1/C17 grants;
- clients bypassing C10 safety evaluation;
- external evidence appearing as personal fact;
- Theory appearing as diagnosis;
- institution/research APIs receiving patient identifiers by default;
- old clients silently receiving new sensitive fields;
- new clients treating `full-investigation` as all-patient-data access;
- post-C10 text mutation after render-token approval.

## B3. Existing C13 / Contract State

Current repository state:

- `backend/apps/api/` is a FastAPI C13 app stub.
- `backend/packages/contracts/` contains shared Pydantic DTOs for existing components.
- Existing contract namespaces include C1, C2, C3, C4, C5, C7, C10, and event/outbox primitives.
- C10 DTOs now exist and require C13 render-token enforcement.
- Deep grants exist in implementation package `backend/packages/c1_consent/`, but C13-facing v2 contract shape is not yet finalized.
- Investigation, Theory, and External Evidence relevance need public/contract DTOs that preserve the new architecture.

## B4. Contract Objects Needing Recommendations

### Investigation

Potential fields:

- `investigation_id`
- `health_thread_ids`
- `primary_question`
- `scope`
- `status`
- `safety_level`
- `participants`
- `workspace_id`
- `grant_id`
- `evidence_bundle_id`
- `linked_theory_ids`
- `missing_context_items`
- `pending_items`
- `review_cadence`
- `created_by`
- `created_at`
- `updated_at`
- C12 audit references

Questions:

- What statuses are allowed?
- What participant fields can be exposed to which roles?
- How does an Investigation represent unknowns without implying diagnosis?
- What is required before an Investigation summary can be rendered?
- What must be source-linked?

### Theory

Potential fields:

- `theory_id`
- `investigation_id`
- `health_thread_id`
- `label`
- `proposed_by`
- `status`
- `safety_level`
- `evidence_for`
- `evidence_against`
- `missing_data`
- `external_context_refs`
- `review_marker`
- `clinician_annotation_ref`
- `created_at`
- `updated_at`

Questions:

- What labels/status values avoid diagnosis semantics?
- What wording or fields are forbidden?
- Can a clinician-entered diagnosis be represented, and if so how is it marked as sourced record rather than WellBe diagnosis?
- How should C10 obligations be represented at API boundary?

### External Evidence / Relevance

Potential fields:

- `external_source_id`
- `external_claim_id`
- `source_quality_tier`
- `source_type`
- `publisher`
- `publication_date`
- `retrieved_at`
- `relevance_link_id`
- `linked_thread_id`
- `context_only`
- `not_personal_evidence`
- `display_label`
- `source_url` or restricted source reference

Questions:

- How should Tier 1-5 be exposed?
- Should Tier 5 be omitted, hidden, or sandbox-only by default?
- How does C13 prevent clients from using external evidence as user-specific proof?
- What required disclaimers/obligations must be returned?

### Workspace / Role / Grant / AccessPredicate

Potential fields:

- `workspace_id`
- `workspace_type`
- `active_role_binding_id`
- `role_type`
- `grant_id`
- `grant_type`
- `scope_code`
- `scope_profile_version`
- `purpose_code`
- `expires_at`
- `revoked_at`
- `capabilities`
- `contribution_policy`
- `resource_filters`
- `denied_labels`
- `obligations`
- `access_predicate_hash`
- `audit_event_id`

Questions:

- Which fields are public, internal, or admin-only?
- How should `AccessPredicate` be returned or referenced?
- Should C13 ever expose raw resource filters to clients?
- How are unknown v2 authorization fields handled?
- How are default-false capabilities represented?
- How are contribution lifecycle states represented?

### C10 Render Token and Output Contract

Potential fields:

- `render_token`
- `binds_request_id`
- `binds_text_sha256`
- `expires_at`
- `c10_decision`
- `obligations`
- `reason_codes`
- `review_markers`
- `source_display_requirements`

Questions:

- Should render token be returned directly to web clients or handled server-side only?
- How should C13 enforce token/hash match?
- How should C13 expose obligations to UI?
- What happens when UI cannot fulfill obligations?

### C12 Audit References

Potential fields:

- `audit_event_id`
- `correlation_id`
- `trace_id`
- `visibility`
- `event_summary`

Questions:

- Which API responses should include audit references?
- Which audit details should be user-visible?
- How should admin/security-only audit remain hidden?

## B5. API Versioning Strategy Questions

The consultant should compare:

### Option 1: `/v2` path versioning

Pros to evaluate:

- easy client separation;
- explicit docs;
- simple routing;
- low ambiguity.

Cons to evaluate:

- duplicate endpoints;
- migration overhead;
- possible drift between v1 and v2.

### Option 2: media-type versioning

Pros:

- cleaner resource paths;
- version negotiated by headers.

Cons:

- harder for browsers/simple clients;
- generated clients may be less obvious;
- operational/debugging complexity.

### Option 3: resource-level version fields

Pros:

- works well for stable resources with evolving fields.

Cons:

- clients may silently ignore or misuse new safety fields;
- harder to enforce breaking changes.

### Option 4: hybrid

Example:

- keep `/v1` for existing MVP Health Thread/share behavior;
- introduce `/v2` or explicit media type for Investigation/Theory/Workspace/Grant contracts;
- use object `schema_version` fields in every DTO;
- preserve v1 compatibility by defaulting new capabilities false and omitting unsafe fields from old responses.

The consultant should recommend one strategy and explain migration rules.

## B6. Authorization and Safety Boundary Questions

C13 must enforce or call:

- C1/C17 access predicate evaluation before data retrieval.
- C10 Safety Gate before any user-facing AI output is rendered.
- C5 provenance validation / source refs for derived claims.
- C12 audit emission for access/render/export/share events.
- C6 graph semantic safety constraints for Investigation/Theory graph data.
- External evidence context-only obligations.

Questions:

1. Which checks happen synchronously inside C13 versus delegated to component services?
2. What is the request flow for a workspace read?
3. What is the request flow for rendering an AI-generated summary?
4. What is the request flow for exporting a Visit Packet?
5. What is the request flow for institution aggregate summaries?
6. What is the request flow for research sandbox output?
7. What must fail closed?

## B7. Error Code Recommendations Needed

Please propose stable C13 error codes and HTTP mappings for:

- `grant_required`
- `grant_expired`
- `grant_revoked`
- `scope_denied`
- `capability_denied`
- `active_role_required`
- `workspace_membership_not_access`
- `c10_token_required`
- `c10_token_hash_mismatch`
- `c10_obligations_unfulfilled`
- `provenance_missing`
- `external_context_only_violation`
- `theory_diagnosis_violation`
- `institution_aggregate_only_violation`
- `cross_patient_opt_in_required`
- `research_protocol_consent_required`
- `audit_write_failed`
- `export_requires_capability`
- `unknown_contract_version`
- `unknown_authorization_field`

The consultant may rename these, but should provide final recommended codes.

## B8. MVP / Post-MVP / Deferred Boundary

Current Jira marks WEL-127 as post-MVP, but the C1-C6 redesign alignment may require at least contract scaffolding earlier.

Please classify:

- must exist before C1-C6 alignment can be considered clean;
- must exist before WEL-74/C10 can be fully integrated;
- must exist before clinician/shared/institution/research workspaces;
- post-MVP only;
- deferred.

Likely MVP/minimum scaffolding:

- C10 render-token enforcement contract at C13 boundary;
- v2 DTO stubs for `AccessPredicate`, `Workspace`, `Grant`, `Investigation`, `Theory`, and `ExternalEvidenceRef`;
- explicit error-code contract;
- no unsafe fields exposed to v1 clients;
- OpenAPI generation strategy.

Likely post-MVP:

- full clinician workspace endpoint suite;
- full institution aggregate APIs;
- research sandbox APIs;
- complete generated TS client for all v2 resources.

The consultant should confirm or revise this boundary.

## B9. Expected Deliverable for Assignment B

Please provide:

1. Recommended C13 versioning strategy.
2. Versioned DTO/resource model for Investigation, Theory, External Evidence, Workspace, Role, Grant, AccessPredicate, C10 render token, and C12 audit references.
3. Endpoint families and minimum required routes.
4. Backward compatibility strategy for v1 clients.
5. Required C1/C5/C10/C12 integration checks.
6. Error-code and HTTP-status mapping.
7. Field-level rules: required, optional, forbidden, default-false, internal-only.
8. OpenAPI / generated-client strategy.
9. MVP/post-MVP/deferred split.
10. Test plan and acceptance criteria.
11. Open risks and trade-offs.

---

## 4. Files the Consultant Should Reference

Canonical / architecture:

- `docs/system-design/platform_identity.md`
- `docs/system-design/system_design.md`
- `docs/system-design/system_principles.md`
- `docs/architecture/component-map.md`
- `docs/architecture/development-backlog.md`
- `docs/safety/safety_model.md`
- `docs/safety/do_not_diagnose_rules.md`

Existing approved Decision Records:

- `docs/decisions/deep-grant-role-workspace-model.md`
- `docs/decisions/safety-gate-evaluation-contract.md`
- `docs/decisions/engine-risk-tier-safety-routing.md`

Existing implementation / contracts:

- `backend/packages/contracts/src/wellbe_contracts/`
- `backend/packages/contracts/src/wellbe_contracts/c10_safety/__init__.py`
- `backend/packages/c1_consent/src/wellbe_c1_consent/deep_grants.py`
- `backend/packages/c10_safety/src/wellbe_c10_safety/evaluator.py`
- `backend/packages/c5_evidence/src/wellbe_c5_evidence/service.py`
- `backend/packages/c3_ingestion/src/wellbe_c3_ingestion/external_evidence.py`
- `backend/packages/c4_processing/src/wellbe_c4_processing/investigation_extractor.py`
- `backend/packages/c12_audit/`
- `backend/apps/notification-worker/`
- `backend/apps/api/`

Migrations:

- `db/migrations/versions/009_c1_deep_grant_workspace_schema.py`
- earlier C1-C6 migrations in `db/migrations/versions/`

Jira:

- `WEL-75` — C12 append-only audit and closure-oriented notification service.
- `WEL-127` — C13 versioned contracts for Investigation, Theory, External Evidence, and Grant.
- `WEL-74` / `WEL-134` — C10 Safety Gate and risk-tier research, now approved.
- `WEL-131` — C1/C17 deep grant research, now approved.

---

## 5. Non-Goals

Do not redesign WellBe’s product identity. The individual remains controller and primary beneficiary.

Do not propose default institution access, default cross-patient analytics, clinician-controlled patient data, diagnosis output, ranked differentials, or external evidence as proof about the user.

Do not propose model-only enforcement for safety, access, or provenance.

Do not make C12 a mutable event store.

Do not make C13 a bypass around C1 grants, C10 safety, C5 provenance, or C12 audit.

Do not require WellBe to become an EHR, practice-management platform, clinical-staff workflow system, or medical authority.

---

## 6. Required Output Format From Consultant

Please return one report with two sections:

1. **C12 Audit & Notification Contract**
2. **C13 Versioned API & Contract Boundary**

Each section should include:

- executive recommendation;
- recommended contract/schema;
- alternatives considered;
- decision-ready recommendation;
- MVP vs post-MVP boundary;
- implementation notes;
- test plan;
- open risks and trade-offs;
- any assumptions that must be approved before implementation.

The report may cite external standards or references for audit, notification, API versioning, privacy, health AI governance, OpenAPI, or event sourcing, but the final recommendations must fit the WellBe constraints above.

---

## 7. Agent Protocol Note

These assignments touch core components:

- C12 Notification & Audit Service
- C13 API & Contract Layer

Agents may read existing repo docs to formulate the question, but agents may not conduct the research or decide the answer themselves. Research results must be provided by the user or external consultant. After results are provided, the agent will record them in Decision Records, propose implementation decisions, wait for explicit approval, and only then implement.
