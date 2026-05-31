# Do-not-diagnose rules

> **Bible file.** This document may only be modified with explicit user approval. See `doc-governance.mdc`.

These are hard rules. No feature, agent, mode, or configuration may bypass them. They are not defaults — they are constraints.

---

## 1. Diagnostic language — never permitted

WellBe must never output:

| Prohibited | Reason |
|---|---|
| "You have [condition]." | Diagnosis — not permitted |
| "You do not have [condition]." | Ruling out — not permitted |
| "This is [condition]." | Diagnostic conclusion — not permitted |
| "Your doctor missed [condition]." | Clinical judgment of a third party — not permitted |
| "Stop / start / change this medication." | Prescriptive medical instruction — not permitted |
| "This normal test rules everything out." | False closure — not permitted |
| "This referral means you are safe to wait." | Clinical reassurance without basis — not permitted |
| "This is not serious." | Risk minimization without clinician/source backing — not permitted |
| "You probably have X" or "almost certainly X" | Probabilistic diagnosis — not permitted |
| A ranked differential diagnosis list | Output of a clinical diagnostic process — not permitted |

---

## 2. What WellBe may say instead

| Instead of | Say |
|---|---|
| Diagnosis | "This symptom is still unresolved in your thread." |
| Ruling out | "This result was normal, but your thread still shows symptoms after the test." |
| Medical advice | "Here are questions worth discussing with a clinician." |
| Ownership claim | "This item appears pending based on the information you uploaded." |
| Clinical certainty | "The source of this claim is [patient-reported / lab report / imported note]." |
| Urgency without path | "Based on what you've logged, this may need urgent attention — [local emergency / urgent care] is one option." |
| Theory result | "Your data partially supports this theory; X and Y remain unknown. Worth discussing with a clinician." (never "this theory is true/false" or a diagnosis) |
| External evidence | "This source discusses a similar pattern, but it is low-certainty and not specific to you." (never "this source says your symptoms mean X") |
| Live-metric signal | "This is outside your usual range and paired with a symptom you marked concerning — consider contacting a clinician or urgent care depending on severity." (never "your heart data suggests [disease]") |

---

## 3. Urgency routing rules

- Any output flagged red/orange by the safety triage must include a next-step path (emergency services, urgent care, or "contact your clinician today").
- WellBe must never add urgency language and then leave the user with no action.
- WellBe must never suppress urgency language to reduce user anxiety if the signal is genuinely serious.

---

## 4. Source rules

- Every health claim derived from AI or pattern detection must be labeled by source type and confidence level.
- A claim with no traceable source may not be surfaced to the user.
- "WellBe says" is not a source. The source is always the raw input (lab report, patient entry, imported note, wearable reading) or the research reference.

---

## 5. Audience design rules

Every feature must serve and benefit the individual, even when clinicians, care teams, institutions, or researchers use it through their own grant-scoped workspaces.

**The rule:**
> No feature may grant any audience default or institution-controlled access to individual data, and no feature may deliver value only to a business/clinician without also benefiting the individual. Clinician/institution/researcher workspaces are permitted only when access is grant-based, scoped, purpose-bound, and revocable, and the individual remains the controller.

**Why this is here:**
WellBe is personal-first but can be deployed through businesses as a distribution channel. The individual is always the end-user. A feature that only serves a business, a clinic, or an institution — without also serving the individual user directly — does not belong in WellBe.

**In practice:**
- A feature that lets an employer deploy WellBe to employees is allowed — the employee (individual) is the user and controls their data.
- A feature that gives an employer aggregate health insights about their employees without individual opt-in is not allowed.
- Any feature description that says "for enterprise customers" or "for hospital administrators" must also explain how it serves the individual. If it cannot, it should not exist.

See also: `.cursor/rules/audience-guardrails.mdc` for the full audience model.

---

## 6. The non-bypass rule

The Safety Engine must evaluate every user-facing AI output before it reaches the user. No mode, no agent, no feature flag, and no configuration may disable or skip this evaluation.

This applies to:
- The Professor / explanation mode
- Myth Buster / Theory Evaluator outputs
- Research Agent / External Evidence Watch results
- Pattern detection insights
- Live-metric escalation guidance
- Clinician, institution, and research workspace outputs
- Clinician visit packet / Full Health Context Summary generation
- Any summarization or synthesis output

---

## 7. What triggers a rule update

These rules may only be changed with explicit user approval via the doc governance protocol (`doc-governance.mdc`). A rule update is triggered when:
- A new AI capability is added that produces health-related output
- A new feature category (e.g., external research, institutional integration) is introduced
- A safety incident or near-miss is identified in testing or use

Any change must be proposed, approved, and recorded before implementation.
