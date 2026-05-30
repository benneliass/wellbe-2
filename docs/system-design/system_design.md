# WellBe — Personal Shared Health Memory OS

## 1. Design thesis

WellBe v1 is strong because it already has the right foundation: a personal data factory, provenance, graph linking, safety, evidence ranking, concern tracking, and investigation tooling.

The research changes the product center of gravity. The platform should not be defined mainly as **a data factory** or as **a chatbot that investigates symptoms**. The stronger design is:

> **WellBe is a Personal Shared Health Memory OS: a user-controlled memory layer for unresolved health concerns, built on a traceable data factory and organized around Health Threads.**

The system's job is to help a person remember, connect, clarify, close, and correct health context across time.

## 2. What stays from WellBe v1

The following v1 ideas remain core:

- personal-first identity
- data factory foundation
- raw context immutability
- source-linked derived facts
- evidence grading
- cross-time, cross-source, cross-domain comparison
- user narrative primacy
- investigate, never diagnose
- safety engine before user-facing AI output
- user-controlled sharing and consent
- compounding longitudinal memory

## 3. What changes

The product identity shifts:

| Original framing | New framing |
|---|---|
| Personal Data Factory first | Personal Shared Health Memory OS, powered by Data Factory |
| Concern Tracker | Health Thread Engine |
| Pattern discovery | Pattern Memory that persists unresolved threads |
| Doctor summary as a feature | User-controlled Visit Packet as a core workflow |
| Investigation triage | Pre-visit + post-visit continuity loop |
| Missing data detection | Missing context + normal-test safety-net layer |
| Medical integration | User-controlled import/share, not institutional default access |

## 4. New core object: Health Thread

A **Health Thread** is a living container for one unresolved or ongoing health concern.

It combines:

- patient's own words
- timeline and baseline change
- symptom episodes
- daily-life impact
- related visits and contacts
- tests/results, including normal-result context
- referrals and their status
- pending items and due dates
- open questions and uncertainty
- patient corrections
- access/language/cost barriers
- source-linked evidence
- clinician-share packet if the user chooses

The product should organize around threads rather than documents, metrics, visits, or isolated symptoms.

## 5. New operating loop

Replace the generic second-brain loop with a medical loop:

**Capture -> Connect -> Clarify -> Close -> Correct**

| Step | Meaning in WellBe | Example output |
|---|---|---|
| Capture | collect raw and structured context | symptom words, lab PDF, referral message, wearable trend |
| Connect | link signals into Health Threads | recurring abdominal pain + ED visit + normal scan + referral |
| Clarify | show known, unknown, missing, pending, and worsening | “Symptoms persist after normal ultrasound; referral not scheduled.” |
| Close | track open loops until resolved, explained, monitored, or safely handed off | pending test due Friday; referral booked; follow-up check-in complete |
| Correct | let user repair the memory | “This symptom started before the medication change, not after.” |

## 6. Six memories adapted for WellBe

| Memory | What it remembers | WellBe role |
|---|---|---|
| Story Memory | patient words, main fear, own theory, daily impact, timeline | protects patient voice and improves visit prep |
| Clinical Memory | diagnoses, meds, labs, imaging, notes, referrals | imports and organizes formal record context |
| Pattern Memory | repeat visits, recurring symptoms, baseline changes, trends | turns comparison engine into useful longitudinal memory |
| Decision Memory | what was considered, uncertain, unresolved, or needs reassessment | later-stage feature; high value but safety-sensitive |
| Responsibility Memory | pending results, referrals, follow-ups, owner/contact, deadlines | closes black zones without pretending to be the health system |
| Equity & Access Memory | language, cost, transport, caregiver, disability, trust and cultural safety | prevents access barriers from disappearing from the story |

WellBe adds a seventh operational memory:

| Memory | What it remembers | Why it matters |
|---|---|---|
| Evidence/Provenance Memory | source, timestamp, confidence, raw input, derived claim, correction history | keeps every output traceable and audit-ready |

## 7. Product promise

The product promise should be:

> **WellBe helps you carry your health context forward until an issue is resolved, explained, monitored, or safely handed off.**

Avoid promises such as:

- “AI doctor”
- “diagnosis engine”
- “rare disease finder”
- “hospital workflow replacement”
- “cross-patient insights by default”

## 8. MVP shape

The MVP should not start with autonomous diagnosis or cross-patient comparison. It should start with:

1. Health Thread creation
2. Story Memory intake
3. timeline and baseline-change capture
4. evidence traceability
5. pending result/referral tracker
6. normal-test safety net
7. patient correction loop
8. user-controlled clinician visit packet
9. post-visit plan checker
10. scoped share/export controls

## 9. Strategic product rule

When research identifies a clinical-system failure, WellBe should translate it into a personal continuity capability.

| Research failure | Do not build first | Build for WellBe |
|---|---|---|
| no named clinical owner | hospital task ledger | personal pending-item memory with official/user-entered/unknown owner labels |
| referral vanished | enterprise referral management | referral lifecycle tracker and visit packet |
| clinician missed repeat visits | clinician alert system | user-visible persistence/repeat-visit view |
| patient voice dismissed | clinician surveillance tool | Story Memory and correction loop |
| normal test closed inquiry | diagnosis predictor | normal-test context and unresolved-symptom safety net |

This keeps the product aligned with the WellBe vision while absorbing the research evidence.
