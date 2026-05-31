# Core product objects

## Health Thread

The central object. A Health Thread represents one unresolved or ongoing concern. It contains story, timeline, data, uncertainty, pending items, corrections, and shareable summaries.

## Health Signal

A structured piece of health context: symptom, lab, wearable metric, medication change, mood entry, environmental factor, document fact, or user note. Signals do not become conclusions unless linked with evidence and context.

## Pending Item

A personal memory of an open loop: test result, referral, repeat test, appointment, safety-net instruction, document request, or follow-up check. Pending items must include status, due date if known, source, owner/contact if known, and next action.

## Visit Packet

A user-controlled clinician-readable summary for one Health Thread or visit. It is short by default and source-linked throughout.

## Correction Request

A user-authored repair to the Health Memory. It does not overwrite source data. It adds a new source-linked correction layer.

## Investigation

The active, structured research process around one or more Health Threads. A thread is the *concern*; an investigation is the *attempt* to understand, monitor, explain, or close it. A single thread may carry multiple investigations (personal, clinician, external-evidence watch, theory evaluation, post-visit follow-up, device-trend).

Fields:
- `id`
- `owner_type`: individual | clinician | shared | institution | research
- `linked_health_thread_ids[]`
- `primary_question`
- `status`: open | monitoring | waiting_for_data | ready_for_visit | handed_off | closed
- `scope`: flags for personal data / clinical documents / wearable data / external research / cross-patient comparison allowed
- `participants[]`: individual, caregiver, clinician, care team (each present only under a Grant)
- `evidence_bundle_ids[]`
- `active_theory_ids[]`
- `missing_context_items[]`
- `pending_item_ids[]`
- `safety_flags[]`
- `last_reviewed_at`, `next_review_due_at`
- `outputs`: patient summary, clinician packet, questions to ask, evidence map, unresolved items

Investigation status is governed by the lifecycle in `health_thread_state_machine.md` and never asserts a diagnosis.

## Theory

A user- or clinician-proposed explanation evaluated against available evidence. It is **never** a diagnosis, a ranked differential, or a disease claim.

Fields:
- `id`
- `created_by`: individual | clinician | system_suggested_question
- `linked_investigation_id`
- `theory_text`
- `theory_type`: symptom_trigger | medication_effect | lifestyle_factor | environmental_factor | clinical_condition_question | care_process_gap
- `evidence_for[]`, `evidence_against[]`, `missing_data[]`, `external_source_ids[]`
- `status`: unreviewed | needs_more_data | partially_supported | not_supported_by_current_data | contradicted_by_current_data | discuss_with_clinician | clinician_reviewed
- `safety_level`: low | needs_clinician_context | urgent_symptom_present | blocked_due_to_diagnostic_claim

## External Evidence Source

An item of external medical knowledge (guideline, paper, medical source, explainer, anecdote). Stored in the **External Evidence Graph**, never the personal Raw Context Vault. It carries a `source_quality_tier` (Tier 1 clinical guidelines … Tier 5 forums/anecdotes) and links to personal facts only through Relevance Links — it is context, never a fact about the user.

## Relevance Link

A typed edge connecting a personal fact to an External Evidence Source claim. It expresses "this external source discusses a similar pattern", carries a confidence and the source tier, and never imports the external claim into the personal graph.

## Workspace

A role-specific interface over the shared primitives. Types: Individual, Clinician Case Investigation, Shared Health Thread, Institution Continuity, Research Sandbox. A workspace can read or contribute to an individual's data only through an active Grant. The individual remains the data controller in every workspace.

## Role

The capacity in which a participant acts: individual (controller), caregiver, clinician, care team, institution, researcher. A Role never confers data control; it only defines which Grants a participant may be offered.

## Share Grant

A scoped, revocable permission that lets a recipient view selected thread context for a specific purpose and time window. The full grant model includes: `recipient_role`, `purpose`, `scope` (visit-packet-only | specific-thread | labs+symptoms | wearable-trends-only | full-investigation), `duration` / expiry, `can_comment`, `can_export`, `can_invite`, `contribution_becomes_permanent_record`, and `workspace_scope`. Institutions receive only aggregate, consented grants — never default individual-level access.
