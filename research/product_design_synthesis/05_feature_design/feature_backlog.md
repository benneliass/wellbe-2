# Feature backlog

## Diagnostic episode layer / unresolved-problem tracker

- User: doctor; nurse; patient; specialist; admin
- Problem solved: Repeated visits, tests, referrals, messages and persistent symptoms are treated as separate encounters instead of one unresolved diagnostic thread.
- Evidence: research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::04_topic_outputs/diagrams_or_flows/flow_maps.csv::FM09; S20; S21; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::04_topic_outputs/other_outputs/product_opportunities.csv::Longitudinal diagnostic signal accumulator; B-001/B-009/B-014/B-020/B-021; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::02_extracted_evidence/cases_or_examples.csv::C008; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::02_extracted_evidence/evidence_items.csv::E005; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::02_extracted_evidence/cases_or_examples.csv::C001
- Risk level: High
- Guardrail: Every issue has status, owner, next action, uncertainty statement, and manual clinician override; monitor false positives and missed escalations.

## Rich patient intake timeline with change-from-baseline

- User: patient; caregiver; nurse; doctor
- Problem solved: Current intake often captures a chief complaint but loses timeline, functional impact, patient fear, prior failed contacts, and what changed from normal.
- Evidence: research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM05/FM06/FM07; 02_extracted_evidence/evidence_items.csv::E011; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::02_extracted_evidence/evidence_items.csv::E003/E006/E007; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::02_extracted_evidence/cases_or_examples.csv::C001/C002/C005; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::cases_or_examples.csv::B-002/B-023
- Risk level: Medium
- Guardrail: Adaptive short form; plain language; translation and caregiver mode; separate patient narrative from clinician assessment; emergency escalation language.

## Repeat-visit diagnostic reset trigger

- User: doctor; nurse triage; urgent care; ED; primary care
- Problem solved: Return visits for the same or worsening complaint are handled as fresh visits rather than safety signals.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Repeat-visit diagnostic reset; B-006/B-010/B-028/B-030; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM09; 02_extracted_evidence/cases_or_examples.csv::C002/C009; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::cases_or_examples.csv::C003; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C001
- Risk level: High
- Guardrail: Trigger only on meaningful persistence/worsening/repeat count; present as diagnostic reset support; require clinician acknowledgment and override rationale.

## Closed-loop abnormal result ownership ledger

- User: doctor; nurse; admin; patient; specialist
- Problem solved: Abnormal lab, imaging, microbiology or histology results can be seen, filed, or lost without clear action, patient notification, or accountable owner.
- Evidence: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E001/E015; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Closed-loop abnormal result ownership; B-011/B-012/B-015/B-017/B-018; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C010/C011; sources S013/S014/S035; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM08; sources S19/S24/S25; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C002
- Risk level: High
- Guardrail: Risk-ranked worklist; escalation by criticality; backup owner; patient notification only with pathway to explanation; audit overdue closures.

## Referral completion and transparency tracker

- User: doctor; patient; admin; specialist
- Problem solved: Referral placement is confused with completed specialty assessment; rejection, advice-only, wrong specialty, missing information, scheduling failure, and non-attendance are invisible.
- Evidence: research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM10/FM11; sources S27/S28/S29; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E013/E014; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C006/C016; reviews R007/R008; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C005/C006; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::cases_or_examples.csv::B-005/B-029/B-032
- Risk level: High
- Guardrail: Separate “no pathway”, “more info needed”, “wrong service”, “clinical advice only”, and “diagnosis ruled out”; require follow-up owner for advice-only outcomes.

## Normal-test trap explainer and persistent-symptom safety net

- User: doctor; nurse; patient
- Problem solved: Normal or old tests can close an encounter even when symptoms remain severe, persistent, anatomically discordant, episodic, or outside the test’s scope.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Normal-test trap explainer; B-001/B-003/B-004/B-016; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C003/C007; quote Q003; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::main_report.md::normal-test trap; flow FM09; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::practical_implications.md::pair normal test results with symptom status
- Risk level: High
- Guardrail: Use uncertainty language; show what remains unexplained; avoid automatic diagnosis; tie next steps to clinician-reviewed safety net.

## Patient voice protection: verbatim concern + correction path

- User: patient; caregiver; doctor; nurse
- Problem solved: Patients report that histories are cut off, symptoms are minimized, and what matters to them is not documented in a way that survives the visit.
- Evidence: research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::quotes.csv::Q001/Q003/Q004/Q018/Q019/Q020; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::quotes.csv::Q001/Q002/Q003/Q004; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::quotes.csv::Q-001/Q-004/Q-005/Q-007; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::quotes.csv::Q001/Q004
- Risk level: Medium
- Guardrail: Separate patient voice from clinical assessment; respectful language normalization; patient-visible summary corrections; no automated accusation of dismissal.

## Concern-by-concern visit closure

- User: doctor; patient; nurse; caregiver
- Problem solved: Multi-issue visits can close one symptom while leaving other patient-listed concerns unresolved without visible disposition.
- Evidence: research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C002; quote Q002; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E004; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::practical_implications.md::specific safety-netting and follow-up
- Risk level: Medium
- Guardrail: Allow “deferred with plan” disposition; keep closure concise; prioritize safety-critical unresolved concerns.

## Doctor-facing concise timeline and red-flag summary

- User: doctor; nurse; specialist
- Problem solved: Clinicians need context quickly but EHR notes, messages, repeated encounters, and copied-forward content bury relevant signals.
- Evidence: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E015/E016/E021; quotes Q002/Q011; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::patterns.md::no one connected the dots; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::patterns.md::patient narratives reveal continuity failures earlier than structured records
- Risk level: High
- Guardrail: Show source links, timestamps, uncertainty, and missing data; user can expand raw notes/results; flag generated summary as support only.

## Missing-data checklist for family history, medication access and prior tests

- User: patient; caregiver; doctor; nurse
- Problem solved: Family history, medication interruption, prior testing, out-of-system diagnoses, and patient/caregiver concern are treated as background rather than active diagnostic signal.
- Evidence: research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C005; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::cases_or_examples.csv::B-013/B-023/B-031; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E003; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::practical_implications.md::ask what happened before current visit
- Risk level: Medium
- Guardrail: Use optional patient-controlled disclosure; privacy notices; clinician confirms before action; do not infer blame from non-adherence.

## Triage red-flag co-pilot with reassessment timers

- User: nurse; ED/urgent-care clinician; registration staff
- Problem solved: Arrival, registration and triage sort urgency under pressure; red flags, worsening while waiting, and abnormal vitals can lose salience.
- Evidence: research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM01/FM02/FM04; sources S01/S03/S04/S09/S10; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E010; quote Q010; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::nurse triage/vitals; B-006/B-016; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C003/C008/C009
- Risk level: High
- Guardrail: Support not replace nurse judgment; make timers actionable; require human reassessment; audit overrides and missed deteriorations.

## Waiting-room and pre-triage deterioration check-in

- User: patient; registration staff; nurse triage; ED/urgent care
- Problem solved: Patients can deteriorate before registration, during self-service intake, or while waiting by acuity order, especially if they do not know what to report.
- Evidence: research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM02/FM04/FM05; evidence_items.csv::E004/E008; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C008/C009; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::black_zones_by_patient_stage.csv::arrival / registration; nurse triage / vitals
- Risk level: High
- Guardrail: Multilingual/plain-language prompts, accessibility modes, visible escalation button, queue-monitoring rules, staff triage review.

## Digital intake complexity escape hatch

- User: patient; admin/care navigator; nurse; GP/primary care
- Problem solved: Online triage and self-service flows can force single-symptom routing, depend on free text, omit prior high-risk history, or exclude patients with digital/language barriers.
- Evidence: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E006/E007; quote Q005; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM05/FM06/FM07; evidence_items.csv::E006/E011; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C002; source S033 virtual-care evidence
- Risk level: High
- Guardrail: Human-review escape hatch, prior-history auto-pull, multi-symptom support, accessibility fallback, clear emergency redirection.

## Bias and misattribution guardrail

- User: doctor; nurse; safety team
- Problem solved: Physical symptoms may be dismissed or attributed to anxiety, stress, age, gender, substance use, difficult behavior, or mental illness before dangerous alternatives are considered.
- Evidence: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E017/E018; quotes Q012/Q013; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Bias/misattribution guardrail; B-003/B-020/B-021/B-024; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::quotes.csv::Q009/Q010/Q014; cases C012/C014/C015; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C008; cultural_black_zone_map.md
- Risk level: High
- Guardrail: Frame as coexisting physical-risk review; do not accuse; require documentation of red flags considered when symptoms remain discordant.

## Lab trend and personal-baseline explorer

- User: doctor; nurse; specialist; patient
- Problem solved: Clinically important change can be hidden when individual values look normal, are viewed out of sequence, or are not connected to symptoms.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::cases_or_examples.csv::B-001/B-014/B-015; black_zones_by_patient_stage.csv::long-term monitoring; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E015; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::reviews_or_complaints.csv::R009; source S54
- Risk level: High
- Guardrail: Start with transparent trend visualization and clinician-reviewed thresholds; capture false positives/negatives; no final diagnosis.

## Pending-test discharge contract

- User: patient; doctor; nurse; admin
- Problem solved: Patients leave care while tests are pending, unclear, or not yet interpreted; no one knows who will act or when.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Pending-test discharge contract; B-012/B-017; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM08; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C010/C011; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E004
- Risk level: High
- Guardrail: Plain-language plan: “what is pending,” “when you will hear,” “who owns it,” and “what to do if no contact.”

## Cross-specialty pattern map

- User: doctor; specialist; referral coordinator; patient
- Problem solved: Complex symptoms spanning specialties are split into GI/GYN/cardiology/neuro/psych silos, causing wrong-specialty drift or advice-only loops.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Cross-specialty referral map; B-002/B-003/B-024/B-029/B-032; research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::patterns.md::wrong specialty or unclear referral pathway; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E013/E014; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM10/FM11
- Risk level: High
- Guardrail: Local referral directory and criteria; “consider asking” prompts rather than automated referral; shared summary with clinical question.

## Patient-held record and out-of-system care import

- User: patient; caregiver; doctor; admin; CHW
- Problem solved: Signals from private, informal, cross-border, pharmacy, traditional, or disconnected care never enter the formal record.
- Evidence: research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::evidence_items.csv::E008/E009; cases C004/C005; product_or_system_implications.md; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_notes_by_care_setting.csv::telehealth / home/community / rural settings; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::cases_or_examples.csv::B-031
- Risk level: Medium-high
- Guardrail: Provenance labels; clinician verification; patient consent; data-quality confidence; do not overwrite official results.

## Language, interpreter and cultural-safety layer

- User: patient; caregiver; registration staff; nurse; doctor; liaison
- Problem solved: Language barriers, mistrust, cultural safety failures, racism, and did-not-wait patterns shape whether symptoms are voiced, believed and followed up.
- Evidence: research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::sources S023/S024/S026/S027/S028; cases C008/C009/C010; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E003; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_notes_by_care_setting.csv::telehealth / public health screening / community visit
- Risk level: High
- Guardrail: Connect to actual interpreter/liaison workflows; track completion not just need; avoid ethnicity-based risk scoring.

## Low-resource diagnostic availability and stockout-aware plan

- User: clinician; CHW; nurse; district manager; patient
- Problem solved: A diagnostic tool may not exist, be affordable, be in stock, or be reachable; missing diagnostics can look like clinician delay unless explicitly captured.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::cases_or_examples.csv::B-025/B-026/B-027; product_opportunities.csv::Low-resource diagnostic availability layer; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases C005/C006/C007; evidence_items E010; product implications; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E019/E020; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM12 and rural/low-resource clinic notes
- Risk level: High
- Guardrail: Resource-aware workflows; offline/paper/SMS modes; aggregate stockout reporting; escalation alternatives; no punitive clinician metrics for stockouts.

## CHW and informal-provider referral capture mode

- User: CHW; informal provider; nurse; primary care; patient
- Problem solved: Community health workers and informal/non-allopathic providers are often first assessment nodes but may not be connected to formal testing and referral loops.
- Evidence: research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases C005/C007; evidence_items E010; sources S012/S021; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::flow_maps.csv::FM12; sources S38/S40/S41/S43; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E019
- Risk level: High
- Guardrail: Protocol-bound scope, supervision, offline mode, referral confirmation, local-language prompts, supply/status integration.

## Medication and access-as-diagnostic-clue capture

- User: patient; doctor; nurse; social worker
- Problem solved: Medication interruption, device/supply problems, insurance gaps, and affordability can be a direct clue to deterioration or differential diagnosis.
- Evidence: research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Medication/access-as-diagnostic-clue; B-013/B-031; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::patterns.md::cost/transport/access barriers; research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E003
- Risk level: Medium-high
- Guardrail: Ask nonjudgmentally; mark patient-controlled sensitive data; link to assistance/referral resources; do not equate cost barriers with noncompliance.

## Note-diff and copied-forward detection

- User: doctor; specialist; nurse; safety reviewer
- Problem solved: Long redundant notes obscure new facts, changed assessments, unresolved problems, and copied-forward assumptions.
- Evidence: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E016; product implications; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::patterns.md::no one connected the dots; normal-test trap; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::patterns.md::patient narratives reveal continuity failures
- Risk level: Medium-high
- Guardrail: Prioritize clinically meaningful changes; allow clinician dismissal; tie output to unresolved episode summary.

## Workload-aware alert management and risk-ranked worklists

- User: doctor; nurse; admin; safety lead
- Problem solved: More alerts can worsen the exact overload that causes missed abnormal results and poor follow-up.
- Evidence: research_evidence_package_clinician_side_diagnostic_pain_points_2026-05-30.tar.gz::evidence_items.csv::E001/E011/E015/E021; quotes Q003/Q008/Q010/Q011; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::main_report.md::front-door workflows sort urgency before diagnosis; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::risks_and_safety_notes.md::over-alert risk
- Risk level: High
- Guardrail: Actionable, tiered alerts; suppress duplicates; ownership + escalation; measure false positives/negatives; do not use fatigue data punitively.

## Patient/family deterioration escalation route

- User: patient; caregiver; nurse; doctor; safety team
- Problem solved: Family or patient concern about deterioration may be ignored or lack a route beyond repeating the same complaint.
- Evidence: research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::cases_or_examples.csv::C004/C008; source S036 Martha’s Rule; quotes Q004/Q008; research_evidence_package_global_health_issue_identification_2026-05-30.tar.gz::cases_or_examples.csv::C003/C008/C009; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::reviews_or_complaints.csv::R003; quotes Q004
- Risk level: High
- Guardrail: Clear criteria, named response team, acknowledgment timestamp, triage of escalation requests, respectful language.

## Diagnosis-status clarity in patient portal

- User: patient; doctor; admin
- Problem solved: Patients may see labels, referral decisions or results without knowing whether a diagnosis is confirmed, suspected, excluded, pending, or unexplained.
- Evidence: research_evidence_package_patient_complaints_identification_failures_2026-05-30.tar.gz::quotes.csv::Q007/Q011/Q012; product implications; research_evidence_package_missed_signals_diagnostic_errors_2026-05-30.tar.gz::product_opportunities.csv::Pending-test discharge contract; research_evidence_package_health_system_patient_flows_2026-05-30.tar.gz::practical_implications.md::record what remains unexplained
- Risk level: Medium-high
- Guardrail: Use clinician-authored uncertainty templates; explain status categories; show who to contact and when.
