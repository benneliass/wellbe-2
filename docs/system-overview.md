# WellBe System Overview

> **Generated document — not a bible file.** This is a comprehensive cross-reference of all WellBe sources of truth. It should be regenerated periodically as the project evolves.
>
> **Generated:** 2026-05-31
>
> **Sources:** Bible docs, system design docs, feature backlog, safety docs, architecture docs, decision records, analysis reports, Jira project WEL (belias.atlassian.net), and agent rule files.

---

## 1. Executive Summary

WellBe is a **Personal Shared Health Memory OS** — a user-controlled memory layer that helps individuals carry health context forward until each concern is resolved, explained, monitored, or safely handed off. It is built on a traceable data factory and organized around **Health Threads**, living containers for unresolved health concerns.

The system's core value is longitudinal memory: helping one person understand what is changing in their health, what might be connected, what is still unresolved, and what they should discuss or track next. WellBe achieves this through cross-time, cross-source, and cross-domain synthesis of the individual's own data — never by diagnosing, never by replacing clinical judgment, and never by giving institutions default access to personal health data.

The product operates through a six-step loop — **Capture → Connect → Investigate → Clarify → Close → Correct** — implemented by core components (C1–C17) and feature components. As of this writing, the foundational data pipeline (vault, ingestion, processing, graph store) is implemented at a placeholder level with a rule-based extractor. The full design pipeline, intelligence engines, Health Thread state machine, and user-facing surfaces remain to be built. All 80 Jira tickets are in "To Do" status.

---

## 2. The Problem Space

WellBe exists because health information is fragmented across providers, time, and domains — and patients bear the consequences. The research packages (A–F) that grounded the project's design documented specific, systemic failures:

**Missed diagnoses and delayed recognition.** Symptoms that persist across months or years are treated as isolated encounters. Repeat visits for the same unresolved concern are not connected. Normal test results are treated as closure even when symptoms persist. (Research B, F — PI003, PI006)

**Handoff gaps and referral voids.** A referral placed is confused with a referral completed. Pending test results have no named owner. Post-visit plans — what to watch for, when to return, what is still pending — disappear after the encounter ends. (Research E, F — PI004, PI005, PI016)

**Patient disempowerment in clinical encounters.** The patient's own words, fears, timeline, daily-life impact, and prior theories are lost in short visits or single-symptom intake forms. Patients cannot easily show the sequence of symptoms, tests, visits, and changes over time. (Research C, F — PI002, PI007, PI009)

**Lack of longitudinal health memory.** No system carries the individual's full health context across providers, time, and domains. Clinical records are siloed by institution. Patient-generated data (wearables, mood logs, photos of documents) is disconnected from the clinical record. Access barriers — language, cost, transport, disability — are omitted from the story. (Research F — PI018, PI019, PI020)

**The WellBe reframe:** Where research identifies a clinical-system failure (e.g., "no named owner for abnormal results"), WellBe translates it into a personal continuity capability (e.g., "help the user know what is still open and who to follow up with"). WellBe empowers the patient within the health system — it does not replace or become the system.

*Sources: `VISION.md`, `docs/system-design/system_design.md` §9*

---

## 3. Audience Model

### Primary audience: individuals

Patients, caregivers, and family members managing their own or a dependent's health. The individual is **always** the end-user whose interests the product serves. Every product decision — features, language, defaults, data flows — serves this person first.

### Secondary audience: businesses as distribution channels

Hospitals, clinics, employers, and health platforms that deploy WellBe to their users. The business deploys WellBe; the individual uses it. The business is a **channel** — not a customer, not a data controller.

| Role | Relationship to WellBe |
|---|---|
| Individual (patient/caregiver) | Primary user. Data belongs to this person. |
| Business (hospital, employer) | Deployment channel. No data access unless each individual explicitly grants it. |
| Clinician | Third party the individual may choose to share context with — never a primary user. |

### Hard constraints

- No feature is designed exclusively for businesses. Every feature must make sense from the individual's perspective.
- Cross-patient comparison is always opt-in, user-initiated, and never a business default.
- Deploying businesses are distribution channels, not data controllers.
- Even in B2B deployment: the individual's data belongs to the individual. If the individual leaves the business (e.g., changes employer), their data follows them.

### Cross-patient opt-in model

The default mode is always personal and isolated — one user, their own data, their own intelligence. Cross-referencing against other patients (anonymized or otherwise) is a feature the user explicitly activates. The institution deploying WellBe cannot enable this on behalf of its users.

*Sources: `docs/system-design/platform_identity.md`, `.cursor/rules/audience-guardrails.mdc`*

---

## 4. Core Architecture — The Operating Loop

### Capture → Connect → Investigate → Clarify → Close → Correct

| Step | What it does | Components | Example |
|---|---|---|---|
| **Capture** | Collect raw and structured health context | C2 Raw Context Vault, C3 Ingestion Layer | Symptom words, lab PDF, referral message, wearable trend |
| **Connect** | Link signals into Health Threads via the Knowledge Graph | C4 Processing Pipeline, C5 Evidence & Provenance, C6 Knowledge Graph, C7 Health Thread Engine | Recurring pain + ED visit + normal scan + pending referral |
| **Investigate** | Run a structured research process over a thread: open an Investigation, evaluate Theories, pull personal + external evidence, detect what changed | C14 Investigation Engine, C15 Theory Service, C16 External Evidence Graph, Intelligence Engines (F-ENGINES) | "Investigation: fatigue vs. med change — evidence for/against, missing data flagged" |
| **Clarify** | Surface what is known, unknown, missing, pending, or worsening | C8 Six Memories, Intelligence Engines (F-ENGINES) | "Symptoms persist after normal ultrasound; referral not yet scheduled." |
| **Close** | Track open loops until resolved, explained, monitored, or handed off | C9 Continuity & Closure Engine | Pending test due; referral booked; follow-up complete |
| **Correct** | Let the user repair inaccurate or incomplete memory | C11 Correction Service | "This started before the medication change, not after." |

### Architectural layers

| Layer | Purpose | Core components |
|---|---|---|
| L0 — Trust & consent | User owns scope, sharing, corrections, retention, cross-patient opt-in | C1, C11 |
| L1 — Personal Data Factory | Capture raw context immutably, with provenance | C2, C3 |
| L2 — Extraction & graph | Transform raw data into source-linked entities and relationships | C4, C5, C6 |
| L3 — Health Thread Memory | Represent unresolved concerns as longitudinal threads | C7 |
| L4 — Six Memories | Story, Clinical, Pattern, Decision, Responsibility, Equity/Access memories | C8 |
| L5 — Continuity & closure | Track open loops: pending results, referrals, unresolved symptoms | C9 |
| L6 — Investigation & explanation | Help users ask better questions, see what changed, identify missing context | F-RESEARCH, F-MYTH, F-SAFENET |
| L7 — Safety & governance | Prevent diagnosis claims, panic language, bias amplification, privacy violations | C10, C12 |
| L8 — User surfaces | Dashboard, Health Thread, visit packet, mobile, graph viz | C13, F-PACKET, F-KG-VIZ, F-AUI |

### Three load-bearing relationships

1. **Vault → Provenance → everything (C2 → C5 → …).** Every derived fact carries a chain back to an immutable raw event. Removing C5 breaks "every output has provenance" and "no orphan claims".
2. **Graph ↔ Thread ↔ Engines (C6 ↔ C7 ↔ F-ENGINES).** The Knowledge Graph is the shared substrate; the Health Thread Engine organizes a slice of it around one concern; the Intelligence Engines read the graph and write back first-class objects.
3. **Everything user-facing → Safety Gate → API (… → C10 → C13).** No path exists from an engine, agent, or thread directly to a surface. The gate is the only door to C13 for AI output; if it is down, output is blocked and logged, never passed through.

*Sources: `docs/system-design/architecture.md`, `docs/architecture/core-stack-relations.md`*

---

## 5. Component Map & Implementation Status

### Core components (C1–C13)

| ID | Component | Layer | Purpose | Status | Jira tickets |
|---|---|---|---|---|---|
| C1 | Trust & Consent Service | L0 | Auth identity, consent scopes, share grants, revocation, cross-patient opt-in gate | Planned (MVP) | [WEL-72](https://belias.atlassian.net/browse/WEL-72) (OIDC + consent model, To Do), [WEL-73](https://belias.atlassian.net/browse/WEL-73) (cross-patient gate, post-mvp, To Do) |
| C2 | Raw Context Vault | L1 | Immutable, append-only store of every raw input with full provenance | **Implemented** (placeholder) | [WEL-80](https://belias.atlassian.net/browse/WEL-80) (vault store, To Do) |
| C3 | Ingestion Layer | L1 | Source-type adapters writing into the Vault | **Implemented** (placeholder) | [WEL-81](https://belias.atlassian.net/browse/WEL-81) (adapters + processing, To Do) |
| C4 | Processing Pipeline | L2 | Entity/fact/signal extraction + quality/confidence scoring | **Implemented** (rule-based keyword extractor only) | [WEL-81](https://belias.atlassian.net/browse/WEL-81), [WEL-82](https://belias.atlassian.net/browse/WEL-82) (OCR pipeline, To Do) |
| C5 | Evidence & Provenance | L2 | Links every derived fact to its raw source; enforces "no orphan claims" | **Implemented** (basic linking) | [WEL-83](https://belias.atlassian.net/browse/WEL-83) (evidence service, To Do) |
| C6 | Knowledge Graph Store | L2 | Typed nodes + evidence-weighted edges | **Implemented** (nodes only, 0 edges — auto-linker unbuilt) | [WEL-77](https://belias.atlassian.net/browse/WEL-77) (graph store + auto-linker, post-mvp, To Do) |
| C7 | Health Thread Engine + State Machine | L3 | Central product object: lifecycle, linking, status | Planned (MVP) | [WEL-64](https://belias.atlassian.net/browse/WEL-64) (state machine, To Do) |
| C8 | Six Memories Store | L4 | Story, Clinical, Pattern, Decision, Responsibility, Equity/Access memories | Planned (MVP partial) | [WEL-70](https://belias.atlassian.net/browse/WEL-70) (memory models, To Do) |
| C9 | Continuity & Closure Engine | L5 | Pending item ledger, referral lifecycle, result tracker, post-visit plan checker | Planned (MVP) | [WEL-67](https://belias.atlassian.net/browse/WEL-67) (continuity engine, To Do) |
| C10 | Safety & Governance Gate | L7 | Mandatory gate before any user-facing AI output | Planned (MVP) | [WEL-74](https://belias.atlassian.net/browse/WEL-74) (safety gate, To Do) |
| C11 | Correction Service | L0/L4 | User repairs as new source-linked layers; never overwrites raw/derived | Planned (MVP) | [WEL-71](https://belias.atlassian.net/browse/WEL-71) (correction service, To Do) |
| C12 | Notification & Audit Service | L7 | Append-only audit trail + low-alarm notifications | Planned (MVP) | [WEL-75](https://belias.atlassian.net/browse/WEL-75) (notification + audit, To Do) |
| C13 | API & Contract Layer | L8 | REST/OpenAPI surface + webhooks; single contract boundary | Planned (MVP) | [WEL-65](https://belias.atlassian.net/browse/WEL-65) (API layer, To Do) |

### Feature components

| ID | Feature | Feature IDs | Layer | Phase | Jira tickets |
|---|---|---|---|---|---|
| F-MOOD | Mood / Energy Logging | WB2-F034 | L1 | MVP | [WEL-36](https://belias.atlassian.net/browse/WEL-36), [WEL-85](https://belias.atlassian.net/browse/WEL-85) |
| F-PEND | Pending / Referral / Result trackers | WB2-F007/F008/F020 | L5 | MVP | [WEL-26](https://belias.atlassian.net/browse/WEL-26), [WEL-27](https://belias.atlassian.net/browse/WEL-27), [WEL-31](https://belias.atlassian.net/browse/WEL-31) |
| F-PACKET | Visit Packet + Scoped Share/Export | WB2-F011/F024 | L8 | MVP | [WEL-30](https://belias.atlassian.net/browse/WEL-30), [WEL-34](https://belias.atlassian.net/browse/WEL-34), [WEL-68](https://belias.atlassian.net/browse/WEL-68) |
| F-SAFENET | Normal-test safety net | WB2-F006 | L6 | MVP | [WEL-25](https://belias.atlassian.net/browse/WEL-25), [WEL-69](https://belias.atlassian.net/browse/WEL-69) |
| F-KG-VIZ | Knowledge Graph Visualization | WB2-F033 | L8 | Post-MVP | [WEL-35](https://belias.atlassian.net/browse/WEL-35), [WEL-78](https://belias.atlassian.net/browse/WEL-78) |
| F-ENGINES | Intelligence Engine Suite | WB2-F042 | L3/L4 | Post-MVP | [WEL-37](https://belias.atlassian.net/browse/WEL-37), [WEL-79](https://belias.atlassian.net/browse/WEL-79) |
| F-RESEARCH | Research Agent | WB2-F036 | L6 | Post-MVP | [WEL-39](https://belias.atlassian.net/browse/WEL-39), [WEL-86](https://belias.atlassian.net/browse/WEL-86) |
| F-MYTH | Myth Buster | WB2-F035 | L6 | Post-MVP | [WEL-38](https://belias.atlassian.net/browse/WEL-38), [WEL-87](https://belias.atlassian.net/browse/WEL-87) |
| F-ENV | Environmental Context Ingestion | WB2-F037 | L1 | Post-MVP | [WEL-40](https://belias.atlassian.net/browse/WEL-40), [WEL-88](https://belias.atlassian.net/browse/WEL-88) |
| F-WEAR | Wearable Integration | WB2-F039 | L1 | Post-MVP | [WEL-41](https://belias.atlassian.net/browse/WEL-41), [WEL-89](https://belias.atlassian.net/browse/WEL-89) |
| F-XDEV | Cross-Device Intelligence | WB2-F038 | L2 | Post-MVP | [WEL-42](https://belias.atlassian.net/browse/WEL-42) |
| F-AUI | Health-Adaptive UI | WB2-F040 | L8 | Post-MVP | [WEL-43](https://belias.atlassian.net/browse/WEL-43), [WEL-91](https://belias.atlassian.net/browse/WEL-91) |
| F-FHIR | Medical Institution Integration | WB2-F041 | L1 | Deferred | [WEL-49](https://belias.atlassian.net/browse/WEL-49), [WEL-90](https://belias.atlassian.net/browse/WEL-90) |

**Implementation note:** C2–C6 exist at a placeholder level. The benchmark corpus (5 cases, 197 events) runs through the pipeline end-to-end, producing 201 facts and 186 graph nodes — but using a 10-symptom/4-medication keyword extractor that produces only `Symptom`, `Medication`, and `Other` node types with zero graph edges. The designed LLM/NER extractor, auto-linker, intelligence engines, and Health Thread state machine are all unbuilt.

*Sources: `docs/architecture/component-map.md`, `docs/architecture/development-backlog.md`*

---

## 6. Feature Inventory

### Epic E1: Health Thread Core (WEL-12) — MVP, Highest priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Health Thread core object and lifecycle | WB2-F001 | MVP | strong | [WEL-22](https://belias.atlassian.net/browse/WEL-22), [WEL-64](https://belias.atlassian.net/browse/WEL-64) | To Do |
| Evidence traceability layer 2.0 | WB2-F004 | MVP | strong | [WEL-23](https://belias.atlassian.net/browse/WEL-23) | To Do |
| Health Thread timeline and evidence graph | WB2-F005 | Post-MVP | strong | [WEL-60](https://belias.atlassian.net/browse/WEL-60) | To Do |
| API & Contract Layer | — | MVP | — | [WEL-65](https://belias.atlassian.net/browse/WEL-65) | To Do |

### Epic E2: Care Continuity (WEL-13) — MVP, High priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Normal-test safety net | WB2-F006 | MVP | strong | [WEL-25](https://belias.atlassian.net/browse/WEL-25), [WEL-69](https://belias.atlassian.net/browse/WEL-69) | To Do |
| Personal pending result tracker | WB2-F007 | MVP | strong | [WEL-26](https://belias.atlassian.net/browse/WEL-26) | To Do |
| Referral lifecycle tracker | WB2-F008 | MVP | strong | [WEL-27](https://belias.atlassian.net/browse/WEL-27) | To Do |
| Post-visit plan checker | WB2-F009 | MVP | strong/some | [WEL-28](https://belias.atlassian.net/browse/WEL-28) | To Do |
| User-controlled clinician visit packet | WB2-F011 | MVP | strong | [WEL-30](https://belias.atlassian.net/browse/WEL-30), [WEL-68](https://belias.atlassian.net/browse/WEL-68) | To Do |
| Personal Responsibility Memory ledger | WB2-F020 | MVP | strong | [WEL-31](https://belias.atlassian.net/browse/WEL-31) | To Do |
| Repeat-visit and persistence view | WB2-F012 | Near-term | strong | [WEL-44](https://belias.atlassian.net/browse/WEL-44) | To Do |
| Low-resource / CHW / SMS mode | WB2-F026 | Regional | regional | [WEL-54](https://belias.atlassian.net/browse/WEL-54) | To Do |
| Workload-aware alert mode | WB2-F028 | Deferred | caution | [WEL-61](https://belias.atlassian.net/browse/WEL-61) | To Do |
| Continuity & Closure Engine | — | MVP | — | [WEL-67](https://belias.atlassian.net/browse/WEL-67) | To Do |

### Epic E3: Memory Layer (WEL-14) — MVP, High priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Story Memory intake | WB2-F002 | MVP | strong | [WEL-24](https://belias.atlassian.net/browse/WEL-24) | To Do |
| Baseline change and function impact capture | WB2-F003 | MVP | strong | [WEL-32](https://belias.atlassian.net/browse/WEL-32) | To Do |
| Patient correction loop | WB2-F010 | MVP | strong | [WEL-29](https://belias.atlassian.net/browse/WEL-29), [WEL-71](https://belias.atlassian.net/browse/WEL-71) | To Do |
| Access and equity memory | WB2-F015 | Near-term | strong/regional | [WEL-33](https://belias.atlassian.net/browse/WEL-33) | To Do |
| Scoped share link / export | WB2-F024 | MVP | strong | [WEL-34](https://belias.atlassian.net/browse/WEL-34) | To Do |
| Decision and uncertainty memory | WB2-F030 | Later | caution | [WEL-59](https://belias.atlassian.net/browse/WEL-59) | To Do |
| Six Memories Store | — | MVP | — | [WEL-70](https://belias.atlassian.net/browse/WEL-70) | To Do |

### Epic E4: Safety and Privacy (WEL-15) — MVP, Highest priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Deterioration check-in and escalation guidance | WB2-F019 | Near-term | strong/regional | [WEL-47](https://belias.atlassian.net/browse/WEL-47) | To Do |
| Bias/misattribution reflection | WB2-F027 | Deferred | caution | [WEL-55](https://belias.atlassian.net/browse/WEL-55) | To Do |
| Trust & Consent Service (OIDC + consent model) | — | MVP | — | [WEL-72](https://belias.atlassian.net/browse/WEL-72) | To Do |
| Cross-patient opt-in gate | — | Post-MVP | — | [WEL-73](https://belias.atlassian.net/browse/WEL-73) | To Do |
| Safety & Governance Gate | — | MVP | — | [WEL-74](https://belias.atlassian.net/browse/WEL-74) | To Do |
| Notification & Audit Service | — | MVP | — | [WEL-75](https://belias.atlassian.net/browse/WEL-75) | To Do |
| Infra + observability + security | — | MVP | — | [WEL-76](https://belias.atlassian.net/browse/WEL-76) | To Do |

### Epic E5: Knowledge Graph (WEL-16) — Post-MVP, Medium priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Knowledge graph and visualization | WB2-F033 | Post-MVP | strong | [WEL-35](https://belias.atlassian.net/browse/WEL-35), [WEL-78](https://belias.atlassian.net/browse/WEL-78) | To Do |
| Health Thread timeline and evidence graph | WB2-F005 | Post-MVP | strong | [WEL-60](https://belias.atlassian.net/browse/WEL-60) | To Do |
| Knowledge Graph Store (+ auto-linker) | — | Post-MVP | — | [WEL-77](https://belias.atlassian.net/browse/WEL-77) | To Do |

### Epic E6: Intelligence Engines (WEL-17) — Post-MVP, Medium priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Intelligence engines (pattern, temporal, confounder, contradiction, missing data) | WB2-F042 | Post-MVP | strong | [WEL-37](https://belias.atlassian.net/browse/WEL-37), [WEL-79](https://belias.atlassian.net/browse/WEL-79) | To Do |
| Missing context checklist | WB2-F013 | Near-term | some/strong | [WEL-45](https://belias.atlassian.net/browse/WEL-45) | To Do |
| Lab trend and personal baseline explorer | WB2-F016 | Near-term | some | [WEL-50](https://belias.atlassian.net/browse/WEL-50) | To Do |
| Note/document delta view | WB2-F018 | Later | some | [WEL-56](https://belias.atlassian.net/browse/WEL-56) | To Do |
| Cross-specialty pattern map | WB2-F029 | Later | some | [WEL-58](https://belias.atlassian.net/browse/WEL-58) | To Do |
| Trend-over-noise PGHD summarizer | WB2-F023 | Near-term | some | [WEL-53](https://belias.atlassian.net/browse/WEL-53) | To Do |

### Epic E7: Data Capture (WEL-18) — MVP, High priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Mood and energy logging | WB2-F034 | MVP | strong | [WEL-36](https://belias.atlassian.net/browse/WEL-36), [WEL-85](https://belias.atlassian.net/browse/WEL-85) | To Do |
| Medication and access clue capture | WB2-F017 | Near-term | some | [WEL-51](https://belias.atlassian.net/browse/WEL-51) | To Do |
| Environmental context ingestion | WB2-F037 | Post-MVP | strong | [WEL-40](https://belias.atlassian.net/browse/WEL-40), [WEL-88](https://belias.atlassian.net/browse/WEL-88) | To Do |
| Raw Context Vault | — | MVP | — | [WEL-80](https://belias.atlassian.net/browse/WEL-80) | To Do |
| Ingestion + Processing Pipeline | — | MVP | — | [WEL-81](https://belias.atlassian.net/browse/WEL-81) | To Do |
| OCR Pipeline | — | MVP | — | [WEL-82](https://belias.atlassian.net/browse/WEL-82) | To Do |
| Evidence & Provenance Service | — | MVP | — | [WEL-83](https://belias.atlassian.net/browse/WEL-83) | To Do |
| Event backbone + Temporal | — | MVP | — | [WEL-84](https://belias.atlassian.net/browse/WEL-84) | To Do |

### Epic E8: External Intelligence (WEL-19) — Post-MVP, Low priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Myth Buster — personal theory evaluator | WB2-F035 | Post-MVP | strong | [WEL-38](https://belias.atlassian.net/browse/WEL-38), [WEL-87](https://belias.atlassian.net/browse/WEL-87) | To Do |
| Research Agent — external evidence lookup | WB2-F036 | Post-MVP | product supported | [WEL-39](https://belias.atlassian.net/browse/WEL-39), [WEL-86](https://belias.atlassian.net/browse/WEL-86) | To Do |
| Safe research and explanation mode | WB2-F021 | Near-term | internal + safety | [WEL-48](https://belias.atlassian.net/browse/WEL-48) | To Do |
| Personal experiment guardrails | WB2-F022 | Later | needs more evidence | [WEL-52](https://belias.atlassian.net/browse/WEL-52) | To Do |

### Epic E9: Integrations (WEL-20) — Post-MVP, Low priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Wearable integration | WB2-F039 | Post-MVP | product supported | [WEL-41](https://belias.atlassian.net/browse/WEL-41), [WEL-89](https://belias.atlassian.net/browse/WEL-89) | To Do |
| Cross-device intelligence | WB2-F038 | Post-MVP | product supported | [WEL-42](https://belias.atlassian.net/browse/WEL-42) | To Do |
| Patient-held record import | WB2-F014 | Near-term | regional/strong | [WEL-46](https://belias.atlassian.net/browse/WEL-46) | To Do |
| Medical institution integration (FHIR) | WB2-F041 | Deferred | complex | [WEL-49](https://belias.atlassian.net/browse/WEL-49), [WEL-90](https://belias.atlassian.net/browse/WEL-90) | To Do |
| Care-team comment mode | WB2-F025 | Later | some | [WEL-57](https://belias.atlassian.net/browse/WEL-57) | To Do |
| Doctor discovery as pathway support | WB2-F031 | Later | some | [WEL-62](https://belias.atlassian.net/browse/WEL-62) | To Do |

### Epic E10: UI Layer (WEL-21) — Post-MVP, Medium priority

| Feature | ID | Phase | Evidence | Jira | Status |
|---|---|---|---|---|---|
| Health-adaptive UI | WB2-F040 | Post-MVP | product supported | [WEL-43](https://belias.atlassian.net/browse/WEL-43), [WEL-91](https://belias.atlassian.net/browse/WEL-91) | To Do |
| Cross-patient comparison sandbox | WB2-F032 | Deferred | needs more evidence | [WEL-63](https://belias.atlassian.net/browse/WEL-63) | To Do |

*Sources: `docs/feature-backlog/feature_backlog.md`, `docs/feature-backlog/mvp_plan.md`, `docs/architecture/development-backlog.md`, Jira project WEL*

---

## 7. Safety Model Summary

### Core safety posture

WellBe is a memory and investigation support system, not a diagnostic authority. The Safety & Governance Gate (C10) evaluates every user-facing AI output before it reaches the user. No assistant, agent, summary generator, or research mode can bypass it.

### The 8 safety layers

| # | Layer | What it guards against |
|---|---|---|
| 1 | Scope safety | Feature outside personal-first WellBe scope |
| 2 | Data safety | Claims not source-linked or not labeled by type/quality |
| 3 | Language safety | Output uses diagnosis, blame, panic, or certainty language |
| 4 | Urgency safety | Urgent content that routes without care advice or delays care |
| 5 | Privacy safety | Sharing not user-scoped, not revocable, or not minimal |
| 6 | Bias safety | Stigmatizing labels, demographic shortcuts |
| 7 | Workflow safety | Overloading clinicians or implying false ownership |
| 8 | Monitoring safety | False positives, false negatives, ignored alerts, outcomes not reviewed |

### The do-not-diagnose invariant

WellBe must **never** output diagnostic conclusions, rule conditions in or out, give prescriptive medical instructions, or present ranked differential diagnosis lists. The strongest permitted causal language in the Knowledge Graph is `may_explain`. Contradictions are preserved, never auto-resolved. Every health claim must be labeled by source type and confidence level. A claim with no traceable source may not be surfaced.

### Safety Gate architecture (C10)

Three-layer design:
1. **Deterministic rule checks** — do-not-diagnose lexicon, panic-language detection, provenance-present verification
2. **NeMo Guardrails** — Colang rails for structured safety checking
3. **Safety classifier** — Llama Guard / equivalent for content classification

The gate runs as its own isolated Kubernetes service. If it is unavailable, AI output is blocked (`ai_output.blocked`), never passed through. This makes "investigate, never diagnose" structurally enforced.

**Implementation status:** Planned. [WEL-74](https://belias.atlassian.net/browse/WEL-74) (To Do, MVP, High priority).

*Sources: `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`, `docs/architecture/tech-stack.md` §8*

---

## 8. Design Principles

The 12 non-negotiable system principles from `docs/system-design/system_principles.md`:

1. **Personal-first, always.** The individual remains the primary user and controller.
2. **Data Factory underneath, Health Memory on top.** Data ingestion is foundation; the user value is memory and continuity.
3. **Threads, not files.** Unresolved health concerns are the main product object.
4. **Patient voice is evidence, but not diagnosis.** Preserve raw words and corrections while labeling them as patient-reported.
5. **Every output has provenance.** No orphan claims, no unsupported summaries.
6. **Uncertainty is a product object.** Track what is known, unknown, missing, pending, and unresolved.
7. **Closure beats visibility.** A visible result/referral is not enough; the user needs status, next step, and follow-up memory.
8. **Investigate, never diagnose.** The platform asks better questions; it does not give final medical answers.
9. **Concise by default, deep on demand.** Clinician packets and user views must not become data dumps.
10. **Global by configuration, not one-size-fits-all.** Care-flow model, resources, language, and access barriers change the product behavior.
11. **Correction is safety infrastructure.** The user can repair wrong, missing, or stale memory.
12. **No institutional overreach.** Sharing, clinician access, cross-patient comparison, and integrations remain user-controlled.

---

## 9. Intelligence Engines

Five background engines that transform raw Health Thread data into insight, operating on the Knowledge Graph and feeding results into the Clarify step. All are post-MVP.

| Engine | Purpose | Safety constraint | Jira |
|---|---|---|---|
| **Pattern Detection** | Find recurring structures — co-occurrence, compound triggers, episode clusters | Patterns surfaced as observations, never conclusions | [WEL-79](https://belias.atlassian.net/browse/WEL-79) |
| **Temporal Analysis** | Determine order of events — time-lagged correlations, temporal precedence | "Correlation only" framing; no clinical ordering claims | [WEL-79](https://belias.atlassian.net/browse/WEL-79) |
| **Confounder Detection** | When pattern A→B is detected, identify if third variable C explains both | Guards against spurious causal claims | [WEL-79](https://belias.atlassian.net/browse/WEL-79) |
| **Missing Data** | Surface context gaps that would clarify a thread or resolve ambiguity | Framed as opportunities, not alarms; never implies hidden diagnosis | [WEL-79](https://belias.atlassian.net/browse/WEL-79) |
| **Contradiction Resolution** | Find conflicting signals and preserve them as explicit contradictions | Never auto-resolves; both sides preserved until user action or new evidence | [WEL-79](https://belias.atlassian.net/browse/WEL-79) |

Engines run in sequence when triggered: Pattern → Confounder → Temporal → Missing Data → Contradiction. All outputs are stored as first-class objects (not just UI annotations), source-linked, correctable, and auditable.

**Implementation status:** Not implemented. All intelligence engine work is under [WEL-79](https://belias.atlassian.net/browse/WEL-79) (Post-MVP, Medium priority, To Do).

*Source: `docs/system-design/intelligence_engines.md`*

---

## 10. Integrations

All integrations are user-initiated, user-controlled, and user-revocable. They write through the same ingestion path (C3 → C2 → C4 → C6).

| Integration | Phase | Description | Privacy | Jira |
|---|---|---|---|---|
| **Wearable Integration** | Post-MVP | Import biometric streams (HR, HRV, sleep, SpO2, steps, CGM) from HealthKit/Health Connect + device APIs | City-level location only; raw biometrics never shared with third parties | [WEL-41](https://belias.atlassian.net/browse/WEL-41), [WEL-89](https://belias.atlassian.net/browse/WEL-89) |
| **Cross-Device Intelligence** | Post-MVP | Baseline/drift/asymmetry detection across paired devices; requires 14-day baseline | No insight before baseline completes; asymmetry framed as "persistent difference" | [WEL-42](https://belias.atlassian.net/browse/WEL-42) |
| **Environmental Context** | Post-MVP | Weather, air quality, pollen, UV, public health alerts, conflict proximity (opt-in) | City-level granularity; precise coordinates never stored; conflict/news explicitly opt-in | [WEL-40](https://belias.atlassian.net/browse/WEL-40), [WEL-88](https://belias.atlassian.net/browse/WEL-88) |
| **Medical Institution (FHIR)** | Deferred | User-pull FHIR R4 import of own records; user authenticates directly with institution | User is data controller; WellBe never writes back to EHR; institution cannot see WellBe data without explicit user share | [WEL-49](https://belias.atlassian.net/browse/WEL-49), [WEL-90](https://belias.atlassian.net/browse/WEL-90) |

*Source: `docs/system-design/integrations.md`*

---

## 11. Infrastructure

### The hard rule: Kubernetes-native

WellBe workloads are Kubernetes-native from day one. Fly.io, standalone Docker-run services, and PaaS container platforms are not valid deployment targets. Every Kubernetes object must be managed through a Helm chart.

### Tech stack summary

| Concern | Choice |
|---|---|
| Backend | Python 3.13 + FastAPI + Pydantic v2 |
| Frontend | TypeScript + Next.js 15 + React 19 + Expo (mobile) |
| UI kit | Tailwind + Radix/shadcn |
| Primary datastore | PostgreSQL 17 (managed by CloudNativePG operator) |
| Vector/embeddings | pgvector (+ pgvectorscale) |
| Graph | Apache AGE (Cypher) on Postgres |
| Time-series | TimescaleDB |
| Events | Transactional outbox + Redis Streams |
| Durable workflows | Temporal |
| Lightweight jobs | Dramatiq (Redis broker) |
| Auth/identity | ZITADEL (self-hosted OIDC) + WebAuthn/passkeys |
| LLM orchestration | LangGraph (inside Temporal activities) |
| Safety gate | Rules engine + NeMo Guardrails + Llama Guard |
| OCR | Hybrid: PaddleOCR-VL/Tesseract → vision-LLM fallback |
| Graph viz | Cytoscape.js (thread-scoped) + Sigma.js v3 (investigation landscape) |

### Infrastructure stack

| Concern | Choice |
|---|---|
| Orchestration | Kubernetes (EKS/GKE/k3s) |
| Postgres HA | CloudNativePG operator |
| Networking | Cilium (eBPF) + Gateway API |
| Node autoscaling | Karpenter |
| IaC | OpenTofu (+ Terramate) with native state encryption |
| CI/CD | GitHub Actions + Flux (GitOps) |
| Secrets | OpenBao + External Secrets Operator + KMS envelope encryption |
| Observability | OpenTelemetry + Grafana LGTM (Prometheus/Mimir, Loki, Tempo) |
| Local dev | Docker Compose (data services) + `uv run` / `k3d` |

### K8s workload map (MVP)

API, vault-writer, ingestion-worker, processing-worker, temporal-worker, safety-gate (isolated namespace), continuity-worker, notification-worker, web, postgres (CloudNativePG), redis, temporal-server (Helm), zitadel (Helm).

**Implementation status:** Local Kind cluster is operational with data services, ingestion, processing, and vault workers running. [WEL-76](https://belias.atlassian.net/browse/WEL-76) covers full infra buildout (To Do, MVP, High).

*Sources: `docs/architecture/tech-stack.md`, `docs/architecture/infra-stack.md`, `.cursor/rules/infra-constraints.mdc`*

---

## 12. Benchmark & Verification

### Benchmark corpus

5 de-identified longitudinal cases (C01–C05) provided in two modes (`blind_pre_diagnosis` and `full_results_no_final_label`). 452 total events across both modes. No answer keys or final labels — consistent with do-not-diagnose posture.

| Case | Narrative | Blind events | Full events |
|---|---|---|---|
| C01 | Chronic multi-year systemic inflammatory/GI course | 51 | 56 |
| C02 | Multi-system (cardiac → neuro-cognitive → renal) decline | 47 | 59 |
| C03 | Acute febrile inflammatory syndrome, steroid-responsive | 36 | 49 |
| C04 | Post-exposure neuro/myelopathy, steroid-responsive | 36 | 46 |
| C05 | Chronic GI with cardiac involvement in full mode | 27 | 45 |

### Prediction vs. actual verification (2026-05-31)

The forward prediction report was verified against the live Kind cluster. Results for the blind mode (the only mode seeded):

| Metric | Predicted (blind) | Actual | Match |
|---|---|---|---|
| C2 vault events | 197 | 197 (+1 stray) | Exact |
| C4 extracted facts | 201 | 201 (+3 stray) | Exact |
| C6 graph nodes | 186 | 186 (+3 stray) | Exact |
| C6 graph edges | 0 | 0 | Exact |
| Symptom/Medication node identities | All predicted | All confirmed | Exact |

**Key finding:** The deterministic prediction was accurate to the unit on every count. The designed pipeline (LLM extractor, auto-linker, intelligence engines, Health Threads) would produce ~679 facts, ~407 nodes, and ~531 edges — but that pipeline is unbuilt. The current keyword-only extractor captures only 3 of 25+ intended node types.

**One operational artifact:** C5 evidence links have ~2x the expected rows due to duplicate C4 processing (at-least-once delivery). Facts and nodes are idempotent; evidence links are not.

*Sources: `docs/analysis/benchmark-expected-results.md`, `docs/analysis/benchmark-prediction-vs-actual.md`*

---

## 13. Jira Project Health

### Ticket totals (as of 2026-05-31)

| Metric | Count |
|---|---|
| **Total tickets** | 80 |
| Epics | 10 |
| Stories (feature-level) | 42 (WEL-22 to WEL-63) |
| Stories (development-level) | 28 (WEL-64 to WEL-91) |

### By status

| Status | Count |
|---|---|
| To Do | **80** (100%) |
| In Progress | 0 |
| Done | 0 |

### By priority

| Priority (Jira name) | Tier | Count |
|---|---|---|
| Highest | P0 | 2 Epics (WEL-12, WEL-15) |
| High | P1-critical | 24 (2 Epics + 22 Stories) |
| Medium | P2-important | 25 (3 Epics + 22 Stories) |
| Low | P3-backlog | 29 (2 Epics + 27 Stories) |

### By phase (fix version)

| Phase | Epics | Stories |
|---|---|---|
| mvp | 4 (E1, E2, E3, E4) + E7, E8 partial | ~26 Stories |
| post-mvp | 4 (E5, E6, E9, E10) | ~18 Stories |
| deferred | — | 3 Stories (WEL-49 FHIR, WEL-63 cross-patient, WEL-90 FHIR dev) |

### Triage health

- All items carry `triage-2026-05-30-001` or `triage-2026-05-30-002` labels
- All items carry `re-eval:clean` — no items flagged `re-eval:needs-review` or `re-eval:blocked-by-change`
- **No orphan tickets** (all carry triage labels)
- **No bug tickets** — project is pre-implementation
- **1 cancelled item:** WEL-66 (WB-DEV-206, Profile B migration — obsolete, system is K8s-native from day one)

### Decision records

12 approved decision records in `docs/decisions/`:

| Decision record | Component | Status |
|---|---|---|
| `trust-consent-scope-enforcement-pattern` | C1 | Approved |
| `raw-context-vault-immutability-enforcement` | C2 | Approved |
| `ingestion-adapter-provenance-pattern` | C3 | Approved |
| `processing-pipeline-extraction-orchestration` | C4 | Approved |
| `c4-extraction-scope-split-wel81-wel82` | C4 | Approved |
| `evidence-provenance-no-orphan-enforcement` | C5 | Approved |
| `knowledge-graph-node-edge-schema` | C6 | Approved |
| `research-brief-c6-graph-visualization` | C6 (viz) | Approved |
| `health-thread-state-machine-enforcement` | C7 | Approved |
| `research-brief-c1-c6` | C1–C6 (research) | Approved |
| `research-brief-repo-structure` | Platform | Approved |

---

## 14. What's Next

### Immediate priorities (MVP)

1. **C1 Trust & Consent** — OIDC/ZITADEL integration, consent-scope + share-grant domain model ([WEL-72](https://belias.atlassian.net/browse/WEL-72))
2. **C2 Raw Context Vault** — production-grade immutable store with S3 object-lock ([WEL-80](https://belias.atlassian.net/browse/WEL-80))
3. **C4 Processing Pipeline** — replace keyword extractor with LLM/NER clinical extractor ([WEL-81](https://belias.atlassian.net/browse/WEL-81))
4. **C7 Health Thread Engine** — implement the core product object and state machine ([WEL-64](https://belias.atlassian.net/browse/WEL-64))
5. **C10 Safety Gate** — layered safety service, fail-closed ([WEL-74](https://belias.atlassian.net/browse/WEL-74))
6. **C13 API & Contract Layer** — FastAPI REST surface with OpenAPI contract ([WEL-65](https://belias.atlassian.net/browse/WEL-65))
7. **Event backbone + Temporal** — transactional outbox, durable workflows ([WEL-84](https://belias.atlassian.net/browse/WEL-84))

### Known gaps and blockers

- **The auto-linker (C6 edge creation) is unbuilt.** The graph has nodes but zero edges. This blocks all Intelligence Engines and meaningful graph visualization.
- **The C4 extractor is a placeholder.** Only 10 symptom + 4 medication keywords are recognized. The designed LLM/NER extractor is needed before the pipeline produces clinically useful output.
- **Evidence links are non-idempotent.** Duplicate C4 processing creates orphan evidence links. The `insert_fact` and `link_fact` paths need `ON CONFLICT` / dedup handling.
- **Only `blind_pre_diagnosis` mode is seeded in the benchmark.** The `full_results_no_final_label` mode events have not been loaded yet.
- **FHIR integration is deferred** pending jurisdiction-specific compliance review.

### Pending decisions

No open Spikes or unresolved Decision Records at this time. All 12 decision records for C1–C7 are approved.

---

## 15. Cross-Reference Index

### A. Jira tickets by Epic

#### E1: Health Thread Core (WEL-12)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-12 | E1: Health Thread Core | Epic | Highest | mvp | To Do |
| WEL-22 | WB2-F001: Health Thread core object and lifecycle | Story | High | mvp | To Do |
| WEL-23 | WB2-F004: Evidence traceability layer | Story | High | mvp | To Do |
| WEL-64 | Health Thread object + state machine (WB-DEV-011) | Story | High | mvp | To Do |
| WEL-65 | API & Contract Layer (WB-DEV-018) | Story | High | mvp | To Do |
| WEL-66 | ~~Profile B migration~~ (WB-DEV-206) — obsolete | Story | Low | post-mvp | To Do |

#### E2: Care Continuity (WEL-13)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-13 | E2: Care Continuity | Epic | High | mvp | To Do |
| WEL-25 | WB2-F006: Normal-test safety net | Story | High | mvp | To Do |
| WEL-26 | WB2-F007: Personal pending result tracker | Story | High | mvp | To Do |
| WEL-27 | WB2-F008: Referral lifecycle tracker | Story | High | mvp | To Do |
| WEL-28 | WB2-F009: Post-visit plan checker | Story | High | mvp | To Do |
| WEL-30 | WB2-F011: User-controlled clinician visit packet | Story | High | mvp | To Do |
| WEL-31 | WB2-F020: Personal Responsibility Memory ledger | Story | High | mvp | To Do |
| WEL-44 | WB2-F012: Repeat-visit and persistence view | Story | High | near-term | To Do |
| WEL-54 | WB2-F026: Low-resource, CHW, and SMS mode | Story | Medium | regional | To Do |
| WEL-61 | WB2-F028: Workload-aware alert mode (deferred) | Story | Low | deferred | To Do |
| WEL-67 | Continuity & Closure Engine (WB-DEV-013/014) | Story | High | mvp | To Do |
| WEL-68 | Visit Packet + Scoped Share (WB-DEV-102) | Story | High | mvp | To Do |
| WEL-69 | Normal-test safety net (WB-DEV-103) | Story | High | mvp | To Do |

#### E3: Memory Layer (WEL-14)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-14 | E3: Memory Layer | Epic | High | mvp | To Do |
| WEL-24 | WB2-F002: Story Memory intake | Story | High | mvp | To Do |
| WEL-29 | WB2-F010: Patient correction loop | Story | High | mvp | To Do |
| WEL-32 | WB2-F003: Baseline change and function impact capture | Story | High | mvp | To Do |
| WEL-33 | WB2-F015: Access and equity memory | Story | Medium | near-term | To Do |
| WEL-34 | WB2-F024: Scoped share link and export | Story | High | mvp | To Do |
| WEL-59 | WB2-F030: Decision and uncertainty memory | Story | Medium | later | To Do |
| WEL-70 | Six Memories Store (WB-DEV-012) | Story | High | mvp | To Do |
| WEL-71 | Correction Service (WB-DEV-016) | Story | High | mvp | To Do |

#### E4: Safety and Privacy (WEL-15)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-15 | E4: Safety and Privacy | Epic | Highest | mvp | To Do |
| WEL-47 | WB2-F019: Deterioration check-in and escalation | Story | High | near-term | To Do |
| WEL-55 | WB2-F027: Bias and misattribution reflection | Story | Low | deferred | To Do |
| WEL-72 | Trust & Consent (WB-DEV-001/002) | Story | High | mvp | To Do |
| WEL-73 | Cross-patient opt-in gate (WB-DEV-003) | Story | Medium | post-mvp | To Do |
| WEL-74 | Safety Gate (WB-DEV-015) | Story | High | mvp | To Do |
| WEL-75 | Notification & Audit (WB-DEV-017) | Story | Medium | mvp | To Do |
| WEL-76 | Infra + observability + security (WB-DEV-201–205) | Story | High | mvp | To Do |

#### E5: Knowledge Graph (WEL-16)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-16 | E5: Knowledge Graph | Epic | Medium | post-mvp | To Do |
| WEL-35 | WB2-F033: Knowledge graph and visualization | Story | Medium | post-mvp | To Do |
| WEL-60 | WB2-F005: Health Thread timeline and evidence graph | Story | Medium | post-mvp | To Do |
| WEL-77 | Knowledge Graph Store (WB-DEV-009/010) | Story | Medium | post-mvp | To Do |
| WEL-78 | Graph Visualization (WB-DEV-104) | Story | Medium | post-mvp | To Do |

#### E6: Intelligence Engines (WEL-17)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-17 | E6: Intelligence Engines | Epic | Medium | post-mvp | To Do |
| WEL-37 | WB2-F042: Intelligence engines core | Story | Medium | post-mvp | To Do |
| WEL-45 | WB2-F013: Missing context checklist | Story | Medium | near-term | To Do |
| WEL-50 | WB2-F016: Lab trend and personal baseline explorer | Story | Medium | near-term | To Do |
| WEL-53 | WB2-F023: Trend-over-noise PGHD summarizer | Story | Medium | near-term | To Do |
| WEL-56 | WB2-F018: Note and document delta view | Story | Medium | later | To Do |
| WEL-58 | WB2-F029: Cross-specialty pattern map | Story | Medium | later | To Do |
| WEL-79 | Intelligence Engine Suite (WB-DEV-105–109) | Story | Medium | post-mvp | To Do |

#### E7: Data Capture (WEL-18)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-18 | E7: Data Capture | Epic | High | mvp | To Do |
| WEL-36 | WB2-F034: Mood and energy logging | Story | High | mvp | To Do |
| WEL-40 | WB2-F037: Environmental context ingestion | Story | Medium | post-mvp | To Do |
| WEL-51 | WB2-F017: Medication and access clue capture | Story | Medium | near-term | To Do |
| WEL-80 | Raw Context Vault (WB-DEV-004) | Story | High | mvp | To Do |
| WEL-81 | Ingestion + Processing (WB-DEV-005/006) | Story | High | mvp | To Do |
| WEL-82 | OCR Pipeline (WB-DEV-007) | Story | Medium | mvp | To Do |
| WEL-83 | Evidence & Provenance (WB-DEV-008) | Story | High | mvp | To Do |
| WEL-84 | Event backbone + Temporal (WB-DEV-019/020) | Story | High | mvp | To Do |
| WEL-85 | Mood/Energy logging (WB-DEV-101) | Story | Medium | mvp | To Do |

#### E8: External Intelligence (WEL-19)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-19 | E8: External Intelligence | Epic | Low | post-mvp | To Do |
| WEL-38 | WB2-F035: Myth Buster | Story | Low | post-mvp | To Do |
| WEL-39 | WB2-F036: Research Agent | Story | Low | post-mvp | To Do |
| WEL-48 | WB2-F021: Safe research and explanation mode | Story | Low | near-term | To Do |
| WEL-52 | WB2-F022: Personal experiment guardrails | Story | Low | later | To Do |
| WEL-86 | Research Agent (WB-DEV-110) | Story | Medium | post-mvp | To Do |
| WEL-87 | Myth Buster (WB-DEV-111) | Story | Medium | post-mvp | To Do |

#### E9: Integrations (WEL-20)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-20 | E9: Integrations | Epic | Low | post-mvp | To Do |
| WEL-41 | WB2-F039: Wearable integration | Story | Low | post-mvp | To Do |
| WEL-42 | WB2-F038: Cross-device intelligence | Story | Low | post-mvp | To Do |
| WEL-46 | WB2-F014: Patient-held record import | Story | Low | near-term | To Do |
| WEL-49 | WB2-F041: Medical institution FHIR (deferred) | Story | Low | deferred | To Do |
| WEL-57 | WB2-F025: Care-team comment mode | Story | Low | later | To Do |
| WEL-62 | WB2-F031: Doctor discovery (deferred) | Story | Low | later | To Do |
| WEL-88 | Environmental ingestion (WB-DEV-112) | Story | Low | post-mvp | To Do |
| WEL-89 | Wearable integration (WB-DEV-113/114) | Story | Medium | post-mvp | To Do |
| WEL-90 | FHIR integration (WB-DEV-116) | Story | Low | deferred | To Do |

#### E10: UI Layer (WEL-21)

| Key | Summary | Type | Priority | Phase | Status |
|---|---|---|---|---|---|
| WEL-21 | E10: UI Layer | Epic | Medium | post-mvp | To Do |
| WEL-43 | WB2-F040: Health-adaptive UI | Story | Medium | post-mvp | To Do |
| WEL-63 | WB2-F032: Cross-patient comparison sandbox (deferred) | Story | Low | deferred | To Do |
| WEL-91 | Health-Adaptive UI (WB-DEV-115) | Story | Low | post-mvp | To Do |

### B. Doc files in the repository

| Path | What it covers |
|---|---|
| `VISION.md` | Product vision and scope boundaries (bible file) |
| `AGENTS.md` | Agent instructions, bible file list, commit rules |
| `docs/system-design/system_design.md` | Core system design and operating loop (bible file) |
| `docs/system-design/system_principles.md` | 12 non-negotiable design principles (bible file) |
| `docs/system-design/platform_identity.md` | Platform identity, audience model, identity boundary (bible file) |
| `docs/system-design/architecture.md` | Layer summary, component overview, architectural rules |
| `docs/system-design/core_objects.md` | Health Thread, Health Signal, Pending Item, Visit Packet, Correction Request, Share Grant |
| `docs/system-design/knowledge_graph.md` | Node types, edge types, evidence weighting, auto-linking, visualization modes |
| `docs/system-design/intelligence_engines.md` | 5 engines: pattern, temporal, confounder, missing data, contradiction |
| `docs/system-design/health_thread_state_machine.md` | 10 states, transitions, closure criteria, safety rules |
| `docs/system-design/integrations.md` | Wearable, cross-device, FHIR, environmental context |
| `docs/safety/safety_model.md` | 8 safety layers, non-bypass rule (bible file) |
| `docs/safety/do_not_diagnose_rules.md` | Diagnostic language prohibitions, urgency routing, source rules (bible file) |
| `docs/safety/privacy_and_consent_model.md` | Sharing primitives, forbidden defaults, audit requirements |
| `docs/safety/regulatory_boundary_notes.md` | Lower-risk vs higher-risk framing, required controls |
| `docs/safety/risk_register.csv` | 13 risk items with severity, guardrails, and feature references |
| `docs/feature-backlog/feature_backlog.md` | 42 features (WB2-F001 to WB2-F042) with phase, evidence, risk |
| `docs/feature-backlog/prioritization.md` | Feature priority tiers (high value/low risk → avoid for MVP) |
| `docs/feature-backlog/mvp_plan.md` | 13 MVP features, exclusions, success definition |
| `docs/feature-backlog/features_to_defer_or_avoid.md` | Features to avoid or defer until safety review |
| `docs/feature-backlog/feature_to_evidence_map.csv` | 89 feature-to-evidence mappings |
| `docs/feature-backlog/feature_backlog.csv` | Machine-readable feature backlog |
| `docs/architecture/README.md` | Architecture area index and reading order |
| `docs/architecture/component-map.md` | 13 core (C1–C13) + 13 feature components with dependencies |
| `docs/architecture/tech-stack.md` | Technology choices per concern with rationale |
| `docs/architecture/infra-stack.md` | K8s deployment, IaC, CI/CD, observability, secrets, compliance |
| `docs/architecture/core-stack-relations.md` | Data flow diagrams, dependency direction, load-bearing relationships |
| `docs/architecture/development-backlog.md` | 36 dev work items (WB-DEV-*) mapped to Jira Stories |
| `docs/decisions/README.md` | Decision record lifecycle and conventions |
| `docs/decisions/_template.md` | Decision record template |
| `docs/decisions/*.md` | 11 approved decision records for C1–C7 and platform |
| `docs/analysis/benchmark-expected-results.md` | Forward prediction for 5 benchmark cases |
| `docs/analysis/benchmark-prediction-vs-actual.md` | Prediction vs. measured live cluster verification |

### C. Rule files

| Path | Enforcement | What it governs |
|---|---|---|
| `.cursor/rules/always-commit.mdc` | Always | Git commit discipline |
| `.cursor/rules/audience-guardrails.mdc` | Always (bible) | Audience model, hard prohibitions, language audit |
| `.cursor/rules/doc-governance.mdc` | Always | Bible file protection, doc re-eval protocol |
| `.cursor/rules/infra-constraints.mdc` | On infra files (bible) | K8s-native mandate, Helm requirement |
| `.cursor/rules/infra-live-monitoring.mdc` | On request | Active monitoring for long-running cluster operations |
| `.cursor/rules/jira-autonomy-thresholds.mdc` | Always | Agent autonomy by impact radius |
| `.cursor/rules/jira-epic-priorities.mdc` | On request | Canonical Epic priority/phase assignments |
| `.cursor/rules/jira-post-execution-comments.mdc` | On request | Post-execution Jira comments |
| `.cursor/rules/jira-prioritization-logic.mdc` | On request | Priority assignment framework |
| `.cursor/rules/jira-triage-protocol.mdc` | Always | 8-step triage protocol (DETECT → VERIFY) |
| `.cursor/rules/jira-triage-taxonomy.mdc` | On request | Classification vocabulary (labels, components, impact) |
| `.cursor/rules/jira-trigger-detection.mdc` | Always | What counts as a triage trigger |
| `.cursor/rules/jira-writing-standards.mdc` | On request | Required fields and label formats |
| `.cursor/rules/research-protocol.mdc` | Always | Spike protocol for core component changes |
| `.cursor/rules/systematic-fixing.mdc` | Always | Root-cause fixing protocol |
| `.cursor/rules/wellbe-vision-guardrails.mdc` | Always (bible) | Vision guardrails for agents |

---

## 16. Gaps & Inconsistencies Found

### Features in docs but missing fix version in Jira

Several first-triage Stories (WEL-22 through WEL-61) do not have `fixVersions` set in Jira, while the feature backlog and development backlog docs specify their phase. These should be reconciled to ensure Jira reflects the canonical phase assignment.

### Dual ticket coverage

Many features have both a feature-level Story (WEL-22 to WEL-63, from the first triage) and a development-level Story (WEL-64 to WEL-91, from the development backlog triage). This is intentional — the feature Stories capture the "what" and the development Stories capture the "how" — but the relationship between them is not formalized with issue links in Jira.

### Evidence link non-idempotency

The benchmark verification revealed that C5 evidence links are created non-idempotently, producing orphan links under at-least-once delivery. No Jira ticket specifically tracks this fix — it should be addressed as part of [WEL-83](https://belias.atlassian.net/browse/WEL-83) (Evidence & Provenance Service).

### `full_results_no_final_label` benchmark mode not seeded

Only `blind_pre_diagnosis` mode events are in the cluster. The Missing-Data engine validation target (comparing blind vs. full mode gaps) cannot be exercised until the full mode is also seeded.

### No frontend implementation tickets

While the architecture specifies Next.js + React for the web app and Expo for mobile, there are no Jira tickets specifically for frontend implementation beyond UI-layer feature Stories. The patient dashboard, thread views, and mobile app scaffolding are not tracked as discrete work items.
