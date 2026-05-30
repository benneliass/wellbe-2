# WellBe Platform Identity

> **This is a bible file.** See `doc-governance.mdc` — it may not be edited without explicit user approval.

---

## What WellBe Is

WellBe is a **Personal Shared Health Memory OS** — a user-controlled memory layer that helps individuals carry health context forward until each concern is resolved, explained, monitored, or safely handed off.

---

## The Operating Loop

| Step | What it does | Example |
|---|---|---|
| **Capture** | Collect raw and structured health context | Symptom words, lab PDF, referral message, wearable trend |
| **Connect** | Link signals into a Health Thread | Recurring pain + ED visit + normal scan + pending referral |
| **Clarify** | Surface what is known, unknown, missing, pending, or worsening | "Symptoms persist after normal ultrasound; referral not yet scheduled." |
| **Close** | Track open loops until resolved, explained, monitored, or safely handed off | Pending test due; referral booked; follow-up complete |
| **Correct** | Let the user repair inaccurate or incomplete memory | "This started before the medication change, not after." |

---

## The Core Object: Health Thread

A **Health Thread** is a living container for one unresolved or ongoing health concern. It holds: patient's own words, timeline and baseline change, symptom episodes, related visits and contacts, test results (including normal-result context), referrals and their status, pending items, open questions, patient corrections, access and equity barriers, and source-linked evidence.

---

## Audience Model

**Primary audience — individuals.** Patients, caregivers, and family members managing their own or a dependent's health. The individual is always the end-user whose interests the product serves.

**Secondary audience — businesses as distribution channels.** Hospitals, clinics, employers, and health platforms that deploy WellBe to their users. The business deploys WellBe; the individual uses it. The individual's data belongs to the individual regardless of who deployed the product.

**Hard constraints:**
- No feature is designed exclusively for businesses. Every feature must make sense from an individual user's perspective.
- Cross-patient comparison is always opt-in, user-initiated, and never a business default.
- Deploying businesses are distribution channels, not data controllers.

---

## What WellBe Is Not

- A clinician-facing EHR or hospital workflow tool
- A diagnosis engine or medical authority
- A population analytics or cross-patient research platform
- A practice management or clinical-staff coordination system
- An autonomous medical AI that reaches conclusions without user agency
- A replacement for clinical judgment

---

## Design Principles (Non-Negotiable)

1. **Personal-first.** The individual remains the primary user and controller.
2. **Source-linked.** Every derived claim traces to a source. No orphan outputs.
3. **Investigate, never diagnose.** The platform asks better questions; it does not give final medical answers.
4. **User-controlled sharing.** Sharing, clinician access, and integrations are always user-initiated.
5. **Safety gate before every AI output.** The Safety Engine evaluates every user-facing AI output. No bypass.
6. **Raw data immutability.** Original inputs are never overwritten; corrections layer on top.
7. **Correct, don't hide.** Errors and gaps are surfaced and repaired, not silently removed.

---

## The Identity Boundary

> If a proposed feature primarily serves an institution, a clinician workflow, or a business without also serving the individual user directly — it does not belong in WellBe at this stage.
