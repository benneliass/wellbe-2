# WellBe — Vision Guardrails

> This document exists to keep the project grounded. It is a constraint on how research, features, and design decisions are interpreted — not a product spec.

---

## The system is personal. Always.

WellBe is a **patient-centered health investigation platform** whose sovereign core is a personal health intelligence system. The primary user and sole data controller is the individual managing their own health. Clinicians, care teams, institutions, and researchers may use their own workspaces, but only under the individual's explicit, scoped grant — and every feature must still serve and benefit that individual.

---

## What the research revealed — and how to read it

The research packages (A–F) studied real-world diagnostic failures: missed signals, clinical handoffs, referral voids, ownership vacuums. This is valuable context. It tells us **what the individual faces** when they navigate the health system.

The research describes failures that live in the clinical system. WellBe's first response is to **empower the person**. Where a consented, scoped workspace lets a clinician or institution help close those same loops for the individual's benefit, WellBe may provide it — but it never becomes the system of record or gains default control over the person's data.

### The reframe

| Research finding | Clinical-system reading (not WellBe) | Personal-system reading (WellBe) |
|---|---|---|
| "No named owner for abnormal results" | Build a clinical result ownership ledger | Help the user know what's still open and who to follow up with |
| "Repeat visits treated as separate encounters" | Build a hospital visit tracking system | Give the user longitudinal memory so they can advocate that this isn't a new problem |
| "Referral placed but never completed" | Build a referral management platform | Help the user understand where their referral stands and when to push |
| "Patient voice cut off during intake" | Build a pre-consultation intake tool for clinicians | Help the user articulate and document their full experience before any appointment |
| "No one connected the dots" | Build cross-clinician diagnostic episode tracking | Synthesize the user's own data across time, sources, and domains so they can see the pattern themselves |

---

## The comparison engine is a feature, not the identity

Cross-device, cross-time, cross-source, cross-domain synthesis is WellBe's **moat** — the mechanism that creates value. But it is a means, not an end.

The end: one person understanding what is changing in their health, what might be connected, and what they should discuss or track next.

Comparison enables that. It is not the product itself.

---

## Cross-patient comparison is user-controlled, always

This applies regardless of how WellBe is sold or deployed — direct to the individual, licensed to a hospital, embedded in a practice.

**The default is always personal and isolated.** One user, their own data, their own intelligence.

Cross-referencing against other patients — even anonymized — is a feature the user explicitly activates. The institution deploying WellBe cannot enable this on behalf of its users. The distribution channel (hospital, practice, employer) does not become the data controller.

| Scenario | Allowed |
|---|---|
| User chooses "compare my recovery to similar cases" | ✅ User-initiated, explicit opt-in |
| Hospital gets aggregate insights across all its WellBe patients by default | ❌ Not without individual user opt-in |
| Clinician enables cross-patient view on their patient's account | ❌ Only the user can enable this for themselves |
| User shares their data with their care team | ✅ User-controlled sharing |
| Practice uses WellBe as a deployment channel | ✅ Distribution channel, not data controller |

This is a privacy and product identity constraint, not just a legal one. WellBe's value proposition is that it works for you. The moment an institution can turn on data flows the individual didn't choose, that proposition breaks.

---

## Scope

**In scope:**
- The user's personal health data, across all domains and time
- Helping the user understand patterns, gaps, and changes in their own health
- Preparing the user for clinical conversations (doctor-summary, symptom articulation)
- Empowering self-advocacy (longitudinal memory, concern tracking, timeline)
- User-controlled sharing of their own data with clinicians or others they choose

**In scope under explicit grant and governance (added by the expanded vision):**
- Consent-scoped clinician case-investigation workspaces (not an EHR/system-of-record)
- Privacy-preserving, aggregate-only institution continuity intelligence (no default individual access)
- Opt-in cross-patient/cohort research sandbox under protocol governance

**Out of scope (still prohibited):**
- A clinician-facing EHR, system-of-record, or workflow replacement
- Default institutional access to or control over individual data
- Population analytics or cross-user research enabled without individual opt-in
- Replacing clinical judgment in any form

---

## The test for any feature

> Does this feature serve the individual user's understanding of and agency over their own health?

If yes: it belongs.

If it requires default institutional access, replaces clinical judgment, or creates value only for a business/clinician without also benefiting the individual — it does not belong. Features that serve clinicians or institutions are welcome only when the individual remains the controller and beneficiary and access is grant-based.
