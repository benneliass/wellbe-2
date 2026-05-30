# Research F — Product-design synthesis for a health-issue identification system

**Prepared from attached evidence packages only.**  
**Date:** 2026-05-30  
**Primary output:** product blueprint for identifying hidden, long-term, missed, delayed, or complex health issues.

## 0. Evidence base used

The synthesis uses five attached packages as the primary evidence base:

1. `research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz`
2. `research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz`
3. `research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz`
4. `research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz`
5. `research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz`

Combined structured evidence ingested: **164 sources, 154 evidence items, 117 cases/examples, 48 quotes, 38 reviews/complaints, 107 facts, and 39 metrics**. Consolidated row-level files are included in this output folder.

## 1. Product principles

|Principle|Meaning|
|---|---|
|Evidence over invention|Every feature must link to cases, quotes, workflow maps, source IDs, or package analysis. Unsupported concepts remain early ideas.|
|Longitudinal before episodic|Hidden and delayed conditions often appear as patterns across time, not single-visit abnormalities.|
|Closed loop or it is not done|Results, referrals, pending tests, screening positives, and patient concerns need owner, deadline, action, patient communication, and closure.|
|Protect patient voice without burdening clinicians|Preserve patient wording and concern, then transform it into concise, source-linked clinical summaries.|
|Support—not replace—clinical judgment|The system flags uncertainty, missing data, and unresolved patterns; it does not make final diagnoses.|
|Resource-aware and culture-aware by design|Workflows must differ across GP-gatekeeper, integrated HMO, fragmented, CHW-based, rural, multilingual, and low-resource settings.|
|Reduce alert fatigue by ranking actionability|Safety features must prioritize ownership gaps, deterioration, elapsed time, and red flags rather than adding undifferentiated reminders.|
|Measure safety both ways|Track false positives, false negatives, closed-loop completion, diagnostic outcomes, patient trust, equity, and clinician workload.|

## 2. Evidence-backed synthesis: facts vs interpretation

### Factual patterns from packages

- Diagnostic failure repeatedly occurs **across time and handoffs**, not only inside one clinician’s reasoning. Evidence appears in patient-flow, missed-signal, clinician, global, and complaint packages.
- Repeated unresolved visits, abnormal results not followed up, normal-test false reassurance, referral delay, poor handoff, incomplete history, and patient dismissal recur across multiple evidence types.
- Clinician workflow pain points include EHR alert overload, time pressure, note bloat, fragmented records, unclear ownership, triage overload, and fatigue.
- Patient voice evidence shows that phrases like “dismissed,” “not listened to,” “too young,” “normal,” and “still no idea” often map to concrete workflow breakdowns.
- Global evidence shows that diagnostic identification depends on system type and resources: CHW/informal-provider flows, rural access, language/cultural safety, cost, transport, diagnostic availability, and referral completion matter.

### Design interpretation

The product should not act as a diagnostic oracle. It should act as a **diagnostic continuity and communication layer** that helps patients express context and helps clinicians see longitudinal signals, unresolved questions, ownership gaps, and safety-net needs earlier.

## 3. Patient-facing workflow

|Step|Workflow|
|---|---|
|1. Before visit|Patient/caregiver enters symptoms, timeline, baseline change, main fear, own theory, prior visits/tests, family/prior history, language/access needs, and optional documents/photos.|
|2. Arrival/intake|System checks red flags, repeat visits, high-risk history, and missing critical fields; non-urgent uncertainty is kept open rather than discarded.|
|3. Visit support|Patient sees a “what I want addressed” list; clinician sees concise source-linked summary and can confirm/correct patient-entered data.|
|4. Diagnosis/status discussion|Visit closes each concern as confirmed/suspected/not yet explained/pending/watchful waiting, with plain-language safety net and uncertainty.|
|5. Tests/referrals/discharge|Patient receives pending-test contract, referral status, result owner, expected timing, and instructions for deterioration.|
|6. Follow-up/check-ins|Targeted check-ins ask whether symptoms resolved/worsened; persistent symptoms re-open the episode and route to owner/escalation.|
|7. Correction/escalation|Patient can correct visit summary, add missing records, or trigger deterioration escalation without replacing emergency services.|

## 4. Doctor-facing workflow

|Step|Workflow|
|---|---|
|1. Open chart|Doctor sees diagnostic episode summary: timeline, repeats, abnormal/pending results, referrals, patient concern, prior high-risk history, and missing data.|
|2. Intake review|Patient-entered data is labeled by source/provenance; clinician can accept, edit, suppress, or request clarification.|
|3. Assessment|System separates acuity from diagnostic uncertainty; red-flag and bias/misattribution prompts appear only when relevant.|
|4. Ordering/interpreting|Tests and referrals automatically create ownership tasks with due dates and patient-notification states.|
|5. Closure|Clinician closes visit concerns with status, rationale, pending items, and safety-net plan; unresolved episodes stay open.|
|6. Worklist|Risk-ranked worklist surfaces overdue abnormal results, pending tests, failed referrals, repeat visits, and unresolved check-ins.|
|7. Specialist/handoff|Cross-specialty handoff shows what was tried, what remains unexplained, patient concern, and exact referral question.|

## 5. Data schema

The schema is delivered as `data_schema.csv`. Core entities include: `PatientProfile`, `DiagnosticEpisode`, `Encounter`, `SymptomTimelineEvent`, `PatientConcern`, `HighRiskHistory`, `MedicationAccessSignal`, `TestOrder`, `TestResult`, `ResultTask`, `ReferralTask`, `DischargePlan`, `FollowUpCheckIn`, `VisitSummaryCorrection`, `LanguageInterpreterEvent`, `ResourceAvailability`, `CHWReferral`, and `AuditAndSafetyOutcome`.

Design rule: all clinically important derived views must preserve provenance: patient-reported, clinician-entered, imported/outside, machine-extracted, or system-derived.

## 6. Black-zone prevention map

The full map is delivered as `black_zone_prevention_map.csv`. The highest-priority black zones are:

- **Before visit/intake:** one-symptom framing and missing patient narrative → rich timeline intake and missing-data checklist.
- **Triage/vitals:** red flags or repeated visits missed → stage-specific red flags and repeat-visit reset.
- **Assessment/history:** dismissal, bias, mental-health misattribution → patient voice ledger and bias/misattribution guardrail.
- **Labs/imaging:** abnormal results not acted on or normal-test false reassurance → result ownership ledger and normal-test safety net.
- **Referral/discharge/follow-up:** no owner after handoff → referral state machine, pending-test discharge contract, and follow-up check-ins.
- **Specialist/community:** wrong specialty or CHW signal lost → cross-specialty pattern map and CHW/informal-provider referral capture.

## 7. Feature opportunity table

The full table is delivered as `feature_opportunity_table.csv`. Summary:

|Feature|Status|Stage|Risk|Evidence refs|
|---|---|---|---|---|
|Rich symptom timeline and patient narrative intake|strongly supported|before visit; intake form; medical history; first clinician assessment|medium|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: E015, E020, E022, C020, C022, Q002 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-002, B-020, B-022, B-023, Q-001, Q-005 / research_evidence_package_patient_complaints_identification_failures_...|
|What-changed-from-normal and daily-function capture|supported by some evidence|before visit; intake form; follow-up; long-term monitoring|medium|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C022, C052, E052 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-021, B-022, B-023, Q-005 / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C012, C013, Q...|
|High-risk history and family-history cards|strongly supported|medical history; first clinician assessment; repeat visit; specialist review|medium|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C020, E020 / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C004, C005, Q004, Q005 / research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz: C001, E005 / resea...|
|Medication, access, and affordability as diagnostic clues|region-specific / needs caution|before visit; medical history; follow-up; referral|high|research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-013 / research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz: M009, M010 / research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz: M005, S020, 05_implications/product_or...|
|Longitudinal unresolved-problem tracker / diagnostic episode layer|strongly supported|follow-up; repeat visit; specialist review; long-term monitoring|high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: E020, E021, E051, C020, C051 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-001, B-009, B-014, B-020, B-021, M-005, M-006 / research_evidence_package_patient_complaints_identification_failures...|
|Repeat-visit diagnostic reset|strongly supported|arrival; nurse triage; first clinician assessment; repeat visit; emergency escalation|medium-high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: E021, C021, C020 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: M-005, B-006, B-010, B-028, B-030 / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C008, ...|
|Normal-test safety net and test-scope explainer|strongly supported|lab interpretation; imaging interpretation; diagnosis discussion; discharge; follow-up|high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: E018, C034, 04_topic_outputs/maps_or_matrices/black_zones_matrix.csv / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: M-003, B-001, B-003, B-004, B-016 / research_evidence_package_patient_complain...|
|Closed-loop abnormal result ownership ledger|strongly supported|lab interpretation; imaging interpretation; discharge; follow-up; specialist review|high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C024, C025, C032, 04_topic_outputs/maps_or_matrices/black_zones_matrix.csv / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: M-004, B-011, B-012, B-017, B-018 / research_evidence_package_patient_co...|
|Pending-test discharge contract|supported by some evidence|discharge; lab interpretation; imaging interpretation; follow-up|high|research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-012, B-017, 04_topic_outputs/other_outputs/product_opportunities.csv / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C026, E026 / research_evidence_package_patient_complaints_identification_fai...|
|Referral completion and wrong-specialty tracker|strongly supported|referral; specialist review; follow-up; repeat visit|medium-high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C027, C028, C029, C023 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: M-009, B-024, B-029, B-032 / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C006, C...|
|Patient/family deterioration escalation route|supported by some evidence|follow-up; discharge; inpatient ward; emergency escalation; repeat visit|high|research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: S036, C004, C007, Q004, Q008 / research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz: E023, Q003 / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C020, C024 / re...|
|Stage-specific red-flag prompts and emergency pathway timers|strongly supported|arrival; nurse triage; vitals; first clinician assessment; labs ordered; imaging ordered; discharge|high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: E002, C001, C009, C041, C039, C040, 04_topic_outputs/diagrams_or_flows/flow_maps.csv / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-006, B-007, B-016, B-030, M-010 / research_evidence_package_...|
|Cross-specialty pattern map for unresolved multi-system symptoms|supported by some evidence|referral; specialist review; repeat visit; diagnosis discussion|high|research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-002, B-003, B-024, B-029, B-032, 04_topic_outputs/other_outputs/product_opportunities.csv / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C015, Q014 / research_evidence_package_h...|
|Concise doctor-facing diagnostic episode summary|strongly supported|first clinician assessment; medical history; specialist review; repeat visit|high|research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz: E001, E015, E016, Q003, Q011, M002, M003, M004, M005, M006 / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: 03_analysis/key_findings.md, 05_implications/product_or_system_implications.md / re...|
|Missing-data checklist and suggested questions|strongly supported|intake form; medical history; physical exam; telehealth; first clinician assessment|medium-high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: 04_topic_outputs/maps_or_matrices/black_zones_matrix.csv, 04_topic_outputs/maps_or_matrices/stage_data_matrix.csv / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C005, C003, C018 / rese...|
|Note-diff and copy-forward detection|supported by some evidence|medical history; first clinician assessment; follow-up; specialist review|medium|research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz: E016, 05_implications/product_or_system_implications.md|
|Patient voice protection and visit-summary correction|strongly supported|diagnosis discussion; discharge; follow-up; patient portal|medium-high|research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: Q001, Q003, Q018, Q019, Q020, C018 / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: Q002, Q004, C022 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: Q-003...|
|Bias and misattribution guardrail|strongly supported / needs caution|first clinician assessment; medical history; referral; diagnosis discussion|high|research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: M-001, M-002, B-003, B-021, Q-004, Q-007 / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C013, C015, Q010, Q014 / research_evidence_package_clinician_side_diagnostic_pain_points_20...|
|Language, interpreter, and cultural-safety fields|strongly supported / region-specific|before visit; intake form; medical history; referral; follow-up|high|research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz: E024, E026, E027, E028, M006, 03_analysis/key_findings.md / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: 04_topic_outputs/maps_or_matrices/stage_data_matrix.csv / research_evidence_package_pat...|
|Low-resource diagnostic availability and provenance layer|strongly supported / region-specific|labs ordered; imaging ordered; referral; follow-up; home/community visit|high|research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz: M009, M010 / research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz: M005, E020, S020, 05_implications/product_or_system_implications.md / research_evidence_package_missed_signals_diagnostic_er...|
|CHW and informal-provider referral capture|strongly supported / region-specific|before visit; home/community visit; referral; follow-up|high|research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz: M004, M007, E012, E013, E021 / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C038, C039, C040, C043, FM12, FM14, FM15|
|Patient-held record import for fragmented systems|supported by some evidence / region-specific|before visit; registration; medical history; referral; specialist review|high|research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz: 03_analysis/patterns.md, 05_implications/product_or_system_implications.md / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C049, C050 / research_evidence_package_patient_complaints_identificati...|
|Public-health screening follow-up navigator|strongly supported|public health screening; lab interpretation; referral; follow-up; diagnosis discussion|medium-high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C032, C033, C034, C035, C036, C037 / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: B-019 / research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: C010, M001 / res...|
|Diagnosis-status clarity and “not yet explained” state|supported by some evidence|diagnosis discussion; discharge; follow-up; patient portal|medium-high|research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz: Q003, Q007, C003, C006, 05_implications/product_or_system_implications.md / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: 04_topic_outputs/other_outputs/product_opportunities.csv /...|
|Risk-ranked result/referral worklists to reduce alert fatigue|strongly supported / needs caution|lab interpretation; referral; follow-up; specialist review|high|research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz: E001, M002, M003, M004, 05_implications/risks_and_safety_notes.md / research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: C024, C025 / research_evidence_package_missed_signals_diagnostic_errors_2026...|
|Symptom-still-present check-ins after normal tests or watchful waiting|strongly supported|diagnosis discussion; discharge; follow-up; repeat visit|medium-high|research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz: E018, C018, C034, 04_topic_outputs/maps_or_matrices/black_zones_matrix.csv / research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz: M-003, B-001, B-004 / research_evidence_package_patient_complaints_ident...|

## 8. Evidence-backed feature backlog

The backlog is delivered as `evidence_backed_feature_backlog.csv` with priority, release theme, acceptance criteria, risk level, complexity, guardrail, and source links.

Recommended build order:

1. **P0 safety backbone:** diagnostic episode layer, repeat-visit reset, closed-loop abnormal result ledger, risk-ranked worklists, rich patient narrative intake.
2. **P1 continuity and trust:** referral completion tracker, normal-test safety net, pending-test discharge contract, symptom-still-present check-ins, patient voice/summary correction, high-risk history cards, missing-data checklist, doctor-facing summary, language/interpreter foundation.
3. **P2 adapted pathways:** red-flag timers, bias/misattribution guardrail, cross-specialty pattern map, screening navigator, low-resource availability layer, CHW capture, diagnosis-status clarity.
4. **P3 advanced/setting-specific:** note-diff/copy-forward detection, patient-held record import, medication/access-as-diagnostic-clue module.

## 9. High-risk safety areas

The full safety table is delivered as `high_risk_safety_areas.csv`. Highest-risk areas are autonomous diagnosis/false certainty, alert fatigue, false reassurance from normal tests, bias amplification, sensitive data privacy, clinician burden, low-resource responsibility shifting, and data provenance failures.

## 10. Region-specific adaptations

The full table is delivered as `region_specific_adaptations.csv`. Key adaptations:

- Integrated EHR/HMO systems: emphasize result ownership, alert ranking, and longitudinal synthesis.
- GP-gatekeeper systems: emphasize repeat visits, safety-netting, referral state, and patient narrative.
- Fragmented/open-access systems: emphasize patient-held record import, provenance, and cross-specialty summary.
- Low-resource/community systems: emphasize offline CHW capture, diagnostic availability, fallback plans, and referral counter-loop.
- Migrant/Indigenous/multilingual contexts: language/cultural-safety fields require community governance and privacy protections.
- Screening systems: positive-screen follow-up must be tracked until diagnostic completion; negative screens must not silence symptoms.

## 11. “Living insight” status

The living insight file is delivered as `living_insights.csv`. No feature is marked “contradicted by evidence.” Several are marked **region-specific / needs caution** because the packages show different realities across integrated, fragmented, rural, low-resource, CHW, and culturally unsafe settings.

## 12. Limitations

See `evidence_quality_and_gaps.md` for detailed limitations. The most important limitation is that this synthesis translates the attached evidence packages; it does not add a new source search. Raw sources were usually not downloaded in the packages, so all source traceability relies on the package source logs, source-summary files, row IDs, and URLs.
