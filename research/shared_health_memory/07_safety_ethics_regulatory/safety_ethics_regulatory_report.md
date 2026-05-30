# Safety, Ethics, and Regulatory Notes

## R001: Autonomous diagnosis risk

**Affected user:** Patient/clinician

**Possible failure mode:** Patient acts on generated diagnosis or clinician over-trusts system.

**Guardrail:** Do not present final diagnoses; use memory/uncertainty language; require clinician review.

**Supporting source IDs:** S015;S016;S017

## R002: Alert fatigue

**Affected user:** Clinician

**Possible failure mode:** Too many flags cause important signals to be ignored.

**Guardrail:** Prioritize unresolved/pending/high-risk items; monitor alert burden and false positives.

**Supporting source IDs:** S014;S015

## R003: Raw data overload

**Affected user:** Clinician

**Possible failure mode:** Patient logs or wearables create noise and burden.

**Guardrail:** Show trends and baseline changes, not raw streams by default.

**Supporting source IDs:** S013;S014

## R004: False reassurance

**Affected user:** Patient/clinician

**Possible failure mode:** Normal tests cause unresolved symptoms to be ignored.

**Guardrail:** Track normal-test-but-symptoms-persist state.

**Supporting source IDs:** S003;S008;S011

## R005: Unclear ownership

**Affected user:** Patient/admin/clinician

**Possible failure mode:** Pending results/referrals have no accountable owner.

**Guardrail:** Every pending item requires owner, due date, status, and escalation path.

**Supporting source IDs:** S010;S011;S012

## R006: Patient correction conflict

**Affected user:** Patient/clinician

**Possible failure mode:** Patient corrections silently overwrite clinical record or create medico-legal conflict.

**Guardrail:** Use review queue; mark patient-reported vs clinician-verified; preserve audit trail.

**Supporting source IDs:** S005;S016

## R007: Bias amplification

**Affected user:** Patient

**Possible failure mode:** System may reproduce dismissal patterns around gender, race, age, weight, disability, mental health, or language.

**Guardrail:** Track dismissal/minimization signals carefully; audit outcomes; avoid accusatory language.

**Supporting source IDs:** S003;S020;S021

## R008: Regulatory misclassification

**Affected user:** Company/clinician/patient

**Possible failure mode:** Product claims may move tool into regulated CDS/device territory.

**Guardrail:** Define intended use carefully; maintain transparency and clinician review; get regulatory counsel.

**Supporting source IDs:** S017

