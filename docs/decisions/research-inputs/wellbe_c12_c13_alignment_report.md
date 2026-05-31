# WellBe C12/C13 Alignment Report

_Verbatim text extraction from consultant .docx received 2026-06-01._

WellBe C12 and C13 Alignment Gates: Audit, Notification, and Versioned Contracts

Decision-ready implementation recommendations for WEL-75 and WEL-127

Prepared for WellBe by external research reviewer

2026-06-01

Table of Contents

Document control

Purpose. This report provides implementation-ready recommendations for the two remaining C1-C6 alignment gates: C12 Notification and Audit Service, and C13 API and Contract Layer. It is written so the recommendations can be copied into WellBe Decision Records and used as acceptance criteria.

Approval posture. These are recommendations for approval. They should not be treated as already-approved product policy until WellBe explicitly accepts them in the relevant Decision Records.

Scope assumptions. The recommendations are based on the supplied research brief and the stated repository state. They assume WellBe remains a Patient-Centered Health Investigation OS; the individual remains the controller; WellBe investigates but does not diagnose; external evidence is context only; all user-facing AI or AI-assisted health output passes C10 before rendering; and all access resolves through C1/C17 grants or controller entitlement.

External references used. The design borrows terminology and guardrails from HL7 FHIR AuditEvent, NIST SP 800-92, OWASP logging guidance, CloudEvents, W3C Trace Context, OpenAPI 3.1.1, RFC 9457 Problem Details, RFC 9110 HTTP semantics, the HIPAA Security Rule technical safeguards, and the NIST AI Risk Management Framework. A reference list appears at the end of the document.

Executive summary

C12 recommendation in one paragraph

Approve C12 as an append-only trust spine composed of a tamper-evident audit ledger, a minimized event envelope, a restricted payload-reference model, and a closure-oriented notification service. C12 must record who accessed, changed, rendered, exported, shared, blocked, routed, or corrected data under which authority, while avoiding a secondary PHI store. The audit ledger must be insert-only at the service and database levels, use payload hashes and event hash chains, and expose only redacted summaries to patients and authorized reviewers. Notifications must be generated from policy, not raw event copy, and must use static or C10-approved text that helps the user close loops without diagnosis, alarmism, false reassurance, or hidden urgent risk.

C13 recommendation in one paragraph

Approve a hybrid versioning strategy: keep existing /v1 behavior stable, introduce /v2 path-versioned resources for Investigation, Theory, External Evidence, Workspace, Role, Grant, AccessPredicate, C10 render authorization, and C12 audit references, and include explicit schema_version fields in every DTO. C13 must be the only public contract boundary, but it must not become an authorization or safety bypass. Every read, search, comment, export, render, webhook, invite, or aggregate request must synchronously resolve C1/C17 access, enforce C5 provenance and C6 semantics, enforce C10 render-token and output-hash binding for AI outputs, and emit C12 audit events. Errors should use RFC 9457-style Problem Details with WellBe-stable error codes.

Minimum approval package

The minimum clean alignment package should include:

C12 AuditEventV1 envelope, event taxonomy, immutable storage controls, PHI-minimized payload references, notification policy, and query access model.

C13 /v2 DTOs for AccessPredicate, Grant, RoleBinding, Workspace, Investigation, Theory, ExternalEvidenceRef, RelevanceLink, RenderApproval, and AuditRef.

C13 stable error codes, OpenAPI generation strategy, and contract tests proving v1 clients do not receive v2 fields.

C1/C10/C12 integration rules that fail closed for revoked grants, missing or mismatched render tokens, missing provenance, external-evidence overclaiming, and audit write failure on critical flows.

Section 1 - C12 Audit and Notification Contract

1.1 Executive recommendation

C12 should be implemented as two coupled but separate services:

C12 Audit Ledger. A write-once, append-only, tamper-evident ledger of trust, access, safety, provenance, graph, investigation, theory, external-evidence, API, export, institution, and research events.

C12 Notification Service. A policy-driven subscriber that converts a small subset of audit events into patient-facing notifications or digest entries. It must never be the system of record for clinical truth, access policy, investigation state, or safety decisions.

C12 must prove that an action happened under an authority without storing the sensitive content of the action. It should store event metadata, canonical payload hashes, source references, access predicate hashes, render token references, and restricted secure references when content retention is strictly required. Raw context, raw clinical text, candidate AI output, blocked text, and external article text should not be placed on the audit backbone by default.

1.2 Decision-ready C12 principles

Approve the following C12 principles:

Append-only is a security boundary. C12 has no update or delete application API for audit rows. Corrections are represented as new events that reference prior events.

Audit is not a PHI warehouse. Store hashes, identifiers, source refs, provenance refs, and minimal summaries. Store full sensitive text only in a restricted encrypted store with secure_text_ref, TTL, reason code, and separate access audit.

Authority is mandatory. Every access, export, render, invite, contribution, aggregate, or research event must include controller entitlement or grant_id, role_binding_id, purpose_code, scope_codes, and access_predicate_hash.

C10 output rendering is auditable. C10 decision events and C13 render events must correlate through safety_request_id, render_token_id, binds_text_sha256, output_hash, correlation_id, and access_predicate_hash.

External evidence remains context-only. External source and relevance events must carry context_only=true and not_personal_evidence=true; any attempted use as personal proof must emit a rejection event.

Patient-facing audit is a redacted transparency layer. Patients can see meaningful summaries of access, sharing, export, grant, investigation, and safety fallback events, but not admin-only, security-only, or restricted review payloads.

Notifications are closure-oriented. Notifications describe what changed, why it matters, and the next available step. They must not diagnose, rank diseases, create panic, hide urgent risk, or blame clinicians.

1.3 C12 event naming convention

Use lower-case dotted event names:

<component>.<domain>.<action>

Examples: c1.grant.revoked, c13.output.rendered, c14.investigation.closed.

Exception: preserve the already-approved C10 event names exactly as approved: ai_output.allowed, ai_output.blocked, and related names. Set producer_component="c10" in the envelope.

Every event type has an event_version, starting at 1.0.0. Breaking payload changes require a new event version. Event types should not be renamed after production use; deprecate and supersede instead.

1.4 Recommended C12 event taxonomy

1.4.1 C1 and C17 trust, consent, grant, role, and workspace events

Event name

Purpose

Notification policy

c1.auth.session_started

Authentication/session start.

Audit-only unless security anomaly.

c1.auth.session_ended

Session ended or token revoked.

Audit-only.

c1.auth.failed

Failed login or auth challenge.

Security notification if risk threshold met.

c1.controller.entitlement_evaluated

Controller entitlement checked.

Audit-only.

c1.grant.created

New grant created.

Immediate to controller; digest to grantee if appropriate.

c1.grant.updated

Scope, purpose, or expiry changed.

Immediate if materially affects access; otherwise digest.

c1.grant.expired

Grant expired.

Digest unless it blocks pending collaboration.

c1.grant.expiring_soon

Grant approaching expiry.

Digest or immediate based on user preference.

c1.grant.revoked

Controller or policy revoked grant.

Immediate to controller; grantee receives scoped non-PHI notice.

c1.grant.revocation_enforced

Revocation synchronously propagated to access path.

Audit-only; required for compliance evidence.

c1.grant.scope_evaluated

Scope decision made.

Audit-only.

c1.access.allowed

Access authorized.

Audit-only; patient-visible audit summary.

c1.access.denied

Access denied.

Audit-only unless repeated suspicious attempts.

c1.access.predicate_issued

AccessPredicate returned to C13 or service.

Audit-only.

c17.role_binding.created

Role binding created.

Immediate to controller if external person/service.

c17.role_binding.deactivated

Role binding deactivated.

Digest or immediate if access changes.

c17.workspace.membership_added

Principal added to workspace.

Immediate to controller.

c17.workspace.membership_removed

Principal removed from workspace.

Immediate or digest.

c17.workspace.viewed

Workspace viewed.

Audit-only; patient-visible for non-owner access.

c17.workspace.searched

Workspace searched.

Audit-only; patient-visible for non-owner search.

c17.workspace.comment_added

Comment or annotation added.

Digest by default; immediate if directly assigned.

c17.workspace.invite_sent

Invite sent.

Immediate to controller and invitee.

c17.workspace.invite_accepted

Invite accepted.

Immediate to controller.

c17.workspace.invite_revoked

Invite revoked.

Immediate to invitee if already delivered; audit otherwise.

c17.contribution.proposed

Non-owner proposes permanent contribution.

Immediate or digest to controller.

c17.contribution.accepted

Controller accepts contribution.

Immediate to proposer and controller.

c17.contribution.rejected

Controller rejects contribution.

Digest; careful neutral copy.

c17.export.requested

Export requested.

Audit-only at request; visible in export timeline.

c17.export.completed

Export file/snapshot completed.

Immediate.

c17.export.denied

Export denied by policy.

Immediate to requester with non-technical reason.

c17.institution.aggregate_consent_changed

Aggregate inclusion consent changed.

Immediate.

c17.research.protocol_consent_changed

Protocol-level consent changed.

Immediate.

c17.cross_patient.opt_in_enabled

Global cross-patient opt-in enabled.

Immediate confirmation.

c17.cross_patient.opt_in_disabled

Global cross-patient opt-in disabled.

Immediate confirmation.

Mandatory payload fields for non-owner access events: grant_id, workspace_id, role_binding_id, purpose_code, scope_codes, access_predicate_hash, policy_version, resource_type, resource_id_hash, outcome, and reason_codes.

1.4.2 C2 Raw Context Vault events

Event name

Purpose

Notification policy

c2.raw_context.created

Raw context metadata created.

Digest only if user-facing capture completed.

c2.raw_blob.written

Raw blob written to immutable storage.

Audit-only.

c2.raw_blob.object_lock_recorded

Object lock or WORM metadata recorded.

Audit-only.

c2.append_only_write_rejected

Attempted update/delete or invalid append rejected.

Security/admin audit; notify only if user action failed.

c2.raw_context.read

Raw context read by service or user.

Audit-only; patient-visible for non-owner reads.

c2.raw_context.viewed

Raw context viewed in UI.

Audit-only; patient-visible for non-owner views.

c2.raw_context.exported

Raw context included in export.

Immediate as part of export completion.

c2.raw_context.deduplication_result

Duplicate or idempotent ingest resolved.

Audit-only.

Payload must use raw_event_id, raw_blob_hash, source_type, source_system_ref, provenance_id, object_lock_mode, and retention_until when applicable. Do not store raw text, file path containing patient UUID, or original filename if it contains PHI.

1.4.3 C3 ingestion events

Event name

Purpose

Notification policy

c3.adapter.run_started

Adapter job started.

Audit-only.

c3.adapter.run_completed

Adapter job completed.

Digest if user-initiated.

c3.adapter.run_failed

Adapter job failed.

Immediate if user action needs retry; audit otherwise.

c3.personal_source.imported

Personal source imported into C2 path.

Digest or inline confirmation.

c3.external_source.ingested_to_c16

External source ingested to C16 path.

Audit-only or research-watch digest.

c3.ingestion.rejected

Ingestion rejected for consent, provenance, quality, or adapter error.

Immediate if user-facing correction needed.

Payload must include ingestion_run_id, source_scope (personal or external), adapter_type, source_type, target_component, provenance_id, consent_context, and rejection_reason when applicable.

1.4.4 C4 processing events

Event name

Purpose

Notification policy

c4.fact.extracted

Personal fact extracted from source-linked context.

Audit-only.

c4.health_signal.created

Health signal created.

Digest only when surfaced through Investigation UI.

c4.theory_claim.extracted

Hypothesis/theory claim extracted.

Audit-only.

c4.external_claim.extracted

External claim extracted from C16 source.

Audit-only.

c4.extraction.requires_review

Low confidence extraction or ambiguity.

Digest if user can resolve missing context.

c4.ocr.completed

OCR completed.

Audit-only.

c4.ocr.failed

OCR failed.

Immediate if user can re-upload; otherwise audit-only.

c4.negative_evidence_query.created

Query seeking evidence-against/missing context.

Audit-only.

Payload must include processing_run_id, input_source_refs, output_claim_refs, confidence_bucket, review_required, source_scope, and claim_scope (personal_fact, theory_claim, or external_claim).

1.4.5 C5 Evidence and Provenance events

Event name

Purpose

Notification policy

c5.evidence.linked

Claim linked to source.

Audit-only.

c5.evidence.corrected

Evidence link corrected.

Digest if user-visible claim changed.

c5.orphan_claim.rejected

Derived claim rejected for missing provenance.

Audit-only; critical metric.

c5.relevance_link.created

Context-only relevance link created.

Digest only if surfaced in Investigation.

c5.relevance_link.evaluated

Relevance link scored/evaluated.

Audit-only.

c5.external_evidence_as_personal_support.rejected

Attempted misuse of external evidence as personal proof rejected.

Audit-only; security/safety review if repeated.

Payload must include claim_id, provenance_id, source_refs, evidence_role, link_type, external_context_only, not_personal_evidence, and rejection_reason when applicable.

1.4.6 C6 Knowledge Graph events

Event name

Purpose

Notification policy

c6.graph.node_created

Node created.

Audit-only unless user-visible Investigation/Theory created.

c6.graph.node_updated

Node updated.

Audit-only.

c6.graph.edge_created

Edge created.

Audit-only.

c6.graph.edge_rejected

Edge rejected by graph constraints.

Audit-only.

c6.graph.prohibited_diagnostic_edge_rejected

Diagnosis-like edge rejected.

Audit-only; safety metric.

c6.graph.investigation_projection_changed

Investigation projection changed.

Digest only if visible state changed.

c6.graph.theory_projection_changed

Theory projection changed.

Digest only if visible state changed.

c6.graph.retrieval_performed

Graph retrieval used for API or engine response.

Audit-only.

Payload must include node_type, edge_type, semantic_constraint_version, allowed_semantics, source_refs, retrieval_purpose, and prohibited_semantics when rejected. Diagnosis-like nodes and edges must not be persisted.

1.4.7 C10 Safety Gate events

Preserve the approved C10 event names:

Event name

Required outcome

Notification policy

ai_output.allowed

Output passed C10.

Audit-only; output may render.

ai_output.allowed_with_obligations

Output passed with display obligations.

Audit-only; obligations render inline.

ai_output.rewrite_required

Candidate must be rewritten.

Audit-only.

ai_output.rewritten

Rewritten candidate evaluated.

Audit-only.

ai_output.blocked

Output blocked.

Audit-only plus in-session safe fallback; no push notification.

ai_output.routed_urgent

Urgent route triggered.

In-session static urgent fallback; push only if approved by safety policy.

ai_output.manual_review_required

Manual review required.

Audit-only or neutral in-app status if user is waiting.

ai_output.fail_closed

Safety evaluation unavailable or invalid.

Audit-only plus in-session safe fallback.

Mandatory payload fields: safety_request_id, c10_policy_version, risk_tier, decision, reason_codes, obligations, candidate_output_hash, render_token_id if issued, render_token_expires_at, rewritten_output_hash if applicable, fallback_route_id if applicable, secure_text_ref only if restricted retention is approved, source_refs, access_predicate_hash, correlation_id, and trace_id.

Text retention rule: do not place full candidate text, blocked text, or rewritten text on the event backbone. Store only hashes and references. If blocked text is retained for safety QA, use an encrypted restricted store with TTL, separate key, separate service role, and its own C12 read audit.

1.4.8 C13 API and render events

Event name

Purpose

Notification policy

c13.api.request_accepted

API request accepted after auth/routing.

Audit-only; sample high volume if needed except critical paths.

c13.api.request_denied

API request denied.

Audit-only; security notification if suspicious.

c13.render_token.verified

C10 token verified against output hash.

Audit-only.

c13.render_token.rejected

Missing, expired, invalid, or mismatched token.

Audit-only; in-session safe error.

c13.output.rendered

AI/AI-assisted health output rendered.

Audit-only; patient-visible audit summary.

c13.output.text_mismatch_blocked

Post-C10 text mutation detected.

Audit-only; safety/security metric.

c13.export.download_delivered

Export/download delivered.

Immediate or digest to controller.

c13.webhook.received

Webhook received.

Audit-only.

c13.webhook.rejected

Webhook rejected.

Audit-only; admin if integration affected.

c13.share_link.accessed

Share/public link accessed.

Patient-visible audit summary; immediate only for high-risk settings.

c13.share_link.denied

Share/public link denied.

Audit-only unless suspicious.

Payload must include route_id, http_method, principal_ref, workspace_id, grant_id, access_predicate_hash, render_token_id, binds_text_sha256, output_hash, c10_decision, response_resource_refs, source_display_requirements, and audit_write_required.

1.4.9 C14 Investigation events

Event name

Purpose

Notification policy

c14.investigation.created

Investigation opened.

In-app confirmation; digest if created by collaborator.

c14.investigation.updated

Scope/status/metadata updated.

Digest if user-visible change.

c14.investigation.closed

Investigation closed.

Immediate closure notification.

c14.investigation.reopened

Investigation reopened.

Immediate or digest.

c14.investigation.participant_added

Participant added under grant.

Immediate to controller.

c14.investigation.participant_removed

Participant removed.

Immediate or digest.

c14.evidence_bundle.created

Evidence bundle created.

Audit-only.

c14.evidence_bundle.changed

Evidence bundle changed.

Digest if visible summary changes.

c14.pending_item.created

Pending item created.

Digest or immediate if due soon.

c14.pending_item.due_soon

Pending item approaching due date.

Immediate or digest based on urgency and preferences.

c14.pending_item.closed

Pending item closed.

Digest or inline confirmation.

c14.review_cadence.due

Review cadence due.

Digest by default.

c14.review_cadence.completed

Review completed.

Digest or closure summary.

Payload must include investigation_id, health_thread_ids, workspace_id, status, safety_level, evidence_bundle_id, participant_refs, grant_id, missing_context_item_ids, and review_cadence_id when applicable.

1.4.10 C15 Theory events

Event name

Purpose

Notification policy

c15.theory.created

Theory/hypothesis created.

Digest unless user-created.

c15.theory.updated

Label, evidence refs, or metadata changed.

Digest if visible.

c15.theory.status_changed

Theory status changed.

Digest or immediate if it closes a loop.

c15.theory.evidence_for_linked

Evidence-for linked.

Audit-only; digest if visible summary changes.

c15.theory.evidence_against_linked

Evidence-against linked.

Audit-only; digest if visible summary changes.

c15.theory.missing_data_linked

Missing data linked.

Digest if user can act.

c15.theory.external_context_linked

External context linked.

Digest only if quality threshold met.

c15.theory.safety_level_changed

Safety level changed.

Audit-only plus UI state update; urgent handled by C10/C14 flow.

c15.theory.clinician_annotation_added

Clinician annotation added.

Digest or immediate if directly assigned.

Payload must include theory_id, investigation_id, health_thread_id, status, label_hash, proposed_by_role, evidence_for_refs, evidence_against_refs, missing_data_refs, external_context_refs, source_refs, and not_diagnosis=true.

1.4.11 C16 External Evidence Graph and Research Watch events

Event name

Purpose

Notification policy

c16.external_source.added

External source added to C16.

Audit-only.

c16.external_source.tiered

Source-quality tier assigned/changed.

Audit-only.

c16.external_source.updated

External source metadata updated.

Audit-only.

c16.external_claim.extracted

External claim extracted.

Audit-only.

c16.relevance_link.created

External source linked as context to thread/investigation.

Digest if surfaced.

c16.relevance_link.evaluated

Relevance evaluated.

Audit-only.

c16.relevance_link.rejected

Relevance rejected or overclaim blocked.

Audit-only.

c16.research_watch.result_found

Research watch found candidate source.

Digest only; never alarming.

c16.research_watch.result_ignored

Watch result ignored by policy/user.

Audit-only.

c16.research_watch.result_suppressed

Watch result suppressed for quality/safety.

Audit-only.

c16.tier5_source.hidden

Tier 5 source hidden by default.

Audit-only.

c16.tier5_source.surfaced_in_sandbox

Tier 5 surfaced in explicit sandbox.

Audit-only and sandbox-visible warning.

Payload must include external_source_id, external_claim_id, source_quality_tier, source_type, publisher_hash_or_ref, publication_date, retrieved_at, relevance_link_id, linked_thread_id, linked_investigation_id, context_only=true, not_personal_evidence=true, tier5_policy, and sandbox_context when applicable.

1.4.12 Institution and research events

Event name

Purpose

Notification policy

c17.institution.aggregate_query_executed

Aggregate-only query executed.

Audit-only; optional transparency digest.

c17.institution.aggregate_export_created

Aggregate export created.

Audit-only; optional transparency digest.

c17.institution.aggregate_query_denied

Aggregate query denied.

Audit-only/security.

c17.research.sandbox_query_executed

Research sandbox query executed.

Audit-only; protocol transparency summary.

c17.research.sandbox_export_created

Research export created.

Audit-only; protocol transparency summary.

c17.research.query_denied

Research query denied.

Audit-only/security.

c17.research.protocol_consent_checked

Protocol consent checked.

Audit-only.

Institution-facing payloads must never include patient identifiers. Patient-facing transparency can reference that the user’s consent setting allowed inclusion in aggregate use, but should avoid exposing research query details that increase re-identification risk.

1.5 Versioned audit payload schema for MVP

1.5.1 AuditEventV1 envelope

Recommended envelope:

{
  "schema_version": "c12.audit_event.v1",
  "event_id": "01J...ULID",
  "event_type": "c1.grant.revoked",
  "event_version": "1.0.0",
  "producer_component": "c1",
  "producer_service": "consent-service",
  "environment": "prod",
  "occurred_at": "2026-06-01T12:00:00Z",
  "recorded_at": "2026-06-01T12:00:01Z",
  "time_skew_ms": 1000,
  "actor": {
    "actor_type": "user|service|system|institution|researcher",
    "actor_id_hash": "hmac_sha256:...",
    "role_type": "controller|clinician|caregiver|service|admin",
    "auth_session_id_hash": "hmac_sha256:..."
  },
  "subject": {
    "patient_id_hash": "hmac_sha256:...",
    "controller_user_id_hash": "hmac_sha256:...",
    "workspace_id": "wrk_...",
    "grant_id": "grt_...",
    "role_binding_id": "rb_...",
    "resource_type": "investigation",
    "resource_id_hash": "hmac_sha256:..."
  },
  "authority": {
    "entitlement_type": "controller|grant|service_policy|protocol_consent",
    "access_predicate_hash": "sha256:...",
    "purpose_code": "care_context_review",
    "scope_codes": ["thread.read", "investigation.read"],
    "policy_version": "c1.policy.2026-06-01"
  },
  "context": {
    "correlation_id": "corr_...",
    "trace_id": "00-...",
    "request_id": "req_...",
    "idempotency_key": "idem_...",
    "client_app": "wellbe-web",
    "user_agent_hash": "hmac_sha256:...",
    "ip_geo_bucket": "country-region"
  },
  "outcome": {
    "status": "success|denied|rejected|failed|routed",
    "reason_codes": ["grant_revoked"]
  },
  "payload_classification": "metadata_only",
  "payload_hash": "sha256:canonical_payload",
  "payload_ref": null,
  "payload_min": {},
  "notification_policy": "none|digest|immediate|static_template|urgent_route",
  "visibility": ["controller_visible", "admin_only"],
  "retention_class": "trust_ledger",
  "previous_event_hash": "sha256:...",
  "event_hash": "sha256:...",
  "hash_chain_scope": "patient_stream",
  "signature_ref": "kms_sig_..."
}

1.5.2 Field requirements

Field group

Required?

Notes

Event identity

Required

event_id, event_type, event_version, schema_version.

Time

Required

Use producer occurred_at plus C12 server recorded_at; record skew.

Producer

Required

Component, service, environment, build or policy version where available.

Actor

Required

Use hashed identifiers; service actors must include service principal.

Subject

Required when patient-affecting

Use patient/controller hashes, workspace/grant/resource refs.

Authority

Required for access-related events

Must include entitlement or access predicate details.

Correlation

Required

correlation_id; trace_id when available; idempotency key for retried producers.

Outcome

Required

Status and reason codes.

Payload hash

Required

Hash canonical typed payload, not display summary.

Payload ref

Optional

Only for restricted encrypted or source-store payloads.

Visibility

Required

Controls audit query and patient transparency.

Hash chain fields

Required for trust events; recommended for all

previous_event_hash, event_hash, chain scope.

1.6 Visibility model

Use additive visibility labels. A query principal must satisfy at least one allowed label and all resource constraints.

Visibility label

Meaning

Typical events

controller_visible

The individual/controller can see a redacted summary.

Grants, exports, non-owner views, investigation closure.

participant_visible

A workspace participant can see a scoped event summary.

Invite status, comment accepted, grant expired for that participant.

admin_only

Operational staff with approved reason can view.

Adapter failures, low-risk system events.

security_only

Security role and break-glass path only.

Suspicious access, policy bypass attempts.

safety_review

Safety QA/reviewer role only; separate text store access.

C10 blocked retained text refs.

research_admin

Research governance role only.

Protocol query/export metadata.

institution_aggregate_admin

Institution aggregate admin only, no patient identifiers.

Aggregate query metadata.

system_internal

Service-only event, not exposed to humans except logs.

High-volume predicate eval internals.

Patient-visible audit should return summaries, not raw payloads. Example: “A clinician workspace searched this investigation under grant grt_... for visit-prep purpose” is acceptable after redaction. It should not return raw search terms if they include PHI unless the controller performed the search.

1.7 PHI, text retention, hashing, redaction, and references

1.7.1 Payload classification

Classification

Allowed on audit row

Examples

no_phi

Safe metadata only.

Event type, service name, policy version.

metadata_only

Hashed IDs and non-sensitive descriptors.

Grant ID, scope codes, event outcome.

source_refs

References to C2/C5/C16 objects and hashes.

raw_event_id, provenance_id, external_source_id.

restricted_text_ref

Secure reference only, never text.

secure_text_ref for blocked AI output retained for QA.

encrypted_phi_fragment

Strongly discouraged; allowed only with approved exception.

Short message variable that cannot be represented by source ref.

prohibited

Must not be stored in C12.

Raw document text, raw SMS, full candidate AI output, full external article text.

1.7.2 Hashing model

Use separate hashing strategies by purpose:

Identity indexes. HMAC-SHA256 with an audit indexing key for patient IDs, user IDs, session IDs, IP-derived buckets, and resource IDs where enumeration risk exists.

Content binding. SHA-256 for immutable objects and C10 output hashes where the exact bytes must be verified, with the source object kept outside C12.

Payload integrity. SHA-256 over canonical JSON payload after redaction but before insertion. If a restricted original must be proved, store sensitive_content_hash separately without storing the content.

Event integrity. event_hash = SHA256(canonical_envelope_without_event_hash + payload_hash + previous_event_hash).

1.7.3 Restricted text store

A restricted text store is allowed only for approved safety QA, incident response, legal hold, or user-dispute review. It must provide:

Envelope encryption with separate keys from the audit ledger.

Separate service role from C12 normal writer/reader.

TTL default of 30 to 90 days unless legal hold or approved safety case requires longer.

secure_text_ref, not text, on the audit event.

Dedicated c12.restricted_payload.read audit events for every access.

No notification generation from restricted text.

1.8 Append-only technical design

1.8.1 Database controls

Recommended tables:

audit_events: immutable event envelope, minimal payload, hashes, visibility, retention class.

audit_event_subjects: optional fan-out index for patient, workspace, grant, investigation, theory, external source, export, and research protocol references.

audit_hash_roots: daily or hourly Merkle roots and per-stream chain heads.

audit_ingest_idempotency: idempotency keys and producer acknowledgements.

notification_outbox: immutable notification work items derived from audit events.

notification_delivery_attempts: append-only delivery attempts, outcomes, provider message hashes, retry state.

notification_preferences: mutable preferences, separate from the audit ledger; changes emit audit events.

Database enforcement:

Application audit writer role has INSERT only on audit_events and audit_event_subjects.

No application role has UPDATE, DELETE, or TRUNCATE on audit tables.

Database triggers reject update/delete attempts and emit security alerts through a separate privileged path.

Row-level security restricts query by hashed subject and visibility label.

Partition by time and optionally by hash bucket, not raw patient ID.

Backups and archives use WORM/object-lock-capable storage.

Schema migrations that touch audit tables require two-person approval and test evidence.

1.8.2 Service/API controls

C12 exposes POST /internal/c12/audit-events for producers; no update/delete endpoint.

Producers supply idempotency keys for retriable events.

C12 returns event_id, recorded_at, and event_hash on success.

For critical flows, C13/C1/C10 must not proceed if C12 write fails.

For high-volume low-risk telemetry, producers may use local outbox and async forward, but the local outbox must be durable before acknowledging user-visible success.

1.8.3 Tamper evidence

Use per-subject-stream hash chains plus daily Merkle roots:

patient_stream: events involving one hashed patient/controller.

grant_stream: events involving one grant.

global_stream: security and schema events.

research_protocol_stream: protocol consent/query/export events.

Persist chain heads in C12 and write daily Merkle roots to WORM storage. Post-MVP can anchor roots in an external transparency store, but this is not required for MVP.

1.8.4 Time and clock skew

Use C12 server time for recorded_at and producer time for occurred_at.

Store time_skew_ms when producer time is available.

Reject or quarantine events with impossible future timestamps beyond policy threshold.

Query APIs sort by recorded_at by default and expose occurred_at for trace reconstruction.

1.8.5 Retention

Recommended default retention classes:

Retention class

Suggested retention

Examples

trust_ledger

Account lifetime plus approved legal minimum

Grant, access, export, render, revocation.

security

7 years or approved security policy

Failed access, policy bypass, admin query.

safety

7 years for metadata; text refs 30-90 days by default

C10 decisions, urgent routes, fail-closed.

operational

13 to 25 months

Adapter runs, OCR events, webhook failures.

research_governance

Protocol lifetime plus approved legal minimum

Consent, sandbox query/export.

notification_delivery

13 to 25 months for delivery metadata

Delivery attempts and provider outcomes.

Final retention periods require legal/privacy approval by deployment jurisdiction.

1.9 Notification-triggering rules

1.9.1 Notification classes

Class

Use

Delivery behavior

inline_confirmation

Immediate confirmation of user action.

In-app only; no push unless user opted in.

digest

Non-urgent loop closure updates.

Batched by investigation/thread.

immediate_closure

Action is ready, completed, or access changed.

In-app plus preferred channel.

security_notice

Risk-sensitive account/access change.

In-app plus email/push if enabled.

urgent_route

C10/C14 safety route shown in current session.

Static in-session route with next step; push only by approved safety policy.

silent_audit

No patient notification.

Audit only.

1.9.2 Events that should usually notify

Grant created, materially updated, revoked, expiring soon, or expired when it affects collaboration.

Workspace member added or removed.

Invite sent, accepted, or revoked.

Export completed, denied, or delivered.

Clinician/caregiver comment added, when addressed to the user or not already seen.

Contribution proposed, accepted, or rejected.

Investigation closed, reopened, review due, or pending item due soon.

Theory status changed when it closes a loop or changes what the user can do next.

External research watch found a high-quality source that the user explicitly subscribed to receive.

Institution aggregate or research consent changed.

Security-sensitive login/access anomaly.

1.9.3 Events that should usually remain audit-only

Routine access predicate evaluations.

Routine internal graph retrievals.

Raw blob writes and object-lock metadata.

Fact extraction, OCR completion, evidence linking, and graph mutations not surfaced to the user.

C10 allowed/allowed-with-obligations events; obligations render inline with the output.

C10 blocked, rewrite-required, manual-review, and fail-closed events, except for in-session safe fallback copy.

External source ingestion, tiering, and suppressed low-quality research watch results.

Institution/research aggregate query internals that could increase re-identification risk.

1.10 Notification tone and copy rules

1.10.1 Tone policy

Every patient-facing notification must satisfy all of the following:

State what changed.

State why the change matters in closure or agency terms.

Offer the next available step when action is useful.

Avoid diagnosis, disease conclusion, disease probability, or ranked differential wording.

Avoid panic language, hidden urgency, false reassurance, and clinician blame.

Avoid raw PHI in push/SMS/email subject lines.

Use static pre-approved templates for safety, security, grant, export, and research consent events.

Send AI-generated notification text through C10 before rendering. For MVP, do not use AI-generated notification text for safety, access, export, grant, or consent events.

1.10.2 Allowed and blocked examples

Scenario

Allowed copy

Blocked copy

Grant revoked

“Access for Dr. Lee’s workspace has been turned off. You can review or restore sharing settings anytime.”

“Your doctor can no longer see your health data and may miss something important.”

Pending item due soon

“A follow-up item in your sleep investigation is coming due. Review it when you are ready.”

“You may be at risk if you do not complete this now.”

Clinician comment

“A new workspace comment was added to your headache investigation. You can review it and decide whether to add it to your record.”

“Your clinician found a new diagnosis.”

External evidence watch

“A new source may be useful context for your investigation. It is not evidence about you personally.”

“New research explains your symptoms.”

Theory status changed

“One explanation is now marked less consistent with the information currently linked. You can review the sources.”

“We ruled out condition X.”

C10 blocked output

In-session: “I cannot show that wording safely. Here is a safer way to continue.”

Push: “We blocked a dangerous health answer.”

Urgent route

“Based on what you shared, it may be safest to contact local urgent help now. Here are options.”

“Emergency! You are in danger.”

Export completed

“Your Visit Packet is ready. The link expires at the time shown in the app.”

“Your complete medical file has been released.”

Research consent changed

“Your research sharing setting was updated. This does not give researchers direct access to your identity.”

“Researchers can now use your data.”

1.11 Retry, deduplication, quiet hours, batching, and failure handling

1.11.1 Deduplication

Deduplication key:

patient_id_hash + notification_class + event_family + resource_id_hash + day_bucket + template_id

Rules:

Collapse repeated processing or access events into digest items.

Do not dedupe security notices if separate risk events require user awareness.

Do not send more than one non-urgent notification per investigation per day by default.

Do not dedupe export completion with export delivery failure; they are different user outcomes.

1.11.2 Batching

Batch investigation updates into a thread-level digest.

Batch external evidence watch results into a weekly or user-selected digest.

Batch comment/contribution updates unless directly assigned or time-sensitive.

Keep grant revocation, security, export completion, and consent changes outside routine digest.

1.11.3 Quiet hours

Default quiet hours should be user-configurable and region-aware; suggested default is local 21:00 to 08:00 for non-urgent channels.

In-app notifications may appear immediately without push.

Security notices can bypass quiet hours only when risk policy requires it.

Urgent safety routes should be handled in-session; do not rely on delayed push/SMS for urgent clinical safety.

1.11.4 Retry and delivery failure

Use append-only delivery attempts:

Attempt 1 immediately after outbox item becomes eligible.

Retry with exponential backoff and jitter, for example 1 minute, 5 minutes, 30 minutes, 2 hours, 12 hours.

Stop after policy maximum and emit c12.notification.dead_lettered.

Never create repeated user-facing messages after successful delivery.

Provider errors must be stored as provider code, not raw provider response if it contains PHI.

Notification audit events:

c12.notification.created

c12.notification.suppressed

c12.notification.deduped

c12.notification.batched

c12.notification.quiet_hours_deferred

c12.notification.delivery_attempted

c12.notification.delivered

c12.notification.failed

c12.notification.dead_lettered

1.12 Grant revocation, C10, urgent routing, institution, research, and external evidence handling

Grant revocation

C1 must synchronously emit c1.grant.revoked and c1.grant.revocation_enforced before returning revocation success. C13 must reject any subsequent access using the revoked grant and emit access denial events. Cached AccessPredicates must expire immediately through a revocation version or predicate invalidation token.

C10 block and fail-closed

C10 blocked or fail-closed events should not create push notifications. The active session should receive a safe fallback or neutral status message. Audit must capture C10 decision, reason codes, output hash, access predicate hash, and render-token absence.

Urgent routing

Urgent routing is a safety interaction, not a marketing notification. It should use static pre-approved content, display a concrete next step, and record ai_output.routed_urgent. Push/SMS after the session should be allowed only under a separately approved safety policy.

Institution aggregate events

Institution events must be aggregate-only. C12 institution-facing logs cannot include patient identifiers. Patient transparency, if provided, should be phrased at consent-setting level or protocol level and must avoid query details that increase re-identification risk.

Research consent/query/export

Research requires global cross-patient opt-in plus protocol-level consent. Query and export events must include protocol_id, consent_version, sandbox_policy_version, aggregate_only_or_deidentified=true, suppression thresholds, and export approval refs. All research exports are audit-critical.

External-evidence relevance

External-evidence notifications should be digest by default and must say the source is context, not evidence about the individual. Tier 5 sources remain hidden except in explicit sandbox surfaces and should not create patient notifications.

1.13 Audit query APIs and access controls

1.13.1 Allowed APIs

Recommended MVP APIs:

GET /v2/audit/my-events: controller-visible redacted timeline.

GET /v2/audit/my-events/{event_id}: controller-visible event detail.

GET /internal/c12/audit-events: internal/admin query with reason code and policy enforcement.

GET /internal/c12/audit-events/{event_id}/integrity: hash-chain verification.

Supported filters: patient_id only for authorized controller or internal service, event_type, event_family, time_range, resource_type, resource_id, workspace_id, grant_id, investigation_id, theory_id, export_id, safety_request_id, correlation_id, and trace_id.

1.13.2 Query rules

Every audit query emits c12.audit.query_performed with requester, reason, filters hash, result count bucket, and visibility labels.

Controller queries never return admin-only, security-only, or safety-review payloads.

Admin/security queries require approved reason code, least-privilege role, time-bounded access, and result limits.

Institution roles cannot query patient audit events.

Research roles can query protocol-level audit summaries, not patient-level timelines.

payload_min may be returned only if classification and visibility allow it; otherwise return event_summary and refs.

1.14 C1, C10, and C13 integration points

Integration

Required behavior

C1 to C12

Grant lifecycle, access predicate, consent, revocation, and cross-patient opt-in events. Revocation writes are synchronous.

C10 to C12

All approved C10 decision events. Text retained only by secure ref.

C13 to C12

API denial, render token verification/rejection, output render, export/download, webhook, and share-link events. Critical writes fail closed.

C5 to C12

Provenance link/correction/orphan rejection and external-context-only rejection.

C6 to C12

Semantic graph mutation/rejection and retrieval events.

C14/C15/C16 to C12

Investigation, Theory, relevance link, research watch, and external source events.

Notification worker to C12

Notification creation, suppression, delivery attempts, success/failure, dead-letter.

1.15 Alternatives considered for C12

Alternative

Decision

Rationale

Use normal application logs only.

Reject.

Logs are not sufficient for trust, revocation, safety, export, and patient transparency.

Store full event payloads and text.

Reject.

Creates avoidable PHI exposure and a second sensitive store.

Make audit table mutable for corrections.

Reject.

Corrections must be new events to preserve history.

Generate notification copy dynamically with AI.

Reject for MVP.

Safety/tone consistency is too important; use static templates or C10-approved text only.

Use blockchain anchoring.

Defer.

Tamper-evident hash chains plus WORM roots are enough for MVP.

Notify on every access event.

Reject.

Causes notification fatigue and anxiety; expose access in audit timeline instead.

1.16 MVP vs post-MVP boundary for C12

MVP / required for clean alignment

AuditEventV1 envelope and event type registry.

Append-only audit_events table with insert-only DB role and no update/delete API.

Payload hash, event hash, idempotency key, correlation ID, trace ID, visibility, and payload classification.

C1/C17 grant/access/export/comment/contribution events.

C10 approved decision events and secure text ref pattern.

C13 render-token, output-render, export/download, and API-denial events.

C14 Investigation lifecycle, C15 Theory lifecycle, C16 external source/relevance events.

Patient-visible audit query by patient, event type, and time range.

Notification policy engine with in-app notifications, digest, dedupe, retry, quiet hours, and delivery audit.

Static templates for grant, export, consent, investigation, and pending-item notifications.

Post-MVP

Merkle root publication/anchoring outside primary database.

Patient downloadable audit report.

Advanced anomaly detection and security alerting.

Full notification channel matrix and localization.

Institution/research transparency reports.

FHIR AuditEvent export mapping.

Deferred

Public immutable transparency ledger.

Cross-organization audit federation.

AI-generated personalized notification copy for sensitive event families.

1.17 C12 implementation notes

Treat C12 producer SDKs as shared infrastructure. Producers should not hand-roll event envelopes.

Maintain an event registry file in contracts with JSON Schema/Pydantic payload definitions.

Add x-wellbe-phi-classification metadata to event payload schemas.

Maintain a redaction test corpus with realistic PHI-containing examples.

Treat payload hash mismatches, missing access predicate hash, or missing C10 render hash as severity-high defects.

Include event taxonomy changes in architecture review.

Add a notification template registry with template owner, allowed variables, PHI class, C10 requirement, and sample rendered copy.

1.18 C12 test plan and acceptance criteria

Test plan

Immutability tests. Attempt update/delete/truncate through app role and migration role; verify rejection and audit/security alert.

Schema validation tests. Validate every event type against AuditEventV1 and typed payload schemas.

Required authority tests. Non-owner access events without grant_id, role_binding_id, purpose_code, or access_predicate_hash fail ingestion.

PHI minimization tests. Seed payloads with raw clinical text, SMS body, filenames with PHI, and candidate AI text; verify ingestion rejects or redacts.

C10 retention tests. Blocked output stores only hash and optional secure ref; normal audit query cannot retrieve text.

Hash-chain tests. Verify event hash, previous hash, chain head, and tamper detection.

Idempotency tests. Retried producer event returns same event ID or recorded duplicate result without new event spam.

Revocation tests. Revoke grant and immediately attempt access through cached predicate; access denied and audited.

Notification policy tests. Verify triggering, suppression, dedupe, quiet hours, digest, and immediate notification behavior.

Tone tests. Lint notification templates for blocked words/patterns; manual review static safety templates.

Query authorization tests. Controller cannot see admin/security/restricted payloads; admin queries require reason and are audited.

Failure tests. Simulate C12 outage during render/export/revocation; critical flows fail closed.

Acceptance criteria

All WEL-75 acceptance criteria are met.

No audit ingestion path stores raw PHI text by default.

There is no update/delete application API for audit events.

Database permissions prevent application update/delete of audit rows.

Grant revocation produces synchronous audit events and invalidates access predicates.

C10 output render can be reconstructed by event ID, render token ID, output hash, C10 decision, and source refs.

Notifications are generated only through approved policies and templates.

Delivery attempts are retried with backoff and audited.

Patient audit query supports patient, event type, and time range filters with redaction.

1.19 C12 open risks and trade-offs

Risk or trade-off

Recommendation

Event volume can become expensive.

Use event family sampling only for non-critical high-volume API accepts; never sample trust/safety/export/access denial events.

Hash chains complicate partitioning.

Use per-subject streams plus daily roots; avoid one global serial bottleneck.

Patient transparency can create anxiety.

Use redacted summaries and digests; avoid push for routine access.

PHI may leak through metadata.

Classify filenames, free-text labels, search terms, and notification variables as potentially sensitive.

Restricted text retention may expand over time.

Require TTL, reason codes, approvals, and metrics for every retained text ref.

Legal retention varies by jurisdiction.

Keep retention configurable and require legal sign-off before production.

Institution/research transparency can raise re-identification risk.

Provide consent-level summaries, not granular query details.

1.20 C12 assumptions requiring approval

Patient-visible audit will show redacted summaries, not full internal payloads.

Push/SMS/email notifications will not include raw PHI unless a separate channel policy explicitly permits it.

C10 blocked/fail-closed events will not generate push notifications by default.

Restricted text retention default TTL will be 30 to 90 days unless legal hold or approved safety case applies.

Audit write failure blocks critical flows: grant revocation success, non-owner access approval, export completion, and AI output render.

Final retention periods require legal/privacy approval by jurisdiction.

Section 2 - C13 Versioned API and Contract Boundary

2.1 Executive recommendation

Approve a hybrid versioning model:

Keep /v1 stable for existing MVP Health Thread and ShareGrant behavior.

Introduce /v2 for Investigation, Theory, External Evidence relevance, Workspace, Role, Grant, AccessPredicate, RenderApproval, and AuditRef resources.

Include schema_version in every DTO.

Optionally support media type application/vnd.wellbe.v2+json, but do not rely on media-type negotiation as the primary versioning mechanism.

Do not add v2-sensitive fields to v1 responses.

This is the safest choice because new primitives carry new authorization, provenance, safety, external-context, and non-diagnosis semantics. Path versioning gives explicit routing, explicit generated clients, simpler browser/debug behavior, and lower risk of old clients silently ignoring safety-critical fields.

2.2 Recommended versioning strategy

2.2.1 Decision

Use:

/v1/... for current MVP resources.

/v2/... for new contract resources.

schema_version in every v2 request and response object.

RFC 9457-style Problem Details for all errors.

OpenAPI 3.1.1 documents generated separately for v1 and v2.

2.2.2 Migration rules

Existing v1 endpoints remain backward compatible until formally deprecated.

v1 ShareGrant can be internally mapped to v2 Grant, but v1 clients receive only v1-safe fields.

v2 capabilities are default-false. Missing capability means denied.

Unknown authorization fields in requests fail closed with unknown_authorization_field.

Unknown display fields in responses may be ignored by clients only if marked non-authoritative.

Adding optional non-sensitive fields is a minor version change.

Adding required fields, changing authorization meaning, or changing safety semantics requires a new endpoint or future major version.

Deprecated fields must include deprecated: true, replacement field, and removal target in OpenAPI.

2.3 Alternatives considered for C13

Strategy

Decision

Rationale

/v2 path versioning only

Adopt as primary.

Clear, simple, generated-client friendly, low ambiguity.

Media-type versioning only

Reject as primary.

Harder for browsers, debugging, gateway rules, and generated clients.

Resource-level schema_version only

Reject as primary.

Unsafe because old clients can silently ignore new required safety fields.

Hybrid path plus schema version

Adopt.

Explicit routing plus machine-checkable DTO versions.

Add v2 fields to v1 responses

Reject.

Old clients may misinterpret Theory, external evidence, or grant fields.

2.4 C13 base DTOs

2.4.1 Common rules

All v2 DTOs must include:

schema_version.

Stable resource identifier.

created_at and/or updated_at where applicable.

audit_refs for write, render, export, share, or access-sensitive responses.

No raw PHI fields unless the endpoint is explicitly authorized and documented.

No diagnosis, ranked differential, disease probability, or unsupported clinical recommendation fields.

Security-sensitive DTOs should use additionalProperties: false in OpenAPI/Pydantic. Clients should treat unknown authorization and safety fields as fail-closed.

2.4.2 AuditRefV2

{
  "schema_version": "c13.audit_ref.v2",
  "audit_event_id": "aud_...",
  "correlation_id": "corr_...",
  "trace_id": "00-...",
  "visibility": ["controller_visible"],
  "event_summary": "Grant was revoked"
}

Rules:

Include AuditRefV2 on responses for grant changes, workspace membership changes, comments/contributions, exports, render events, investigation/theory status changes, consent changes, and denial responses when an audit event was written.

Do not expose admin/security-only details through event_summary.

2.4.3 SourceRefV2

{
  "schema_version": "c13.source_ref.v2",
  "source_ref_id": "src_...",
  "component": "c2|c5|c16",
  "provenance_id": "prov_...",
  "source_hash": "sha256:...",
  "display_label": "Lab result, May 2026",
  "source_scope": "personal|external",
  "access_required": ["raw_context.read"]
}

Rules:

Every derived claim returned by C13 must include source refs or be rejected with provenance_missing.

display_label must be safe for the requesting role.

Raw source paths and mutable blob URLs are forbidden.

2.4.4 C10ObligationV2

{
  "schema_version": "c13.c10_obligation.v2",
  "obligation_code": "show_sources|show_not_diagnosis|show_urgent_next_step",
  "required": true,
  "display_location": "inline|banner|source_panel",
  "blocking_if_unfulfilled": true
}

Rules:

UI must prove it can fulfill blocking obligations before render.

If obligations cannot be fulfilled, C13 returns c10_obligations_unfulfilled and does not render.

2.5 Investigation contract

2.5.1 InvestigationV2

{
  "schema_version": "c13.investigation.v2",
  "investigation_id": "inv_...",
  "health_thread_ids": ["thr_..."],
  "primary_question": "What patterns might explain these recurring symptoms?",
  "scope": {
    "included_thread_ids": ["thr_..."],
    "excluded_categories": ["unrelated_history"],
    "time_window": {"from": "2026-01-01", "to": null}
  },
  "status": "active",
  "safety_level": "routine|watch|caution|urgent_route_active",
  "workspace_id": "wrk_...",
  "participants": [],
  "evidence_bundle_ref": "evb_...",
  "linked_theory_ids": ["thy_..."],
  "missing_context_items": [],
  "pending_items": [],
  "review_cadence": null,
  "created_by": {"role_type": "controller", "actor_ref": "usr_hash_..."},
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "audit_refs": []
}

2.5.2 Required, optional, forbidden

Field category

Fields

Required

schema_version, investigation_id, health_thread_ids, primary_question, scope, status, safety_level, workspace_id, evidence_bundle_ref, created_by, created_at, updated_at.

Optional

participants, linked_theory_ids, missing_context_items, pending_items, review_cadence, external_context_refs, audit_refs.

Forbidden

diagnosis, ranked_differential, disease_probability, treatment_plan, clinical_order, full_patient_record_access.

2.5.3 Status values

Allowed InvestigationStatusV2 values:

draft

active

waiting_for_context

waiting_for_review

monitoring

ready_to_close

closed_resolved

closed_explained

closed_monitoring

closed_handed_off

closed_no_action

reopened

archived

Do not use diagnosed, ruled_out, confirmed_disease, or treated as Investigation statuses.

2.5.4 Unknowns and missing context

Use MissingContextItemV2:

{
  "schema_version": "c13.missing_context_item.v2",
  "missing_context_item_id": "mci_...",
  "question": "When did this pattern first appear?",
  "why_relevant": "It may help compare timing across sources.",
  "status": "open|answered|not_available|not_needed",
  "owner_role": "controller|clinician|caregiver|system",
  "source_refs": []
}

Unknowns should be represented as missing context or open questions, not as implied diagnoses.

2.5.5 Summary rendering rule

An Investigation summary may be returned only if:

C1/C17 authorization succeeds for the requested purpose.

Every derived claim has C5 source refs.

C6 semantics contain no diagnosis-like node/edge claims.

External evidence is marked context-only.

C10 allows the exact summary text and C13 verifies the render token/output hash.

C12 emits output render audit.

2.6 Theory contract

2.6.1 TheoryV2

{
  "schema_version": "c13.theory.v2",
  "theory_id": "thy_...",
  "investigation_id": "inv_...",
  "health_thread_id": "thr_...",
  "label": "A possible pattern related to sleep timing",
  "proposed_by": {"role_type": "controller", "actor_ref": "usr_hash_..."},
  "status": "proposed",
  "safety_level": "routine|watch|caution",
  "evidence_for": [],
  "evidence_against": [],
  "missing_data": [],
  "external_context_refs": [],
  "review_marker": null,
  "clinician_annotation_ref": null,
  "not_diagnosis": true,
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "audit_refs": []
}

2.6.2 Allowed status values

Allowed TheoryStatusV2 values:

proposed

needs_more_context

consistent_with_available_context

less_consistent_with_available_context

not_enough_information

superseded

closed_not_pursued

clinician_recorded

archived

Forbidden status values include diagnosed, confirmed, likely, ruled_out, differential_rank_1, and disease_probability_high.

2.6.3 Evidence entries

Use EvidenceLinkV2:

{
  "schema_version": "c13.evidence_link.v2",
  "evidence_link_id": "evl_...",
  "role": "for|against|missing",
  "claim_ref": "claim_...",
  "source_refs": [],
  "summary": "This source is consistent with the timing pattern.",
  "confidence_bucket": "low|medium|high",
  "not_diagnosis": true
}

confidence_bucket describes confidence in extraction/linking, not disease likelihood.

2.6.4 Clinician-entered diagnosis

If a clinician-entered diagnosis appears in imported records or a clinician workspace, do not represent it as a WellBe diagnosis. Represent it as SourcedRecordFindingV2 or ClinicianAnnotationRefV2:

{
  "schema_version": "c13.sourced_record_finding.v2",
  "finding_id": "find_...",
  "record_type": "external_clinician_assessment",
  "recorded_by_role": "clinician",
  "source_refs": [],
  "verbatim_label_allowed": false,
  "display_label": "Clinician-recorded assessment in source record",
  "not_wellbe_diagnosis": true
}

Verbatim clinical labels can be displayed only if access, provenance, and safety rules allow it.

2.7 External Evidence and Relevance contract

2.7.1 ExternalSourceRefV2

{
  "schema_version": "c13.external_source_ref.v2",
  "external_source_id": "extsrc_...",
  "source_quality_tier": "tier_1|tier_2|tier_3|tier_4|tier_5",
  "source_type": "guideline|systematic_review|peer_reviewed_article|clinical_reference|general_health_info|unverified",
  "publisher": "publisher_ref_or_display_label",
  "publication_date": "2025-11-01",
  "retrieved_at": "2026-06-01T12:00:00Z",
  "source_url_ref": "urlref_...",
  "display_label": "External source title or safe label",
  "context_only": true,
  "not_personal_evidence": true,
  "audit_refs": []
}

2.7.2 Source-quality tier policy

Tier

Meaning

Default display

tier_1

High-quality guideline, systematic review, or authoritative source.

Allowed as context with source label.

tier_2

Peer-reviewed or high-quality clinical source.

Allowed as context with source label.

tier_3

Reputable clinical reference or educational source.

Allowed with context-only obligation.

tier_4

General health information or lower certainty source.

Digest/surface cautiously with quality label.

tier_5

Low-quality, unverified, promotional, anecdotal, or unsafe source.

Hidden by default; sandbox-only with warning.

2.7.3 RelevanceLinkV2

{
  "schema_version": "c13.relevance_link.v2",
  "relevance_link_id": "rel_...",
  "external_source_id": "extsrc_...",
  "external_claim_id": "extclaim_...",
  "linked_thread_id": "thr_...",
  "linked_investigation_id": "inv_...",
  "relevance_status": "candidate|visible_context|hidden_low_quality|rejected|sandbox_only",
  "why_relevant_summary": "This source may provide general context for a question in the investigation.",
  "source_quality_tier": "tier_2",
  "context_only": true,
  "not_personal_evidence": true,
  "obligations": ["show_context_only_label"],
  "created_at": "2026-06-01T12:00:00Z",
  "evaluated_at": "2026-06-01T12:00:00Z",
  "audit_refs": []
}

Rules:

context_only and not_personal_evidence are required and must be true.

C13 rejects any request that attempts to place external evidence in evidence_for or personal_fact_support without context-only marking.

Tier 5 is omitted from normal user-facing responses unless the endpoint is an explicit sandbox surface.

UI must display context-only obligations near the source.

2.8 Workspace, Role, Grant, and AccessPredicate contracts

2.8.1 WorkspaceV2

{
  "schema_version": "c13.workspace.v2",
  "workspace_id": "wrk_...",
  "workspace_type": "personal|clinician_shared|caregiver_shared|institution_aggregate|research_sandbox",
  "display_name": "Visit preparation workspace",
  "controller_subject_ref": "subj_hash_...",
  "membership_state": "active|invited|removed|suspended",
  "active_role_binding": null,
  "capability_summary": {},
  "data_access_not_implied": true,
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "audit_refs": []
}

Rule: workspace membership never authorizes data access. data_access_not_implied=true is required in v2 workspace responses.

2.8.2 RoleBindingV2

{
  "schema_version": "c13.role_binding.v2",
  "role_binding_id": "rb_...",
  "workspace_id": "wrk_...",
  "role_type": "controller|clinician|caregiver|institution_admin|researcher|service",
  "principal_ref": "principal_hash_or_org_ref",
  "state": "active|deactivated|expired|suspended",
  "starts_at": "2026-06-01T12:00:00Z",
  "expires_at": null,
  "audit_refs": []
}

2.8.3 GrantV2

{
  "schema_version": "c13.grant.v2",
  "grant_id": "grt_...",
  "grant_type": "thread_scope|investigation_scope|workspace_scope|aggregate_scope|research_protocol_scope",
  "subject_ref": "patient_hash_...",
  "grantee_ref": "principal_hash_or_org_ref",
  "workspace_id": "wrk_...",
  "role_binding_id": "rb_...",
  "scope_codes": ["investigation.read"],
  "scope_profile_version": "scope.profile.2026-06-01",
  "purpose_code": "visit_prep",
  "status": "active|expired|revoked|superseded|pending_acceptance",
  "starts_at": "2026-06-01T12:00:00Z",
  "expires_at": "2026-06-15T12:00:00Z",
  "revoked_at": null,
  "capabilities": {
    "can_read": true,
    "can_search": false,
    "can_comment": true,
    "can_export": false,
    "can_invite": false,
    "can_contribute": false,
    "can_request_correction": false,
    "can_view_external_context": true,
    "can_run_aggregate": false,
    "can_use_research_sandbox": false
  },
  "contribution_policy": {
    "mode": "annotation_only|propose_changes|controller_acceptance_required",
    "permanent_changes_require_controller_acceptance": true
  },
  "resource_constraints_summary": "Limited to investigation inv_... and linked sources.",
  "obligations": [],
  "created_at": "2026-06-01T12:00:00Z",
  "updated_at": "2026-06-01T12:00:00Z",
  "audit_refs": []
}

Rules:

Capabilities are default-false.

can_export, can_invite, and can_contribute are policy decisions, not raw booleans copied from the client.

Raw resource_filters are internal-only by default; clients receive resource_constraints_summary and scoped links.

A revoked grant must never be returned as active.

2.8.4 AccessPredicateV2

{
  "schema_version": "c13.access_predicate.v2",
  "access_predicate_hash": "sha256:...",
  "decision": "allow|deny|allow_with_obligations",
  "decision_reason_codes": [],
  "grant_id": "grt_...",
  "workspace_id": "wrk_...",
  "role_binding_id": "rb_...",
  "purpose_code": "visit_prep",
  "scope_codes": ["investigation.read"],
  "capabilities": {},
  "resource_constraints_summary": "Limited to investigation inv_...",
  "obligations": [],
  "valid_until": "2026-06-01T12:10:00Z",
  "policy_version": "c1.policy.2026-06-01",
  "evaluated_at": "2026-06-01T12:00:00Z",
  "audit_event_id": "aud_..."
}

Rules:

C13 may return AccessPredicateV2 or a reference to it only when useful to the client. It should not expose raw ABAC rules or full resource filters to ordinary clients.

Unknown predicate fields or policy versions in a client request fail closed.

AccessPredicate validity must be short-lived and invalidated by grant revocation.

2.9 C10 render token and output contract

2.9.1 RenderApprovalV2

{
  "schema_version": "c13.render_approval.v2",
  "render_authorization_ref": "rar_...",
  "render_token": "opaque_optional_server_controlled_token",
  "binds_request_id": "req_...",
  "binds_text_sha256": "sha256:...",
  "expires_at": "2026-06-01T12:05:00Z",
  "c10_decision": "allow|allow_with_obligations|rewrite_required|block|route_urgent|manual_review_required|fail_closed",
  "obligations": [],
  "reason_codes": [],
  "review_markers": [],
  "source_display_requirements": [],
  "audit_event_id": "aud_..."
}

2.9.2 Token exposure recommendation

C13 should keep signed C10 render tokens server-side when possible and return render_authorization_ref to browser clients. Service-to-service clients may receive an opaque render_token if required. The token must never be generated by the client and must never authorize different text from the exact hash C10 evaluated.

2.9.3 Rendering rules

C13 must:

Hash the exact bytes of the text to be rendered.

Verify the C10 token signature, expiry, request binding, role binding, and binds_text_sha256.

Verify that all C10 obligations can be fulfilled by the UI surface.

Emit c13.render_token.verified and c13.output.rendered before returning output.

Return c10_token_required, c10_token_hash_mismatch, or c10_obligations_unfulfilled when validation fails.

If the UI cannot show sources, disclaimers, urgent next steps, or context-only external-evidence labels, C13 must not render the output.

2.10 Endpoint families and minimum required routes

2.10.1 MVP scaffolding routes

Route

Purpose

MVP?

GET /v2/schema

Advertise supported contract versions.

Yes.

POST /v2/access/evaluate

Internal/trusted access predicate evaluation.

Yes, internal/trusted.

GET /v2/workspaces

List workspaces visible to requester.

Yes minimal.

GET /v2/workspaces/{workspace_id}

Workspace metadata, no implied data access.

Yes minimal.

GET /v2/grants

List grants scoped to requester/controller.

Yes.

POST /v2/grants

Create grant.

Yes if sharing MVP exists.

POST /v2/grants/{grant_id}/revoke

Revoke grant synchronously.

Yes.

GET /v2/investigations

List authorized investigations.

Yes minimal.

POST /v2/investigations

Create investigation.

Yes minimal.

GET /v2/investigations/{investigation_id}

Get authorized investigation.

Yes minimal.

PATCH /v2/investigations/{investigation_id}

Update allowed fields.

Yes minimal.

POST /v2/investigations/{investigation_id}/close

Close investigation.

Yes minimal.

POST /v2/investigations/{investigation_id}/reopen

Reopen investigation.

Yes minimal.

GET /v2/investigations/{investigation_id}/theories

List theories.

Yes minimal.

POST /v2/investigations/{investigation_id}/theories

Create theory.

Yes minimal.

GET /v2/theories/{theory_id}

Get theory.

Yes minimal.

PATCH /v2/theories/{theory_id}

Update theory status/evidence refs.

Yes minimal.

GET /v2/investigations/{investigation_id}/external-context

List context-only external refs.

Yes minimal.

POST /v2/render/validate

Validate render approval for exact text.

Yes internal/trusted.

GET /v2/audit/my-events

Controller-visible audit timeline.

Yes if C12 MVP.

2.10.2 Post-MVP routes

Full workspace member management and invite endpoints.

Comment and contribution lifecycle endpoints.

External evidence search/watch subscription endpoints.

Institution aggregate query and export endpoints.

Research sandbox query/export endpoints.

Webhooks for grant lifecycle, export completion, and research watch results.

Admin/security audit review endpoints.

2.11 Backward compatibility for v1 clients

v1 Health Thread responses remain unchanged unless a change is strictly backward compatible and not safety-sensitive.

v1 ShareGrant remains compatible and maps internally to v2 Grant with conservative defaults.

v1 does not expose Investigation, Theory, ExternalEvidenceRef, RelevanceLink, AccessPredicate internals, C10 render tokens, or deep grant fields.

v1 clients cannot render AI-generated health output unless they use a v2 render path or a server-side compatibility wrapper that enforces C10.

No v1 endpoint should return external evidence in a way that can be read as personal proof.

New v2 capabilities default false when mapped from v1.

Deprecation notices should use headers and documentation, not silent behavior changes.

2.12 Required C1/C5/C10/C12/C6 integration checks

2.12.1 Synchronous checks inside C13

C13 must synchronously enforce:

Authentication and principal resolution.

C1/C17 access predicate evaluation before data retrieval or mutation.

Revocation state and short-lived predicate validity.

Capability checks for comment, export, invite, contribution, aggregate, and research actions.

C10 token/hash validation before rendering AI output.

C12 audit write for critical access/render/export/share/revocation paths.

Basic request schema validation and forbidden field rejection.

2.12.2 Delegated service checks

C13 delegates but verifies outcomes:

C5 provenance validation and no-orphan-claim enforcement.

C6 graph semantic constraints and no diagnosis-like edges.

C14 Investigation lifecycle state transitions.

C15 Theory state and evidence role semantics.

C16 source-quality tiering and context-only relevance.

C10 safety evaluation itself.

C12 append-only storage and notification derivation.

2.12.3 Fail-closed conditions

C13 must fail closed when:

C1 is unavailable or returns unknown policy result.

Grant is missing, expired, revoked, or scope/capability denied.

Workspace membership is present but no active grant authorizes the action.

C10 token is missing, expired, invalid, or mismatched to text hash.

C10 obligations cannot be fulfilled.

Provenance is missing for derived claims.

External evidence is requested as personal proof.

Theory or graph content violates non-diagnosis semantics.

Institution/research request would return patient identifiers or individual-level data without valid consent/governance.

C12 audit write fails for critical flows.

Client sends unknown authorization fields.

2.13 Required request flows

2.13.1 Workspace read

C13 authenticates principal and resolves requested workspace.

C13 checks membership only as a workspace relationship, not as data authority.

C13 calls C1/C17 for AccessPredicate with action, purpose, role, resource, and workspace.

C12 records access predicate evaluation and access allowed or denied.

C13 fetches allowed data from C14/C15/C16/C6 using predicate constraints.

C5 validates source refs for derived claims.

C13 redacts fields by role and capabilities.

C13 returns v2 DTOs with audit refs.

2.13.2 AI-generated Investigation summary

C13 resolves access through C1.

C13 gathers scoped evidence and source refs.

Candidate text is generated by the appropriate engine.

C13 sends candidate, source refs, role, purpose, and risk context to C10.

C10 returns decision and render authorization for exact output hash, or blocks/routes/fails closed.

C13 verifies token/hash and obligations.

C13 emits C12 render events.

C13 returns output with sources, obligations, and audit ref.

2.13.3 Visit Packet export

Requester asks for export with purpose and scope.

C13 calls C1 and requires can_export=true.

C13 emits export.requested audit.

C13 builds export from C2/C5/C14/C15/C16 refs; no orphan claims.

Any generated narrative passes C10 and render-token verification.

Export snapshot is stored with hash and expiry.

C13 emits export completed and download delivered audit.

User receives closure-oriented export-ready notification.

2.13.4 Institution aggregate summary

Institution principal authenticates to aggregate workspace.

C13 verifies aggregate-only entitlement, institution role, and user consent prerequisites.

C13 denies any patient identifier or row-level request.

Aggregation service applies minimum cell thresholds and suppression policy.

C12 records aggregate query/export without patient identifiers in institution-facing path.

C13 returns aggregate result only.

2.13.5 Research sandbox output

Researcher authenticates to protocol workspace.

C13 verifies global cross-patient prerequisite and protocol-level consent.

Query executes inside governed sandbox.

C13/C12 record query and export metadata under protocol audit.

Outputs pass de-identification/suppression checks.

AI-generated summaries pass C10 if user-facing or human-facing health claims are generated.

C13 returns only approved sandbox output.

2.14 Error-code and HTTP-status mapping

Errors should use RFC 9457-style Problem Details:

{
  "type": "https://api.wellbe.example/problems/grant-revoked",
  "title": "Grant has been revoked",
  "status": 403,
  "code": "grant_revoked",
  "detail": "The requested action is not authorized by an active grant.",
  "correlation_id": "corr_...",
  "audit_event_id": "aud_...",
  "remediation": "Ask the controller to create a new grant if access is still needed."
}

Recommended codes:

Code

HTTP

Meaning

grant_required

403

No active grant or controller entitlement authorizes the action.

grant_expired

403

Matching grant exists but is expired.

grant_revoked

403

Matching grant exists but is revoked.

scope_denied

403

Grant exists but scope does not cover resource/action.

capability_denied

403

Action requires capability not granted.

active_role_required

403

Principal lacks active role binding for requested workspace/action.

workspace_membership_not_access

403

Membership exists but does not authorize data access.

c10_token_required

428

User-facing AI output requires valid C10 render authorization.

c10_token_hash_mismatch

409

Token does not bind to exact output text hash.

c10_obligations_unfulfilled

409

UI/client cannot fulfill C10 display obligations.

provenance_missing

422

Derived claim lacks required source/provenance refs.

external_context_only_violation

422

External evidence was requested or represented as personal proof.

theory_diagnosis_violation

422

Theory request uses diagnosis/ranked differential semantics.

institution_aggregate_only_violation

403

Institution request would expose individual-level or identifying data.

cross_patient_opt_in_required

403

Cross-patient use lacks global opt-in prerequisite.

research_protocol_consent_required

403

Protocol-level research consent is missing.

audit_write_failed

503

Critical audit write failed; operation did not complete.

export_requires_capability

403

Export requested without can_export.

unknown_contract_version

400 or 406

Unsupported version in path/body or unacceptable media type.

unknown_authorization_field

400

Client supplied unrecognized authorization/safety field.

render_token_expired

409

Render token expired before output render.

render_token_invalid

403

Render token signature or binding invalid.

policy_unavailable

503

C1/C10 policy service unavailable; request failed closed.

audit_ref_unavailable

503

Required audit reference could not be produced.

2.15 Field-level rules

Field type

Rule

schema_version

Required in every v2 DTO.

IDs

Use opaque IDs or hashed refs; no raw patient UUIDs in institution/research paths.

capabilities

Default false; absence means denied.

resource_filters

Internal-only; ordinary clients receive constrained links or summaries.

access_predicate_hash

Required on access-sensitive responses and audit events; raw predicate optional/trusted only.

context_only

Required true for external evidence and relevance links.

not_personal_evidence

Required true for external evidence and relevance links.

not_diagnosis

Required true for Theory responses.

source_refs

Required for every derived claim, summary, evidence link, and sourced record finding.

render_token

Server-side or opaque; never client-created; exact hash binding required.

audit_refs

Required for mutation, render, export, share, consent, and grant responses.

Free text labels

Must be role-filtered and may require C10 if AI-generated or health-facing.

Clinician diagnosis labels

Allowed only as sourced record/annotation, never as WellBe diagnosis.

Institution patient identifiers

Forbidden by default.

Cross-patient outputs

Forbidden unless global opt-in and protocol/aggregate governance pass.

2.16 OpenAPI and generated-client strategy

Use OpenAPI 3.1.1 and JSON Schema 2020-12 compatibility.

Maintain separate openapi-v1.yaml and openapi-v2.yaml artifacts.

Generate clients into separate namespaces, for example wellbe.api.v1 and wellbe.api.v2.

Add vendor extensions:

x-wellbe-component

x-wellbe-phi-classification

x-wellbe-access-required

x-wellbe-c10-required

x-wellbe-audit-required

x-wellbe-context-only

x-wellbe-not-diagnosis

Use additionalProperties: false for authorization, grant, render, and safety DTOs.

Generate contract tests from the OpenAPI spec.

Lint OpenAPI for forbidden field names: diagnosis, differential_rank, disease_probability, personal_proof_from_external_evidence, full_patient_access.

Include negative examples in OpenAPI for external evidence overclaim, missing C10 token, and revoked grant.

Publish a compatibility matrix for v1 and v2 clients.

2.17 MVP, post-MVP, and deferred boundary for C13

Must exist before C1-C6 alignment can be considered clean

/v2 DTO stubs for AccessPredicate, Workspace, RoleBinding, Grant, Investigation, Theory, ExternalSourceRef, RelevanceLink, RenderApproval, and AuditRef.

Stable error-code contract.

C1 access predicate enforcement at C13 boundary.

C5 provenance-required response model.

C6 non-diagnosis semantics in public DTOs.

C16 context-only external evidence model.

C12 audit references for critical responses.

v1 compatibility guardrails so old clients do not receive unsafe new fields.

Must exist before WEL-74/C10 can be fully integrated

C13 render-token verification.

Exact output hash binding.

C10 obligations returned to UI and enforced before render.

c10_token_required, c10_token_hash_mismatch, and c10_obligations_unfulfilled errors.

C12 audit events for C10 decision and C13 render.

Must exist before clinician/shared workspaces

Workspace membership model with data_access_not_implied=true.

RoleBinding and Grant v2 contracts.

AccessPredicate return/reference model.

Comment/contribution lifecycle contracts.

Grant revocation route with synchronous audit.

Export capability enforcement.

Must exist before institution/research workspaces

Aggregate-only institution DTOs.

Global cross-patient opt-in checks.

Protocol-level research consent checks.

Suppression/de-identification metadata.

Research/institution C12 audit event contracts.

No patient identifier fields in institution-facing OpenAPI schemas.

Post-MVP

Full clinician workspace endpoint suite.

Full generated TypeScript client for all v2 resources.

Full institution aggregate APIs.

Full research sandbox APIs.

Webhook delivery and retry contracts.

Patient downloadable audit timeline.

Deferred

Full FHIR/SMART-on-FHIR API compatibility.

Public transparency log anchoring.

Cross-organization audit federation.

Dynamic AI-generated notification copy for sensitive events.

2.18 C13 implementation notes

Implement C13 route dependencies/middleware that require C1 evaluation before handler code can fetch data.

Use typed Pydantic DTOs from backend/packages/contracts as the only response models.

Make unsafe fields impossible to serialize by excluding them from public DTOs.

Use AuditRefV2 returned from C12 as part of write responses.

Treat C12 audit write as part of the transaction boundary for critical flows.

Keep C10 render approval validation in one shared utility; do not duplicate token logic per endpoint.

Keep a contract-level enum registry for status values, source tiers, capabilities, purpose codes, and error codes.

Add golden OpenAPI snapshots in CI.

Add compatibility tests proving v1 schemas do not include v2-only fields.

2.19 C13 test plan and acceptance criteria

Test plan

Version routing tests. v1 and v2 routes return distinct schemas; v1 never returns v2-only fields.

OpenAPI generation tests. OpenAPI 3.1.1 files validate and generated clients compile.

Access tests. Every read/search/comment/export/invite/contribution route calls C1 and fails closed on denied, expired, revoked, or unavailable policy.

Membership-not-access tests. Workspace member without grant receives workspace_membership_not_access.

Capability tests. can_export=false, can_invite=false, and can_contribute=false block respective actions.

C10 render tests. Missing token, expired token, hash mismatch, unfulfilled obligations, and post-C10 mutation all block render.

Provenance tests. Derived claim without source refs returns provenance_missing.

Theory safety tests. Diagnosis/ranked differential/probability fields return theory_diagnosis_violation.

External evidence tests. External evidence as personal proof returns external_context_only_violation.

Institution tests. Individual identifiers in aggregate response schema are impossible; request returns institution_aggregate_only_violation.

Research tests. Missing global opt-in or protocol consent returns required consent error.

Audit tests. Critical response includes audit_refs; simulated C12 outage returns audit_write_failed and operation does not complete.

Error shape tests. All errors conform to Problem Details plus WellBe code, correlation_id, and optional audit_event_id.

Unknown field tests. Unknown authorization or safety fields fail closed.

Acceptance criteria

/v2 OpenAPI includes all required DTOs and errors.

C13 blocks user-facing AI output without valid C10 render authorization bound to exact output hash.

C13 cannot return a derived claim without source refs.

C13 cannot return external evidence as personal evidence.

C13 cannot expose Theory as diagnosis.

C13 cannot treat workspace membership as data access.

C13 critical actions produce C12 audit refs.

v1 compatibility tests pass and v1 clients do not receive v2-only fields.

2.20 C13 open risks and trade-offs

Risk or trade-off

Recommendation

/v2 duplicates some v1 routes.

Accept for clarity and safety; share service internals to reduce drift.

Strict DTOs slow client iteration.

Accept for safety-critical fields; use optional display-only extension fields where safe.

Server-side render tokens complicate architecture.

Prefer server-side for web; allow opaque token for trusted clients only.

Generated clients may ignore obligations.

Make obligations blocking server-side; do not trust client display alone.

Error codes may reveal policy details.

Provide user-safe details; keep internal reason details in audit.

Institution/research schemas may be underpowered.

Start conservative; expand after governance and re-identification review.

v1 clients may still need AI output.

Provide a server-side compatibility wrapper that enforces v2 C10 render rules without exposing v2 fields.

2.21 C13 assumptions requiring approval

/v2 path versioning is acceptable for new resources.

Media-type versioning is optional, not primary.

schema_version is mandatory in every v2 DTO.

C13 may fail closed when C1, C10, or C12 are unavailable on critical paths.

Browser clients should receive render authorization refs rather than raw signed C10 tokens where feasible.

v1 clients will not receive Investigation, Theory, External Evidence relevance, AccessPredicate internals, or deep grant fields.

Institution and research APIs can remain post-MVP, with scaffolding schemas approved now.

Appendix A - Decision record snippets

A.1 C12 decision snippet

Decision. WellBe will implement C12 as an append-only, tamper-evident audit ledger and a policy-driven closure-oriented notification service. C12 audit rows are immutable; sensitive content is minimized; full PHI text and candidate AI output are not stored on the audit backbone by default. C12 records C1/C17 grants and access, C2 raw context operations, C3 ingestion, C4 processing, C5 provenance, C6 graph semantics, C10 safety decisions, C13 render/API/export events, and C14-C16 Investigation/Theory/External Evidence events. Notifications are generated from approved policy and templates and must avoid diagnosis, alarmism, false reassurance, and clinician blame.

Consequences. Critical flows fail closed if required audit writes fail. C12 requires insert-only database permissions, payload classification, hash chains, notification delivery audit, and redacted patient query APIs.

A.2 C13 decision snippet

Decision. WellBe will keep /v1 stable and introduce /v2 path-versioned resources for new Investigation, Theory, External Evidence relevance, Workspace, Role, Grant, AccessPredicate, C10 RenderApproval, and C12 AuditRef contracts. Every v2 DTO includes schema_version. C13 is the single public contract boundary and must enforce C1/C17 authorization, C5 provenance, C6 non-diagnosis graph semantics, C10 render-token validation, C16 context-only external evidence, and C12 audit emission.

Consequences. v1 clients do not receive v2-only fields. New safety or authorization semantics require v2 routes. Errors use stable WellBe codes in Problem Details format.

Appendix B - Reference notes

The following references support the general design choices. They do not override WellBe product constraints.

[R1] HL7 FHIR AuditEvent describes a record of an event relevant to operations, privacy, security, maintenance, and performance analysis, and is a useful health-domain reference for audit event shape.

[R2] NIST SP 800-92 describes computer security log management across generation, transmission, storage, analysis, and disposal.

[R3] OWASP Logging Cheat Sheet emphasizes that logs can contain sensitive information and recommends excluding, masking, sanitizing, hashing, or encrypting sensitive data as appropriate.

[R4] HHS HIPAA Security Rule technical safeguards include access controls and audit controls for systems maintaining electronic protected health information.

[R5] CloudEvents provides a common event envelope model for interoperability across services.

[R6] W3C Trace Context defines HTTP trace context propagation using trace-related headers for distributed tracing.

[R7] OpenAPI Specification 3.1.1 is the recommended API description baseline for C13 generated clients and schema contracts.

[R8] RFC 9457 defines Problem Details for HTTP APIs and obsoletes RFC 7807.

[R9] RFC 9110 defines HTTP semantics, including methods, status codes, and core concepts.

[R10] NIST AI Risk Management Framework is a general reference for AI risk governance and should be considered supportive context for C10/C12/C13 controls.

Appendix C - Source URLs

R1: https://fhir.hl7.org/fhir/auditevent.html

R2: https://csrc.nist.gov/pubs/sp/800/92/final

R3: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

R4: https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312

R5: https://cloudevents.io/

R6: https://www.w3.org/TR/trace-context/

R7: https://spec.openapis.org/oas/v3.1.1.html

R8: https://www.rfc-editor.org/rfc/rfc9457.html

R9: https://datatracker.ietf.org/doc/rfc9110/

R10: https://www.nist.gov/itl/ai-risk-management-framework

