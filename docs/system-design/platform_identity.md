# WellBe Platform Identity

> **This is a bible file.** See `doc-governance.mdc` — it may not be edited without explicit user approval.

---

## What WellBe Is

WellBe is a **Patient-Centered Health Investigation OS**. Its sovereign core is a **Personal Shared Health Memory OS** — a user-controlled memory layer that helps individuals carry health context forward until each concern is resolved, explained, monitored, or safely handed off. Around that core, WellBe offers role-specific workspaces (individual, caregiver, clinician, care team, institution, researcher) that reach the same underlying primitives only through user-granted, scoped, time-boxed, purpose-bound access. The individual is always the data controller; other audiences are users of workspaces, never controllers of the individual's data.

---

## The Operating Loop

| Step | What it does | Example |
|---|---|---|
| **Capture** | Collect raw and structured health context | Symptom words, lab PDF, referral message, wearable trend |
| **Connect** | Link signals into a Health Thread | Recurring pain + ED visit + normal scan + pending referral |
| **Investigate** | Run a structured research process over a thread — open an Investigation, evaluate Theories, pull personal and external evidence, surface what changed | "Open investigation: fatigue after med change vs. sleep disruption — evidence for/against, missing data identified." |
| **Clarify** | Surface what is known, unknown, missing, pending, or worsening | "Symptoms persist after normal ultrasound; referral not yet scheduled." |
| **Close** | Track open loops until resolved, explained, monitored, or safely handed off | Pending test due; referral booked; follow-up complete |
| **Correct** | Let the user repair inaccurate or incomplete memory | "This started before the medication change, not after." |

---

## Core Objects

A **Health Thread** is a living container for one unresolved or ongoing health concern. It holds: patient's own words, timeline and baseline change, symptom episodes, related visits and contacts, test results (including normal-result context), referrals and their status, pending items, open questions, patient corrections, access and equity barriers, and source-linked evidence.

An **Investigation** is the active, structured research process around one or more Health Threads: a primary question, scope and participants (under grant), linked theories, evidence bundle, missing-context items, pending items, safety flags, and review cadence. A thread is the concern; an investigation is the attempt to understand, monitor, explain, or close it.

A **Theory** is a user- or clinician-proposed explanation evaluated against available evidence. It is never a diagnosis, a ranked differential, or a disease claim; it carries evidence-for, evidence-against, missing-data, and a safety level.

---

## Audience Model

WellBe separates four concepts:

- **Audience** — who uses a surface: individual, caregiver, clinician, care team, institution, researcher.
- **Data controller** — always the individual. Other audiences never control an individual's data.
- **Workspace** — the role-specific interface (Individual, Clinician Case Investigation, Shared Health Thread, Institution Continuity, Research Sandbox).
- **Grant** — the user-approved, scoped, time-boxed, purpose-bound permission that lets another party view or contribute. Access without a grant, a care relationship, a legal basis, or explicit research consent does not happen.

**Primary audience — individuals.** Patients, caregivers, and family members managing their own or a dependent's health. The individual is always the end-user whose interests the product serves and always the controller of their data.

**Additional audiences — clinicians, care teams, institutions, researchers.** They may be active workspace users, but only under explicit grant and governance. Businesses (hospitals, clinics, employers) may also deploy WellBe as a distribution channel; deploying never confers data control.

**Hard constraints:**
- Every feature must make sense from, and benefit, the individual user — even when another audience uses it.
- No audience gets default access to an individual's data; access is grant-based, scoped, and revocable.
- Cross-patient comparison is always opt-in, user-initiated, and never an institutional default.
- Institutions receive only aggregate, consented, privacy-preserving continuity intelligence — never default individual-level access.

---

## What WellBe Is Not

- A clinician-facing EHR, system-of-record, or hospital workflow replacement (WellBe offers consent-scoped case-investigation workspaces, not an EHR)
- A diagnosis engine or medical authority
- A population analytics or cross-patient research platform enabled by default (cross-patient and research surfaces exist only under explicit individual opt-in and governance)
- A practice management or clinical-staff coordination system
- A system that grants institutions default access to, or control over, individual data
- An autonomous medical AI that reaches conclusions without user agency
- A replacement for clinical judgment

---

## Design Principles (Non-Negotiable)

1. **Personal-controller-first.** The individual remains the data controller and the audience every feature must benefit, even when clinicians, care teams, institutions, or researchers use their own workspaces under grant.
2. **Source-linked.** Every derived claim traces to a source. No orphan outputs.
3. **Investigate, never diagnose.** The platform asks better questions; it does not give final medical answers.
4. **User-controlled sharing.** Sharing, clinician access, and integrations are always user-initiated.
5. **Safety gate before every AI output.** The Safety Engine evaluates every user-facing AI output. No bypass.
6. **Raw data immutability.** Original inputs are never overwritten; corrections layer on top.
7. **Correct, don't hide.** Errors and gaps are surfaced and repaired, not silently removed.

---

## The Identity Boundary

> A feature belongs in WellBe if it serves the individual's understanding and agency over their own health, and any non-individual access it introduces is grant-based, scoped, purpose-bound, and revocable. A feature does not belong if it requires default institutional access, replaces clinical judgment, or delivers value only to a business/clinician without also benefiting the individual.
