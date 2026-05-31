# Implementation roadmap

## Phase 0 — Align and refactor

- rename product architecture internally: Data Factory foundation + Health Thread layer
- add HealthThread, PendingItem, ThreadEvidenceLink, CorrectionRequest, ShareGrant schemas
- review all v1 features against personal-first guardrail
- build-forward on in-flight C7: include Investigation status hooks and the 6-step loop (Capture → Connect → Investigate → Clarify → Close → Correct)

## Phase 1 — MVP Health Thread

- Health Thread creation and timeline
- Story Memory intake
- evidence traceability layer
- normal-test safety-net copy rules
- pending result/referral tracker
- post-visit plan checker
- visit packet export/share

## Phase 2 — Longitudinal intelligence

- repeat-visit/persistence view
- missing context checklist
- baseline/function trend view
- patient-held record import
- medication/access context
- wearable trend summarizer

## Phase 2.5 — Investigation layer (Investigate step)

- Investigation object + Self Ongoing Investigation (C14)
- Theory object + Theory Evaluator (C15)
- External Evidence Graph + External Evidence Watch (C16) with source-quality tiers
- Live Metrics Safety Monitor (gated)
- Full Health Context Summary

## Phase 3 — Collaboration with guardrails

- deep Grant/Role model + Workspace layer (C17)
- Clinician Case Investigation Workspace (grant-scoped)
- Shared Health Thread workspace
- clinician-view share link
- care-team comments if user invited
- portal/lab import integrations
- referral pathway support

## Phase 4 — Advanced and regional modes

- Institution Continuity Intelligence (aggregate-only, consented) — governance gated
- Research Sandbox / cohort comparison — opt-in, protocol-governed
- low-resource/CHW/SMS mode where locally validated
- decision/uncertainty memory with governance
- cross-specialty map
- tightly controlled cross-patient comparison sandbox only with explicit opt-in
