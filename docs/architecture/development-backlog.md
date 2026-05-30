# Development Backlog

Structured dev work items for **everything referenced across the design that still needs to be built**. This is the "any doc that refers to something that needs to be developed" deliverable. It is the bridge between the design docs and Jira.

- **Component** → `component-map.md` (`Cn` core, `F-*` feature).
- **Phase** → `mvp` / `post-mvp` / `deferred`, consistent with `../feature-backlog/feature_backlog.md`.
- IDs `WB-DEV-NNN` are local to this doc and map to proposed Jira Stories in the last section.

> **Jira status (2026-05-30):** At the time of writing, the WEL project Epics were **mid-bootstrap** by a concurrent agent (only `WEL-12` E1 Health Thread Core, `WEL-13` E2 Care Continuity, `WEL-14` E3 Memory Layer, `WEL-15` E4 Safety and Privacy existed; 10 were planned). Per `../../.cursor/rules/jira-autonomy-thresholds.mdc`, Stories must not be created as orphans before their parent Epics exist. **No Jira Stories were created.** They are recorded below and should be filed under the WEL Epics once the full Epic set is present, using triage session label `triage-2026-05-30-002`.

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

## Proposed Jira Stories (to file under WEL Epics once present)

These were **not created** (Epics mid-bootstrap — see note at top). When the full Epic set exists, file each as a Story under the matching Epic with all required metadata per `../../.cursor/rules/jira-writing-standards.mdc`, session label `triage-2026-05-30-002`, and a description referencing the relevant `docs/` section.

> Component labels marked `(new)` assume the taxonomy additions the concurrent agent is making to `../../.cursor/rules/jira-triage-taxonomy.mdc` (e.g. `component:knowledge-graph`, `component:intelligence-engines`, `component:integrations`, `component:adaptive-ui`). If a new label is not yet present at filing time, use the closest existing label and flag for re-eval.

| Proposed Story (from WB-DEV) | Likely Epic | layer | component | impact | phase | priority |
|---|---|---|---|---|---|---|
| WB-DEV-001/002 Auth + consent/share model | E4 Safety and Privacy (`WEL-15`) | layer:infra | component:safety-model | impact:cross-cutting | mvp | P1-critical |
| WB-DEV-004 Raw Context Vault | E? Data Factory | layer:core | component:data-factory | impact:cross-cutting | mvp | P0-blocker |
| WB-DEV-005/006 Ingestion + Processing | E? Data Factory | layer:feature-backend | component:data-factory | impact:cross-cutting | mvp | P1-critical |
| WB-DEV-007 Hybrid OCR pipeline | E? Data Factory | layer:feature-backend | component:data-factory | impact:component-local | mvp | P2-important |
| WB-DEV-008 Evidence & Provenance | E? Data Factory | layer:core | component:data-factory | impact:cross-cutting | mvp | P1-critical |
| WB-DEV-009/010 Knowledge Graph + auto-link | E? Knowledge Graph | layer:feature-backend | component:knowledge-graph (new) | impact:cross-cutting | post-mvp | P2-important |
| WB-DEV-011 Health Thread Engine + state machine | E1 Health Thread Core (`WEL-12`) | layer:core | component:health-thread | impact:cross-cutting | mvp | P0-blocker |
| WB-DEV-012 Six Memories | E3 Memory Layer (`WEL-14`) | layer:feature-backend | component:story-memory | impact:component-local | mvp/post-mvp | P1-critical |
| WB-DEV-013/014 Continuity & Closure | E2 Care Continuity (`WEL-13`) | layer:feature-backend | component:pending-tracker | impact:cross-cutting | mvp | P1-critical |
| WB-DEV-015 Safety & Governance Gate | E4 Safety and Privacy (`WEL-15`) | layer:infra | component:safety-model | impact:cross-cutting | mvp | P0-blocker |
| WB-DEV-016 Correction Service | E3 Memory Layer (`WEL-14`) | layer:feature-backend | component:story-memory | impact:component-local | mvp | P1-critical |
| WB-DEV-017 Notification & Audit | E4 Safety and Privacy (`WEL-15`) | layer:infra | component:safety-model | impact:component-local | mvp | P2-important |
| WB-DEV-018 API & Contract layer | E1 Health Thread Core (`WEL-12`) | layer:feature-api | component:health-thread | impact:cross-cutting | mvp | P1-critical |
| WB-DEV-019/020 Event backbone + Temporal | E? Data Factory / Platform | layer:infra | component:data-factory | impact:cross-cutting | mvp | P1-critical |
| WB-DEV-101 Mood/energy logging | E? Data Factory | layer:feature-frontend | component:data-factory | impact:self-contained | mvp | P2-important |
| WB-DEV-102 Visit Packet + scoped share | E2 Care Continuity (`WEL-13`) | layer:feature-frontend | component:visit-packet | impact:component-local | mvp | P1-critical |
| WB-DEV-103 Normal-test safety net | E2 Care Continuity (`WEL-13`) | layer:feature-backend | component:pending-tracker | impact:component-local | mvp | P1-critical |
| WB-DEV-104 Graph visualization | E? Knowledge Graph | layer:feature-frontend | component:knowledge-graph (new) | impact:component-local | post-mvp | P2-important |
| WB-DEV-105–109 Intelligence engines | E? Intelligence Engines | layer:feature-backend | component:intelligence-engines (new) | impact:cross-cutting | post-mvp | P2-important |
| WB-DEV-110 Research Agent | E? Investigation | layer:feature-backend | component:intelligence-engines (new) | impact:component-local | post-mvp | P2-important |
| WB-DEV-111 Myth Buster | E? Investigation | layer:feature-backend | component:intelligence-engines (new) | impact:component-local | post-mvp | P2-important |
| WB-DEV-112 Environmental ingestion | E? Integrations | layer:feature-integration | component:integrations (new) | impact:component-local | post-mvp | P3-backlog |
| WB-DEV-113/114 Wearable + cross-device | E? Integrations | layer:feature-integration | component:integrations (new) | impact:component-local | post-mvp | P2-important |
| WB-DEV-115 Health-adaptive UI | E? Frontend | layer:feature-frontend | component:adaptive-ui (new) | impact:self-contained | post-mvp | P3-backlog |
| WB-DEV-116 FHIR patient-access | E? Integrations | layer:feature-integration | component:integrations (new) | impact:cross-cutting | deferred | P3-backlog |
| WB-DEV-201–205 Infra/observability/security/safety-eval | E4 Safety and Privacy / Platform | layer:infra | component:safety-model | impact:cross-cutting | mvp | P1-critical |

`E?` = Epic expected in the bootstrap set but not yet observed (Data Factory, Knowledge Graph, Intelligence Engines, Integrations, Frontend/UI, Investigation/Research). Confirm exact Epic keys before filing.
