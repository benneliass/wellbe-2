# Decision: C13 versioned API and contract boundary

**Status:** Approved  
**Date opened:** 2026-06-01  
**Date approved:** 2026-06-01  
**Approved by:** User  
**Jira Story:** WEL-127  
**Blocks:** WEL-127 — Version API contract for Investigation, Theory, External Evidence, and Grant

---

## Question

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

## Context

C13 is the single public contract boundary for WellBe surfaces and clients. The C1/C17 deep grant model, C10 render-token decision, Investigation/Theory objects, and External Evidence context-only model all need stable API contracts before the redesign can be safely exposed. A weak C13 contract could allow clients to bypass grants, render AI output without C10 approval, treat external evidence as personal proof, represent Theory as diagnosis, or leak institution/research individual-level data.

## Research provided

_Research received: 2026-06-01_ - external consultant report, archived verbatim at [research-inputs/wellbe_c12_c13_alignment_report.md](research-inputs/wellbe_c12_c13_alignment_report.md) (source `.docx` alongside it).

The report recommends a hybrid versioning model:

- Keep `/v1` stable for existing MVP Health Thread and ShareGrant behavior.
- Introduce `/v2` path-versioned resources for Investigation, Theory, External Evidence relevance, Workspace, Role, Grant, AccessPredicate, RenderApproval, and AuditRef resources.
- Include `schema_version` in every DTO.
- Optionally support media type `application/vnd.wellbe.v2+json`, but do not rely on media-type negotiation as the primary versioning mechanism.
- Do not add v2-sensitive fields to v1 responses.

The report says this is the safest option because the new primitives carry new authorization, provenance, safety, external-context, and non-diagnosis semantics. Path versioning gives explicit routing, explicit generated clients, simpler browser/debug behavior, and lower risk of old clients silently ignoring safety-critical fields.

Migration rules from the report:

- Existing v1 endpoints remain backward compatible until formally deprecated.
- v1 ShareGrant can be internally mapped to v2 Grant, but v1 clients receive only v1-safe fields.
- v2 capabilities are default-false. Missing capability means denied.
- Unknown authorization fields in requests fail closed with `unknown_authorization_field`.
- Unknown display fields in responses may be ignored only if marked non-authoritative.
- Adding optional non-sensitive fields is a minor version change.
- Adding required fields, changing authorization meaning, or changing safety semantics requires a new endpoint or future major version.
- Deprecated fields must include `deprecated: true`, replacement field, and removal target in OpenAPI.

All v2 DTOs must include `schema_version`, stable resource identifiers, timestamps where applicable, audit refs for write/render/export/share/access-sensitive responses, no raw PHI unless explicitly authorized and documented, no diagnosis/ranked-differential/disease-probability/unsupported clinical recommendation fields, and strict unknown-field handling for authorization/grant/render/safety DTOs.

The report recommends these core DTOs:

- `AuditRefV2` with audit event id, correlation id, trace id, visibility, and safe event summary. Include on grant changes, workspace membership changes, comments/contributions, exports, render events, Investigation/Theory status changes, consent changes, and denial responses when audit exists.
- `SourceRefV2` with component (`c2|c5|c16`), provenance id, source hash, safe display label, source scope, and required access. Every derived claim returned by C13 must include source refs or be rejected with `provenance_missing`.
- `C10ObligationV2` with obligation code, required flag, display location, and blocking flag. UI must prove it can fulfill blocking obligations before render.
- `InvestigationV2` with health thread ids, primary question, scope, status, safety level, workspace id, evidence bundle ref, linked theories, missing context, pending items, review cadence, created by, timestamps, and audit refs. Forbidden fields include diagnosis, ranked differential, disease probability, treatment plan, clinical order, and full patient record access.
- `TheoryV2` with investigation/thread ids, label, proposed by, status, safety level, evidence-for/evidence-against/missing-data, external context refs, review marker, clinician annotation ref, `not_diagnosis=true`, timestamps, and audit refs.
- `ExternalSourceRefV2` with source quality tier, source type, publisher, publication/retrieval dates, source URL ref, display label, `context_only=true`, `not_personal_evidence=true`, and audit refs.
- `RelevanceLinkV2` with external source/claim ids, linked thread/investigation ids, relevance status, why-relevant summary, source tier, `context_only=true`, `not_personal_evidence=true`, obligations, timestamps, and audit refs.
- `WorkspaceV2` with workspace type, controller subject ref, membership state, active role binding, capability summary, `data_access_not_implied=true`, timestamps, and audit refs.
- `RoleBindingV2` with workspace id, role type, principal ref, state, start/expiry, and audit refs.
- `GrantV2` with grant type, subject/grantee refs, workspace and role binding, scope codes, scope profile version, purpose code, status, start/expiry/revocation, default-false capabilities, contribution policy, resource constraints summary, obligations, timestamps, and audit refs.
- `AccessPredicateV2` with decision, reason codes, grant/workspace/role/purpose/scope/capabilities, resource constraints summary, obligations, validity, policy version, evaluated time, and audit event id.
- `RenderApprovalV2` with render authorization ref, optional opaque token, request/text hash binding, expiry, C10 decision, obligations, reason codes, review markers, source display requirements, and audit event id.

The report recommends that C13 keep signed C10 render tokens server-side when possible and return `render_authorization_ref` to browser clients. Service-to-service clients may receive an opaque render token if required. The token must never be client-generated and must never authorize text other than the exact hash C10 evaluated.

C13 rendering rules:

- Hash the exact bytes of rendered text.
- Verify C10 token signature, expiry, request binding, role binding, and `binds_text_sha256`.
- Verify all C10 obligations can be fulfilled by the UI surface.
- Emit `c13.render_token.verified` and `c13.output.rendered` before returning output.
- Return `c10_token_required`, `c10_token_hash_mismatch`, or `c10_obligations_unfulfilled` when validation fails.
- If the UI cannot show sources, disclaimers, urgent next steps, or context-only external-evidence labels, C13 must not render output.

Recommended MVP scaffolding routes include:

- `GET /v2/schema`
- `POST /v2/access/evaluate`
- `GET /v2/workspaces`
- `GET /v2/workspaces/{workspace_id}`
- `GET /v2/grants`
- `POST /v2/grants`
- `POST /v2/grants/{grant_id}/revoke`
- `GET /v2/investigations`
- `POST /v2/investigations`
- `GET /v2/investigations/{investigation_id}`
- `PATCH /v2/investigations/{investigation_id}`
- `POST /v2/investigations/{investigation_id}/close`
- `POST /v2/investigations/{investigation_id}/reopen`
- `GET /v2/investigations/{investigation_id}/theories`
- `POST /v2/investigations/{investigation_id}/theories`
- `GET /v2/theories/{theory_id}`
- `PATCH /v2/theories/{theory_id}`
- `GET /v2/investigations/{investigation_id}/external-context`
- `POST /v2/render/validate`
- `GET /v2/audit/my-events`

Post-MVP routes include full workspace member/invite endpoints, comment and contribution lifecycle, external evidence search/watch subscriptions, institution aggregate query/export, research sandbox query/export, webhooks, and admin/security audit review endpoints.

Backward compatibility rules:

- v1 Health Thread responses remain unchanged unless strictly backward compatible and not safety-sensitive.
- v1 ShareGrant remains compatible and maps internally to v2 Grant with conservative defaults.
- v1 does not expose Investigation, Theory, ExternalEvidenceRef, RelevanceLink, AccessPredicate internals, C10 render tokens, or deep grant fields.
- v1 clients cannot render AI-generated health output unless they use a v2 render path or a server-side compatibility wrapper that enforces C10.
- No v1 endpoint should return external evidence in a way that can be read as personal proof.
- New v2 capabilities default false when mapped from v1.
- Deprecation notices use headers and documentation, not silent behavior changes.

C13 must synchronously enforce authentication/principal resolution, C1/C17 access predicate evaluation before data retrieval or mutation, revocation state and short-lived predicate validity, capability checks, C10 token/hash validation before rendering AI output, C12 audit write for critical access/render/export/share/revocation paths, and basic request schema validation/forbidden field rejection.

C13 delegates but verifies outcomes for C5 provenance, C6 graph semantic constraints, C14 Investigation lifecycle transitions, C15 Theory state/evidence role semantics, C16 source-quality tiering and context-only relevance, C10 safety evaluation, and C12 append-only storage/notification derivation.

The report says C13 must fail closed when C1 is unavailable or returns unknown policy, grants are missing/expired/revoked/denied, workspace membership exists without active grant, C10 token is missing/expired/invalid/mismatched, C10 obligations cannot be fulfilled, provenance is missing, external evidence is requested as personal proof, Theory or graph content violates non-diagnosis semantics, institution/research paths would return patient identifiers or individual data without governance, C12 audit write fails for critical flows, or clients send unknown authorization fields.

The report recommends RFC 9457-style Problem Details with stable WellBe codes, including: `grant_required`, `grant_expired`, `grant_revoked`, `scope_denied`, `capability_denied`, `active_role_required`, `workspace_membership_not_access`, `c10_token_required`, `c10_token_hash_mismatch`, `c10_obligations_unfulfilled`, `provenance_missing`, `external_context_only_violation`, `theory_diagnosis_violation`, `institution_aggregate_only_violation`, `cross_patient_opt_in_required`, `research_protocol_consent_required`, `audit_write_failed`, `export_requires_capability`, `unknown_contract_version`, `unknown_authorization_field`, `render_token_expired`, `render_token_invalid`, `policy_unavailable`, and `audit_ref_unavailable`.

The report recommends OpenAPI 3.1.1, separate `openapi-v1.yaml` and `openapi-v2.yaml`, generated clients in separate namespaces, `additionalProperties: false` for authorization/grant/render/safety DTOs, golden OpenAPI snapshots in CI, compatibility tests proving v1 schemas exclude v2-only fields, and vendor extensions including `x-wellbe-component`, `x-wellbe-phi-classification`, `x-wellbe-access-required`, `x-wellbe-c10-required`, `x-wellbe-audit-required`, `x-wellbe-context-only`, and `x-wellbe-not-diagnosis`.

The report says the following must exist before C1-C6 alignment can be considered clean: `/v2` DTO stubs for AccessPredicate, Workspace, RoleBinding, Grant, Investigation, Theory, ExternalSourceRef, RelevanceLink, RenderApproval, and AuditRef; stable error codes; C1 access predicate enforcement at C13 boundary; C5 provenance-required response model; C6 non-diagnosis semantics in public DTOs; C16 context-only external evidence model; C12 audit refs for critical responses; and v1 compatibility guardrails.

## Approaches considered

Approach 1: `/v2` path versioning only - expose new contract resources under `/v2`. Pro: clear, simple, generated-client friendly, and low ambiguity. Con: duplicates some v1 route families. Research recommendation: adopt as primary, with schema versions in DTOs.

Approach 2: media-type versioning only - use content negotiation as the primary versioning mechanism. Pro: cleaner URL space. Con: harder for browsers, debugging, gateway rules, and generated clients. Research recommendation: reject as primary; optional support is acceptable.

Approach 3: resource-level `schema_version` only - keep paths stable and rely on body version fields. Pro: minimal routing changes. Con: unsafe because old clients can silently ignore new required safety fields. Research recommendation: reject as primary.

Approach 4: hybrid path plus schema version - use `/v2` route families and `schema_version` in every DTO. Pro: explicit routing plus machine-checkable object versions. Con: more route/docs/client surface. Research recommendation: adopt.

Approach 5: add v2 fields to v1 responses - evolve v1 responses with Investigation/Theory/external evidence/deep grant fields. Pro: fewer endpoint families. Con: old clients may misinterpret Theory, external evidence, or grant fields. Research recommendation: reject.

## Decision

Adopt a hybrid C13 versioning strategy: keep `/v1` stable for existing MVP Health Thread and ShareGrant behavior; introduce `/v2` path-versioned resources for Investigation, Theory, External Evidence relevance, Workspace, Role, Grant, AccessPredicate, C10 RenderApproval, and C12 AuditRef contracts; require `schema_version` in every v2 DTO; enforce C1/C17 authorization, C5 provenance, C6 non-diagnosis semantics, C10 exact-hash render authorization, C16 context-only external evidence, and C12 audit emission at the C13 boundary; use RFC 9457-style Problem Details with stable WellBe error codes.

## Trade-offs accepted

If approved, this accepts:

- `/v2` duplicates some v1 route families, but clarity and safety outweigh route consolidation.
- Strict DTOs slow client iteration, but safety-critical fields need explicit contracts.
- Server-side render tokens complicate the architecture, but prevent client-side token misuse.
- Obligations cannot be trusted to clients alone; C13 must block render when obligations cannot be fulfilled.
- Error codes may reveal policy categories, so user-facing detail must remain safe while internal reason detail stays in audit.
- Institution and research schemas start conservative and may feel underpowered until governance and re-identification review mature.
- v1 clients needing AI output must use a server-side compatibility wrapper that enforces v2 C10 render rules.

## Implementation notes

If approved:

- Add v2 DTOs under `backend/packages/contracts/src/wellbe_contracts/c13_api/` for `AuditRefV2`, `SourceRefV2`, `C10ObligationV2`, `InvestigationV2`, `MissingContextItemV2`, `TheoryV2`, `EvidenceLinkV2`, `SourcedRecordFindingV2`, `ExternalSourceRefV2`, `RelevanceLinkV2`, `WorkspaceV2`, `RoleBindingV2`, `GrantV2`, `AccessPredicateV2`, `RenderApprovalV2`, and Problem Details error models.
- Add stable enum registries for Investigation statuses, Theory statuses, source tiers, capabilities, purpose codes, obligation codes, and error codes.
- Add C13 route dependencies/middleware that require C1 evaluation before handler code can fetch data.
- Keep unsafe fields impossible to serialize by excluding them from public DTOs.
- Treat C12 audit write as part of the transaction boundary for critical access/render/export/share/revocation flows.
- Implement C10 render approval validation in one shared C13 utility; do not duplicate token logic per endpoint.
- Generate and snapshot separate OpenAPI v1/v2 specs.
- Add compatibility tests proving v1 schemas do not include v2-only fields.
- Add tests for version routing, OpenAPI generation, C1 fail-closed access, membership-not-access, capability denial, C10 token/hash/obligation failures, provenance missing, Theory diagnosis violation, external context-only violation, institution/research guardrails, audit write failure, Problem Details shape, and unknown authorization field rejection.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
