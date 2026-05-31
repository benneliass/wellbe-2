# Decision: C12 append-only audit and closure-oriented notifications

**Status:** Proposed - awaiting user approval  
**Date opened:** 2026-06-01  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Story:** WEL-75  
**Blocks:** WEL-75 — Build append-only audit log and closure-oriented notification service

---

## Question

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

## Context

C12 is the append-only trust spine for WellBe. It must prove who accessed, changed, rendered, exported, shared, blocked, routed, or corrected health context under which authority, while avoiding a secondary PHI store. The new C1/C17 grant model, C10 Safety Gate, Investigation/Theory/External Evidence primitives, and future institution/research workspaces all rely on C12 for auditable trust. A weak C12 contract could make revocation unverifiable, leak sensitive text, allow mutable audit history, or create anxiety-inducing notifications.

## Research provided

_Research received: 2026-06-01_ - external consultant report, archived verbatim at [research-inputs/wellbe_c12_c13_alignment_report.md](research-inputs/wellbe_c12_c13_alignment_report.md) (source `.docx` alongside it).

The report recommends approving C12 as an append-only trust spine composed of a tamper-evident audit ledger, minimized event envelope, restricted payload-reference model, and closure-oriented notification service.

The report says C12 should be implemented as two coupled but separate services:

- **C12 Audit Ledger:** a write-once, append-only, tamper-evident ledger of trust, access, safety, provenance, graph, Investigation, Theory, external-evidence, API, export, institution, and research events.
- **C12 Notification Service:** a policy-driven subscriber that converts a small subset of audit events into patient-facing notifications or digest entries. It must never be the system of record for clinical truth, access policy, investigation state, or safety decisions.

The report's decision-ready C12 principles:

- Append-only is a security boundary. C12 has no update/delete application API for audit rows. Corrections are new events that reference prior events.
- Audit is not a PHI warehouse. Store hashes, identifiers, source refs, provenance refs, and minimal summaries. Store full sensitive text only in a restricted encrypted store with `secure_text_ref`, TTL, reason code, and separate access audit.
- Authority is mandatory. Every access, export, render, invite, contribution, aggregate, or research event must include controller entitlement or `grant_id`, `role_binding_id`, `purpose_code`, `scope_codes`, and `access_predicate_hash`.
- C10 output rendering is auditable. C10 decision events and C13 render events must correlate through `safety_request_id`, `render_token_id`, `binds_text_sha256`, `output_hash`, `correlation_id`, and `access_predicate_hash`.
- External evidence remains context-only. External source and relevance events must carry `context_only=true` and `not_personal_evidence=true`; attempted use as personal proof emits a rejection event.
- Patient-facing audit is a redacted transparency layer. Patients can see meaningful summaries of access, sharing, export, grant, investigation, and safety fallback events, but not admin-only, security-only, or restricted review payloads.
- Notifications are closure-oriented. Notifications describe what changed, why it matters, and the next available step. They must not diagnose, rank diseases, create panic, hide urgent risk, or blame clinicians.

The recommended event naming convention is lower-case dotted names: `<component>.<domain>.<action>`, for example `c1.grant.revoked`, `c13.output.rendered`, and `c14.investigation.closed`. The already-approved C10 names (`ai_output.allowed`, `ai_output.blocked`, etc.) are preserved exactly with `producer_component="c10"`.

The recommended `AuditEventV1` envelope includes:

- `schema_version`, `event_id`, `event_type`, `event_version`;
- producer component/service/environment;
- `occurred_at`, `recorded_at`, and `time_skew_ms`;
- hashed actor identifiers, actor type, role type, and session hash;
- hashed patient/controller/resource subject refs, workspace, grant, and role binding;
- authority fields: entitlement type, access predicate hash, purpose code, scope codes, policy version;
- correlation context: correlation id, trace id, request id, idempotency key, client app, user agent hash, coarse IP geo bucket;
- outcome status and reason codes;
- payload classification, payload hash, optional payload ref, minimal payload, notification policy, visibility labels, retention class;
- tamper-evidence fields: previous event hash, event hash, hash-chain scope, signature ref.

The report recommends payload classifications: `no_phi`, `metadata_only`, `source_refs`, `restricted_text_ref`, `encrypted_phi_fragment` as a strongly discouraged exception, and `prohibited`. Prohibited audit payload content includes raw document text, raw SMS, full candidate AI output, full blocked text, and full external article text.

The report recommends an append-only technical design with:

- `audit_events`;
- `audit_event_subjects`;
- `audit_hash_roots`;
- `audit_ingest_idempotency`;
- `notification_outbox`;
- `notification_delivery_attempts`;
- `notification_preferences` as mutable preferences separate from the ledger.

Database enforcement should include INSERT-only application roles on audit tables, no application UPDATE/DELETE/TRUNCATE privileges, triggers rejecting update/delete attempts, row-level security by hashed subject and visibility, time/hash-bucket partitioning, WORM/object-lock backups, and special approval for audit table migrations.

For critical flows, the report says C13/C1/C10 must not proceed if required C12 writes fail. For high-volume low-risk telemetry, producers may use durable local outbox and async forwarding, but the local outbox must be durable before acknowledging user-visible success.

The notification model includes classes: `inline_confirmation`, `digest`, `immediate_closure`, `security_notice`, `urgent_route`, and `silent_audit`. Events that usually notify include grant creation/material changes/revocation/expiry, workspace membership changes, invites, exports, addressed comments, contribution lifecycle, investigation closure/reopen/review due/pending item due, Theory status changes that close a loop or change next steps, high-quality subscribed external research watch results, institution/research consent changes, and security-sensitive anomalies.

Events that should usually remain audit-only include routine access predicate evaluations, internal graph retrievals, raw blob writes, object-lock metadata, routine fact extraction/OCR/evidence linking/graph mutations, C10 allow/allow-with-obligations events, C10 block/rewrite/manual-review/fail-closed except in-session safe fallback, external source ingestion/tiering/suppressed low-quality results, and institution/research internals that could increase re-identification risk.

Every patient-facing notification must state what changed, state why it matters in closure or agency terms, offer a next step when useful, avoid diagnosis/disease probability/ranked differentials, avoid panic/hidden urgency/false reassurance/clinician blame, avoid raw PHI in push/SMS/email subject lines, and use static pre-approved templates for safety, security, grant, export, and research consent events. AI-generated notification text must pass C10; for MVP it should not be used for safety, access, export, grant, or consent events.

The report recommends notification deduplication by `patient_id_hash + notification_class + event_family + resource_id_hash + day_bucket + template_id`, default non-urgent quiet hours of local 21:00-08:00, batching by investigation/thread, append-only delivery attempts, exponential backoff with jitter, dead-lettering after a policy maximum, and provider error storage as provider codes rather than raw PHI-bearing responses.

The recommended MVP audit APIs are:

- `GET /v2/audit/my-events`
- `GET /v2/audit/my-events/{event_id}`
- `GET /internal/c12/audit-events`
- `GET /internal/c12/audit-events/{event_id}/integrity`

Every audit query emits `c12.audit.query_performed`. Controller queries never return admin/security/safety-review payloads. Admin/security queries require reason code, least-privilege role, time-bounded access, and result limits. Institution roles cannot query patient audit events. Research roles can query protocol-level summaries, not patient-level timelines.

The report's C12 MVP boundary includes: `AuditEventV1` envelope and registry, append-only `audit_events` with insert-only DB role, payload/event hashes, idempotency/correlation/trace/visibility/classification, C1/C17 grant/access/export/comment/contribution events, C10 decision events and secure text-ref pattern, C13 render/export/API-denial events, C14/C15/C16 lifecycle/external events, patient-visible audit query by patient/event/time, notification policy engine, and static templates for grant/export/consent/investigation/pending-item notifications.

## Approaches considered

Approach 1: Normal application logs only - use existing logs as the audit system. Pro: low implementation cost. Con: the report says logs are insufficient for trust, revocation, safety, export, and patient transparency. Research recommendation: reject.

Approach 2: Store full event payloads and text - keep complete payloads, raw clinical text, candidate AI text, and blocked text in audit rows. Pro: easier forensic reconstruction. Con: creates avoidable PHI exposure and a second sensitive store. Research recommendation: reject.

Approach 3: Mutable audit table for corrections - update existing rows when events are corrected. Pro: easier current-state queries. Con: destroys historical integrity; corrections must be new events. Research recommendation: reject.

Approach 4: AI-generated notification copy in MVP - dynamically generate patient-facing notifications. Pro: flexible wording. Con: safety and tone consistency are too important for sensitive event families. Research recommendation: reject for MVP; use static templates or C10-approved text only.

Approach 5: Blockchain anchoring - anchor audit events in a public or external immutable ledger. Pro: stronger external tamper evidence. Con: unnecessary for MVP and adds complexity. Research recommendation: defer; tamper-evident hash chains plus WORM roots are enough for MVP.

Approach 6: Notify on every access event - push every access as a patient notification. Pro: maximum apparent transparency. Con: creates fatigue and anxiety. Research recommendation: reject; expose routine access in audit timeline instead.

Approach 7: Append-only trust spine plus policy-driven notifications - use a minimized, tamper-evident ledger and separate notification policy engine. Pro: preserves trust, revocation evidence, PHI minimization, and closure-oriented UX. Con: more schema, registry, hash-chain, and notification policy work. Research recommendation: adopt.

## Decision

Adopt C12 as an append-only, tamper-evident audit ledger plus policy-driven closure-oriented notification service: C12 audit rows are immutable, PHI-minimized, hash-bound, visibility-scoped, and authority-linked; C12 records C1/C17 grants and access, C2-C6 provenance/data/graph events, C10 safety decisions, C13 render/API/export events, and C14-C16 Investigation/Theory/External Evidence events; notifications are generated only from approved policy/templates or C10-approved text and must avoid diagnosis, alarmism, false reassurance, clinician blame, and hidden urgent risk.

## Trade-offs accepted

If approved, this accepts:

- C12 becomes part of critical transaction boundaries; C1/C10/C13 critical flows fail closed if required audit writes fail.
- Event volume and storage cost increase; only non-critical high-volume API accept events may be sampled.
- Hash chains and WORM roots add implementation complexity but provide tamper evidence.
- Patient transparency must be carefully redacted to avoid anxiety and metadata PHI leakage.
- Restricted text retention is allowed only by explicit exception with TTL, reason code, separate keys, metrics, and read audit.
- Legal retention periods remain deployment-jurisdiction decisions and require legal/privacy approval before production.
- Notification copy is less personalized in MVP because sensitive notifications use static templates.

## Implementation notes

If approved:

- Add C12 contracts under `backend/packages/contracts/src/wellbe_contracts/c12_audit/`, including `AuditEventV1`, event type registry, visibility labels, payload classifications, retention classes, notification policies, and delivery attempt DTOs.
- Implement C12 service code in `backend/packages/c12_audit/` with event validation, canonical payload hashing, idempotency, hash-chain computation, visibility enforcement, and append-only write APIs.
- Add migration(s) for `audit_events`, `audit_event_subjects`, `audit_hash_roots`, `audit_ingest_idempotency`, `notification_outbox`, `notification_delivery_attempts`, and `notification_preferences`.
- Enforce INSERT-only DB role for audit event writes and deny UPDATE/DELETE/TRUNCATE via privileges and triggers.
- Keep mutable notification preferences separate from immutable audit rows; every preference change emits an audit event.
- Add a producer SDK/helper so C1/C5/C6/C10/C13/C14-C16 do not hand-roll event envelopes.
- Add a notification template registry with owner, allowed variables, PHI class, C10 requirement, and sample copy.
- Implement in-app/digest notification policy first, with dedupe, quiet hours, retry backoff, delivery attempts, and dead-letter events.
- Add tests for immutability, required authority fields, PHI minimization, C10 text retention, hash-chain integrity, idempotency, revocation, notification policy/tone, audit query authorization, and critical-flow fail-closed behavior.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
