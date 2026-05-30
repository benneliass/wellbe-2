# Black-zone map

## Access barriers, informal/private care, persistent symptoms or high-risk history never enter stable diagnostic pathway.

- Stage: Before visit
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::before visit; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::C004/C005/C006; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM12
- Product prevention: Patient-held record import; access-barrier fields; CHW/informal referral capture; incomplete-workup registry.
- Guardrail: Provenance labels; offline/SMS/paper mode; clinician verification.

## Repeat visit, family history, referral note or deterioration not visible before triage.

- Stage: Arrival / registration
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::arrival / registration; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::C008; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM02
- Product prevention: Front-door repeat-visit banner; referral-note visibility; arrival-to-assessment timer; family/caregiver concern field.
- Guardrail: Avoid algorithmic downgrades; registration escalation button.

## Single-symptom routing loses complexity, prior cancer/high-risk history, or patient meaning.

- Stage: Intake form / digital triage
- Evidence refs: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E006/E007/Q005; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM05/FM06; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::C002
- Product prevention: Hybrid intake: multi-symptom, free text, prior-history auto-pull, “not captured” and human-review escape hatch.
- Guardrail: Accessibility/language fallback; emergency warning; human override.

## Abnormal vitals, repeat visits and red flags lose salience under cognitive strain.

- Stage: Nurse triage / vitals
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::B-006/B-016; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E010/Q010; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM01/FM02
- Product prevention: Triage co-pilot, repeat-vital timers, deterioration check-in, acuity plus diagnostic-uncertainty view.
- Guardrail: Support nurse judgment; calibrated timers; monitor over-alerting.

## First plausible diagnosis or mental-health/age/gender label closes inquiry.

- Stage: First clinician assessment
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::B-003/B-020/B-021/B-024; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E017/E018; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::Q009/Q010/Q014
- Product prevention: Diagnostic time-out: dangerous-to-miss alternatives, bias/misattribution guardrail, patient quote visible.
- Guardrail: Do not accuse; require clinician-reviewed red-flag check only when signals are discordant.

## Family history, medication access, patient’s own theory, functional impact and prior test context are not integrated.

- Stage: Medical history
- Evidence refs: research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::C005; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::B-013/B-023/B-031; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E003
- Product prevention: Risk-context checklist and structured timeline with patient/caregiver input.
- Guardrail: Sensitive-data controls and nonjudgmental wording.

## Time-sensitive exams absent or delayed; telehealth gap hides required in-person exam.

- Stage: Physical exam
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::physical exam; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::S033; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::S14
- Product prevention: Complaint-linked exam checklist; telehealth-to-in-person conversion criteria; timer for torsion/appendicitis-like pathways.
- Guardrail: Clinician override; avoid rigid protocols.

## Wrong test, no test, stockout, or wrong imaging scope.

- Stage: Labs / imaging ordered
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::B-004/B-026/B-027; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E020; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM03
- Product prevention: Order-set suggestions; imaging-scope warning; unavailable-test alternate plan; resource availability capture.
- Guardrail: Do not force testing; adapt to local resources.

## Abnormal result exists but is not communicated, acknowledged or acted on.

- Stage: Lab / imaging interpretation
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::B-008/B-011/B-012/B-017/B-018; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::C010/C011; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E001/E015
- Product prevention: Result/finding lifecycle tracker, owner/deadline, critical semantics, patient notification status.
- Guardrail: Risk-ranked worklist and backup owner; explanation path for patient release.

## Uncertainty, pending tests and unresolved symptoms disappear from patient plan.

- Stage: Diagnosis discussion / discharge
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::Pending-test discharge contract; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::C003/Q003; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E004
- Product prevention: Concern-by-concern closure; “what remains unexplained”; pending-test contract; specific safety-net.
- Guardrail: Avoid panic; plain language and clear contact routes.

## Referral delayed, wrong, rejected, advice-only or never completed.

- Stage: Referral
- Evidence refs: research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM10/FM11; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E013/E014; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::C006
- Product prevention: Referral status taxonomy and completion tracker with next owner.
- Guardrail: Distinguish administrative status from diagnostic conclusion.

## Return visits do not cause diagnostic reset.

- Stage: Follow-up / repeat visit
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::B-006/B-010/B-028/B-030; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::FM09; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::C001
- Product prevention: Repeat-visit diagnostic reset and symptom-still-present check-ins.
- Guardrail: Thresholds by setting; do not punish returns.

## Specialist sees one slice, wrong chart, remote note, or wrong specialty.

- Stage: Specialist review
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::specialist review; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::E013/E014
- Product prevention: Cross-specialty summary pane, identity verification, clinical question and unresolved-pattern map.
- Guardrail: Source-linked and local referral criteria.

## Slow trends and chronic invalidation hide deterioration.

- Stage: Long-term monitoring
- Evidence refs: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::long-term monitoring; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::Q011; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::S53/S54
- Product prevention: Trend explorer, functional status, quality-of-life, unresolved-problem registry.
- Guardrail: Clinical validation before alerts; avoid anxiety loops.
