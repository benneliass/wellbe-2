# Development Backlog

Structured dev work items for **everything referenced across the design that still needs to be built**. This is the "any doc that refers to something that needs to be developed" deliverable. It is the bridge between the design docs and Jira.

- **Component** → `component-map.md` (`Cn` core, `F-*` feature).
- **Phase** → `mvp` / `post-mvp` / `deferred`, consistent with `../feature-backlog/feature_backlog.md`.
- IDs `WB-DEV-NNN` are local to this doc and map to proposed Jira Stories in the last section.

> **Jira status (2026-05-30, updated):** All 10 Epics are present (WEL-12 through WEL-21). **28 Stories were filed** under the correct Epics during triage session `triage-2026-05-30-002` (WEL-64 through WEL-91). See the filed-story mapping in the last section.

---

## CORE work items

| ID | Component | What to build | Depends on | Phase |
|---|---|---|---|---|
| WB-DEV-001 | C1 Trust & Consent | OIDC integration (ZITADEL) + WebAuthn/passkey login; session/token issuance. | — | mvp |
| WB-DEV-002 | C1 Trust & Consent | Consent-scope + Share-Grant domain model (scoped, time-boxed, revocable) + revocation log. | WB-DEV-001 | mvp |
| WB-DEV-003 | C1 Trust & Consent | Cross-patient opt-in gate (off by default; no data path unless enabled). | WB-DEV-002 | post-mvp |
| WB-DEV-004 | C2 Raw Context Vault | Immutable, append-only RawContextEvent store (Postgres + S3 object-lock) with full provenance fields. | WB-DEV-001 | mvp |
| WB-DEV-005 | C3 Ingestion Layer | Adapter framework + manual/photo/PDF/SMS adapters writing to the Vault. | WB-DEV-004 | mvp |
| WB-DEV-006 | C4 Processing Pipeline | Entity/fact/signal extraction + quality/confidence scoring; emits `fact.extracted`, `health_signal.created`. | WB-DEV-004 | mvp |
| WB-DEV-007 | C4 / OCR | Hybrid OCR pipeline (self-host PaddleOCR-VL/Tesseract → vision-LLM fallback) with hash-based caching and structured (Pydantic) extraction. | WB-DEV-006 | mvp |
| WB-DEV-008 | C5 Evidence & Provenance | Evidence-link service (reasons per `../implementation/api_event_model.md`); enforce "no orphan claims". | WB-DEV-006 | mvp |
| WB-DEV-009 | C6 Knowledge Graph | Graph store (Postgres + Apache AGE) with typed nodes + scored edges per `../system-design/knowledge_graph.md`; PotentialScore computation. | WB-DEV-008 | mvp (minimal) / post-mvp (full) |
| WB-DEV-010 | C6 Knowledge Graph | Auto-linking background worker (co-occurrence/temporal/semantic) with pgvector embeddings. | WB-DEV-009 | post-mvp |
| WB-DEV-011 | C7 Health Thread Engine | Health Thread object + lifecycle state machine (`../system-design/health_thread_state_machine.md`); thread↔subgraph linking. | WB-DEV-008 | mvp |
| WB-DEV-012 | C8 Six Memories | Story / Clinical / Pattern / Decision / Responsibility / Equity memory models around threads. | WB-DEV-011 | mvp (Story/Clinical/Responsibility) / post-mvp (rest) |
| WB-DEV-013 | C9 Continuity & Closure | Pending Item Ledger + durable due-date timers (Temporal) emitting `pending_item.due`. | WB-DEV-011 | mvp |
| WB-DEV-014 | C9 Continuity & Closure | Referral lifecycle tracker + result tracker + post-visit plan checker + repeat-visit view. | WB-DEV-013 | mvp / near-term |
| WB-DEV-015 | C10 Safety Gate | Layered safety service: deterministic rule checks (do-not-diagnose lexicon, panic language, provenance-present) + NeMo Guardrails + Llama Guard; fail-closed; emits `ai_output.blocked`. | WB-DEV-008, WB-DEV-011 | mvp |
| WB-DEV-016 | C11 Correction Service | Correction-request model that adds a new source-linked layer; never mutates raw/derived. | WB-DEV-008 | mvp |
| WB-DEV-017 | C12 Notification & Audit | Append-only audit log of all event types + low-alarm, closure-oriented notifications. | WB-DEV-001 | mvp |
| WB-DEV-018 | C13 API & Contracts | FastAPI REST surface + OpenAPI 3.1; generated TS client; webhook intake endpoints. | WB-DEV-011, WB-DEV-015 | mvp |
| WB-DEV-019 | Platform | Event backbone: transactional outbox + Redis Streams for the event taxonomy in `../implementation/technical_architecture_notes.md`. | WB-DEV-004 | mvp |
| WB-DEV-020 | Platform | Temporal deployment + base workflow library (imports, timers, engine pipeline, agent steps). | WB-DEV-019 | mvp |

---

## FEATURE work items

| ID | Component | What to build | Depends on | Phase |
|---|---|---|---|---|
| WB-DEV-101 | F-MOOD | Mood/energy capture UI + signal model feeding the graph. | WB-DEV-006, WB-DEV-009 | mvp |
| WB-DEV-102 | F-PACKET | Visit Packet generator (concise, source-linked) + scoped share link/export. | WB-DEV-011, WB-DEV-015 | mvp |
| WB-DEV-103 | F-SAFENET | Normal-test safety net (keep unresolved symptoms visible after normal result). | WB-DEV-014, WB-DEV-015 | mvp |
| WB-DEV-104 | F-KG-VIZ | Graph visualization: Cytoscape.js thread view + Sigma.js investigation landscape; click-to-source drill-down. | WB-DEV-009 | post-mvp |
| WB-DEV-105 | F-ENGINES | Pattern Detection engine (`../system-design/intelligence_engines.md`). | WB-DEV-010 | post-mvp |
| WB-DEV-106 | F-ENGINES | Temporal Analysis engine. | WB-DEV-105 | post-mvp |
| WB-DEV-107 | F-ENGINES | Confounder Detection engine (guards spurious patterns). | WB-DEV-105 | post-mvp |
| WB-DEV-108 | F-ENGINES | Missing-Data engine (data-gap objects). | WB-DEV-105 | post-mvp |
| WB-DEV-109 | F-ENGINES | Contradiction Resolution engine (preserve, never auto-resolve). | WB-DEV-008 | post-mvp |
| WB-DEV-110 | F-RESEARCH | Research Agent (LangGraph on Temporal); source-linked, evidence-graded, safety-gated. | WB-DEV-015, WB-DEV-020 | post-mvp |
| WB-DEV-111 | F-MYTH | Myth Buster: evaluate a user's theory against their own data; safety-gated. | WB-DEV-009, WB-DEV-015 | post-mvp |
| WB-DEV-112 | F-ENV | Environmental ingestion adapters (weather/AQ/pollen/UV public, conflict/news opt-in); city-level only. | WB-DEV-005, WB-DEV-009 | post-mvp |
| WB-DEV-113 | F-WEAR | Wearable integration: native HealthKit/Health Connect modules + self-hosted aggregator for device APIs; baseline computation (TimescaleDB). | WB-DEV-005, WB-DEV-006 | post-mvp |
| WB-DEV-114 | F-XDEV | Cross-device intelligence (baseline/drift/asymmetry); no insight before baseline window completes. | WB-DEV-113 | post-mvp |
| WB-DEV-115 | F-AUI | Health-adaptive UI: state-driven design tokens from triage state + baseline deviation; never-alarm rule + a11y. | WB-DEV-015, WB-DEV-018 | post-mvp |
| WB-DEV-116 | F-FHIR | SMART-on-FHIR patient-access import (fhir.resources + Authlib) as a Temporal workflow; user-pull only. | WB-DEV-005, WB-DEV-020 | deferred (compliance review) |

---

## Cross-cutting / enablement work items

| ID | Area | What to build | Phase |
|---|---|---|---|
| WB-DEV-201 | Infra | Profile A deployment (Fly.io/managed Postgres + Redis + Temporal + MinIO) per `infra-stack.md`. | mvp |
| WB-DEV-202 | Infra | OpenTofu IaC with state encryption; GitHub Actions CI (build/test/scan/sign + safety-eval gate). | mvp |
| WB-DEV-203 | Observability | OpenTelemetry instrumentation + Grafana LGTM dashboards; PHI scrubbing at collector. | mvp |
| WB-DEV-204 | Security | OpenBao secrets + KMS envelope encryption + per-user data keys (crypto-shred deletion). | mvp |
| WB-DEV-205 | Safety | Safety evaluation harness (regression suite for do-not-diagnose / panic / provenance), gating CI for C10 + AI features. | mvp |
| WB-DEV-206 | Platform | Profile B migration (Kubernetes + CloudNativePG + Flux + Cilium) when scale/compliance require it. | post-mvp |

---

## Filed Jira Stories — triage-2026-05-30-002

All stories filed on 2026-05-30. All 10 Epics confirmed present before filing. Triage session label: `triage-2026-05-30-002`. Priority mapping used: P1-critical → High, P2-important → Medium, P3-backlog → Low (Jira standard names).

> **Note on P0-blocker in the original table:** Stories cannot carry P0 priority per `jira-prioritization-logic.mdc`. WB-DEV-004 and WB-DEV-011 were proposed as P0-blocker in the draft table but filed as P1-critical (High) with the safety-gate and dependency-chain rationale preserved in their descriptions.

| WB-DEV | Jira Story | Parent Epic | layer | component | phase | priority (tier) |
|---|---|---|---|---|---|---|
| WB-DEV-001/002 | [WEL-72](https://belias.atlassian.net/browse/WEL-72) | WEL-15 E4 Safety & Privacy | layer:infra | component:safety-model | mvp | High (P1-critical) |
| WB-DEV-003 | [WEL-73](https://belias.atlassian.net/browse/WEL-73) | WEL-15 E4 Safety & Privacy | layer:infra | component:safety-model | post-mvp | Medium (P2-important) |
| WB-DEV-004 | [WEL-80](https://belias.atlassian.net/browse/WEL-80) | WEL-18 E7 Data Capture | layer:core | component:data-factory | mvp | High (P1-critical) |
| WB-DEV-005/006 | [WEL-81](https://belias.atlassian.net/browse/WEL-81) | WEL-18 E7 Data Capture | layer:feature-backend | component:data-factory | mvp | High (P1-critical) |
| WB-DEV-007 | [WEL-82](https://belias.atlassian.net/browse/WEL-82) | WEL-18 E7 Data Capture | layer:feature-backend | component:data-factory | mvp | Medium (P2-important) |
| WB-DEV-008 | [WEL-83](https://belias.atlassian.net/browse/WEL-83) | WEL-18 E7 Data Capture | layer:core | component:data-factory | mvp | High (P1-critical) |
| WB-DEV-009/010 | [WEL-77](https://belias.atlassian.net/browse/WEL-77) | WEL-16 E5 Knowledge Graph | layer:feature-backend | component:knowledge-graph | post-mvp | Medium (P2-important) |
| WB-DEV-011 | [WEL-64](https://belias.atlassian.net/browse/WEL-64) | WEL-12 E1 Health Thread Core | layer:core | component:health-thread | mvp | High (P1-critical) |
| WB-DEV-012 | [WEL-70](https://belias.atlassian.net/browse/WEL-70) | WEL-14 E3 Memory Layer | layer:feature-backend | component:story-memory | mvp | High (P1-critical) |
| WB-DEV-013/014 | [WEL-67](https://belias.atlassian.net/browse/WEL-67) | WEL-13 E2 Care Continuity | layer:feature-backend | component:pending-tracker | mvp | High (P1-critical) |
| WB-DEV-015 | [WEL-74](https://belias.atlassian.net/browse/WEL-74) | WEL-15 E4 Safety & Privacy | layer:infra | component:safety-model | mvp | High (P1-critical) |
| WB-DEV-016 | [WEL-71](https://belias.atlassian.net/browse/WEL-71) | WEL-14 E3 Memory Layer | layer:feature-backend | component:story-memory | mvp | High (P1-critical) |
| WB-DEV-017 | [WEL-75](https://belias.atlassian.net/browse/WEL-75) | WEL-15 E4 Safety & Privacy | layer:infra | component:safety-model | mvp | Medium (P2-important) |
| WB-DEV-018 | [WEL-65](https://belias.atlassian.net/browse/WEL-65) | WEL-12 E1 Health Thread Core | layer:feature-api | component:health-thread | mvp | High (P1-critical) |
| WB-DEV-019/020 | [WEL-84](https://belias.atlassian.net/browse/WEL-84) | WEL-18 E7 Data Capture | layer:infra | component:data-factory | mvp | High (P1-critical) |
| WB-DEV-101 | [WEL-85](https://belias.atlassian.net/browse/WEL-85) | WEL-18 E7 Data Capture | layer:feature-frontend | component:mood-logging | mvp | Medium (P2-important) |
| WB-DEV-102 | [WEL-68](https://belias.atlassian.net/browse/WEL-68) | WEL-13 E2 Care Continuity | layer:feature-frontend | component:visit-packet | mvp | High (P1-critical) |
| WB-DEV-103 | [WEL-69](https://belias.atlassian.net/browse/WEL-69) | WEL-13 E2 Care Continuity | layer:feature-backend | component:pending-tracker | mvp | High (P1-critical) |
| WB-DEV-104 | [WEL-78](https://belias.atlassian.net/browse/WEL-78) | WEL-16 E5 Knowledge Graph | layer:feature-frontend | component:knowledge-graph | post-mvp | Medium (P2-important) |
| WB-DEV-105–109 | [WEL-79](https://belias.atlassian.net/browse/WEL-79) | WEL-17 E6 Intelligence Engines | layer:feature-backend | component:intelligence-engines | post-mvp | Medium (P2-important) |
| WB-DEV-110 | [WEL-86](https://belias.atlassian.net/browse/WEL-86) | WEL-19 E8 External Intelligence | layer:feature-backend | component:research-agent | post-mvp | Medium (P2-important) |
| WB-DEV-111 | [WEL-87](https://belias.atlassian.net/browse/WEL-87) | WEL-19 E8 External Intelligence | layer:feature-backend | component:research-agent | post-mvp | Medium (P2-important) |
| WB-DEV-112 | [WEL-88](https://belias.atlassian.net/browse/WEL-88) | WEL-20 E9 Integrations | layer:feature-integration | component:environmental-context | post-mvp | Low (P3-backlog) |
| WB-DEV-113/114 | [WEL-89](https://belias.atlassian.net/browse/WEL-89) | WEL-20 E9 Integrations | layer:feature-integration | component:wearable-integration | post-mvp | Medium (P2-important) |
| WB-DEV-115 | [WEL-91](https://belias.atlassian.net/browse/WEL-91) | WEL-21 E10 UI Layer | layer:feature-frontend | component:health-adaptive-ui | post-mvp | Low (P3-backlog) |
| WB-DEV-116 | [WEL-90](https://belias.atlassian.net/browse/WEL-90) | WEL-20 E9 Integrations | layer:feature-integration | component:medical-integration | deferred | Low (P3-backlog) |
| WB-DEV-201–205 | [WEL-76](https://belias.atlassian.net/browse/WEL-76) | WEL-15 E4 Safety & Privacy | layer:infra | component:safety-model | mvp | High (P1-critical) |
| WB-DEV-206 | [WEL-66](https://belias.atlassian.net/browse/WEL-66) | WEL-12 E1 Health Thread Core | layer:infra | component:data-factory | post-mvp | Low (P3-backlog) |
