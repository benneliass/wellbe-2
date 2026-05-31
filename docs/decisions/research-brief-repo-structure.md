# WellBe Repository Structure — Consultation Brief

**Prepared:** 2026-05-31  
**Status:** **APPROVED** — 2026-05-31  
**Purpose:** Full project context for external consultation on how to structure the implementation repository.  
**Current state:** Design-complete, no implementation code exists yet. All architecture is in docs and Jira.

---

## 1. What WellBe Is

WellBe is a **personal health intelligence platform** for individuals — patients and caregivers managing their own or a dependent's health. It is not a clinician tool, not a diagnostic system, and not a hospital platform.

**Core operating loop:** Capture → Connect → Clarify → Close → Correct

The user submits health context (messages, documents, lab results, wearable data). The system extracts facts, connects them into a knowledge graph, surfaces patterns and pending items, and helps the user understand and resolve unresolved health concerns. **The system never diagnoses. It investigates.**

**Primary constraint:** Every AI-generated output must pass a mandatory safety gate (C10) before reaching the user. The safety gate enforces: no diagnosis language, no panic language, every claim has provenance.

---

## 2. Current Repository — What Exists

The repository currently contains **only documentation and design artefacts**. No application code exists. The repo is at `/Users/benel/personal-repos/wellbe-2`.

### 2.1 Annotated directory tree

```
wellbe-2/                          ← root of the design repo (currently docs-only)
│
├── VISION.md                      ← [BIBLE] Product vision and scope. Read-only without approval.
├── AGENTS.md                      ← Agent instructions (bible file list, commit rules)
├── README.md                      ← Project overview
│
├── .cursor/rules/                 ← AI agent rules (Jira triage, research protocol, doc governance)
│   ├── jira-triage-protocol.mdc
│   ├── jira-triage-taxonomy.mdc
│   ├── jira-writing-standards.mdc
│   ├── research-protocol.mdc      ← Governs when architectural Spikes are required
│   ├── audience-guardrails.mdc    ← [BIBLE] Audience model rules
│   └── ...
│
├── docs/
│   ├── architecture/
│   │   ├── component-map.md       ← Canonical list of C1-C13 core + F-* feature components
│   │   ├── tech-stack.md          ← All technology choices with versions and rationale
│   │   ├── infra-stack.md         ← Deployment (Fly.io Profile A → K8s Profile B)
│   │   ├── core-stack-relations.md← Data flow and dependency direction between components
│   │   └── development-backlog.md ← WB-DEV-NNN items → maps to Jira Stories
│   │
│   ├── decisions/                 ← Architectural Decision Records (ADRs)
│   │   ├── README.md              ← DR lifecycle: Open → Research Received → Proposed → Approved
│   │   ├── _template.md
│   │   ├── health-thread-state-machine-enforcement.md   ← C7 APPROVED
│   │   ├── trust-consent-scope-enforcement-pattern.md   ← C1 APPROVED
│   │   ├── raw-context-vault-immutability-enforcement.md ← C2 APPROVED
│   │   ├── ingestion-adapter-provenance-pattern.md      ← C3 APPROVED
│   │   ├── processing-pipeline-extraction-orchestration.md ← C4 APPROVED
│   │   ├── evidence-provenance-no-orphan-enforcement.md ← C5 APPROVED
│   │   ├── knowledge-graph-node-edge-schema.md          ← C6 APPROVED
│   │   ├── research-brief-c1-c6.md      ← Pre-research brief for C1-C6
│   │   ├── research-brief-c6-graph-visualization.md ← C6 viz decisions + component traceability
│   │   └── research-brief-repo-structure.md  ← THIS FILE
│   │
│   ├── system-design/
│   │   ├── system_design.md       ← [BIBLE] Core system design and operating loop
│   │   ├── system_principles.md   ← [BIBLE] 10 non-negotiable design principles
│   │   ├── platform_identity.md   ← [BIBLE] Platform identity and audience model
│   │   ├── core_objects.md        ← Health Thread, Health Signal, Memory, etc.
│   │   ├── health_thread_state_machine.md ← Thread lifecycle states + transitions
│   │   ├── knowledge_graph.md     ← Graph node/edge model (pre-C6 DR)
│   │   ├── intelligence_engines.md ← Pattern, Temporal, Confounder, Missing-data engines
│   │   └── integrations.md        ← Wearable, FHIR, environmental
│   │
│   ├── safety/
│   │   ├── safety_model.md        ← [BIBLE] Safety layers and posture
│   │   ├── do_not_diagnose_rules.md ← [BIBLE] Diagnosis prohibition rules
│   │   ├── privacy_and_consent_model.md
│   │   └── risk_register.csv
│   │
│   ├── feature-backlog/
│   │   ├── feature_backlog.md     ← WB2-F001 through WB2-F042 with evidence and priority
│   │   ├── mvp_plan.md
│   │   └── prioritization.md
│   │
│   ├── implementation/
│   │   ├── implementation_roadmap.md
│   │   ├── api_event_model.md     ← REST resources and event taxonomy
│   │   └── technical_architecture_notes.md
│   │
│   └── workflows/                 ← User-facing workflow descriptions
│       ├── patient_workflow.md
│       ├── pre_visit_workflow.md
│       └── ...
│
└── archive/                       ← Research evidence (read-only, historical)
    └── research/
        ├── clinician_side_diagnostic_pain_points/
        └── global_health_issue_identification/
```

---

## 3. Architecture — 13 Core Components

Every implementation service maps to one or more core components. The component is the unit of ownership, database role, and API boundary.

| # | Component | Layer | One-line purpose | Build phase | Spike status |
|---|---|---|---|---|---|
| C1 | Trust & Consent Service | L0 | Auth (ZITADEL/OIDC), consent tables, Share Grant ACL, revocation | MVP | **APPROVED** (WEL-93 Done) |
| C2 | Raw Context Vault | L1 | Immutable append-only raw event store (Postgres + S3 object-lock) | MVP | **APPROVED** (WEL-94 Done) |
| C3 | Ingestion Layer | L1 | Adapter framework (text/photo/PDF/SMS/FHIR/device) → Vault Writer | MVP | **APPROVED** (WEL-95 Done) |
| C4 | Processing Pipeline | L2 | Entity/fact/signal extraction; OCR; Dramatiq + Temporal workers | MVP | **APPROVED** (WEL-96 Done) |
| C5 | Evidence & Provenance | L2 | Evidence link table; no-orphan-claims enforcement | MVP | **APPROVED** (WEL-97 Done) |
| C6 | Knowledge Graph Store | L2 | Typed nodes + scored edges; Postgres + Apache AGE + pgvector | Post-MVP | **APPROVED** (WEL-98 Done) |
| C7 | Health Thread Engine | L3 | Health Thread object + lifecycle state machine | MVP | **APPROVED** (WEL-92 Done) |
| C8 | Six Memories Store | L4 | Story/Clinical/Pattern/Decision/Responsibility/Equity memories | MVP (partial) / Post-MVP | Not yet researched |
| C9 | Continuity & Closure | L5 | Pending item ledger; referral tracker; Temporal timers (weeks-long) | MVP | Not yet researched |
| C10 | Safety & Governance Gate | L7 | Mandatory gate before any user-facing AI output | MVP | Not yet researched |
| C11 | Correction Service | L0/L4 | User corrections add new source-linked layers; never overwrites raw data | MVP | Not yet researched |
| C12 | Notification & Audit | L7 | Append-only audit trail; closure-oriented notifications | MVP | Not yet researched |
| C13 | API & Contract Layer | L8 | FastAPI REST + OpenAPI 3.1; the single external boundary | MVP | Not yet researched |

**Dependency chain (build order):**
```
C1 → C2 → C3 → C4 → C5 → C7 → C8 → C9
                              ↓
                             C10 (gate before any AI output)
                              ↓
                             C13 (API surface)
C11 depends on: C2, C5, C8
C12 depends on: C1
C6 depends on: C4, C5  (post-MVP minimal graph, post-MVP full)
```

---

## 4. Technology Stack Summary

| Concern | Technology | Version | Notes |
|---|---|---|---|
| Backend language | Python | 3.13 | All server-side services |
| Frontend / mobile | TypeScript | 5.x | Next.js (web) + Expo/React Native (mobile) |
| API framework | FastAPI + Pydantic v2 | 0.115+ | Auto OpenAPI 3.1; async |
| Primary datastore | PostgreSQL | 17 | All structured data; extensions for graph, vector, time-series |
| Graph extension | Apache AGE | 1.6+ | Cypher on Postgres; hot paths use recursive CTEs |
| Vector embeddings | pgvector (+pgvectorscale) | 0.8+ | Semantic similarity in C6 |
| Time-series | TimescaleDB | 2.x | Wearable/metric streams |
| Durable workflows | Temporal | 1.2x | Long-running: FHIR import, pending timers (weeks), LLM agent steps |
| Lightweight workers | Dramatiq + Redis | 1.17+ | Fire-and-forget: extraction, re-index |
| Event bus | Transactional outbox (Postgres) + Redis Streams | — | at-least-once; ordered per thread |
| Identity provider | ZITADEL | latest | OIDC/OAuth2 + WebAuthn/passkey; self-hostable |
| LLM orchestration | LangGraph inside Temporal activities | latest | Research Agent, Myth Buster; HITL support |
| Safety gate | NeMo Guardrails + Llama Guard 4 + deterministic rules | latest | C10; fail-closed always |
| OCR | PaddleOCR-VL / Tesseract → vision-LLM fallback | — | Self-hosted by default; hash-cached |
| Web framework | Next.js 15 + React 19 | — | Patient dashboard |
| Mobile | Expo / React Native | latest | HealthKit + Health Connect |
| UI kit | Tailwind + Radix/shadcn | latest | Accessible, WCAG |
| Graph visualisation (thread) | Cytoscape.js | 3.x | <5k nodes; expandable radial layout |
| Graph visualisation (full) | Sigma.js v3 + graphology | v3 | WebGL; 10k–100k nodes |
| IaC | OpenTofu + Terramate | 1.9+ | State encryption at rest |
| CI/CD | GitHub Actions | — | Safety eval gate on C10-touching PRs |
| Observability | OpenTelemetry + Grafana LGTM | — | PHI scrubbed at collector |
| Secrets | OpenBao + KMS envelope encryption | — | Per-user data keys for crypto-shred |
| Deployment (all envs) | Kubernetes (EKS/GKE/k3s) + CloudNativePG | — | K8s-native from day one; no Fly.io/PaaS |
| Local dev (data services) | Docker Compose | — | Postgres + Redis + MinIO + Temporal + ZITADEL |

---

## 5. Jira Project State

**Project:** WEL (`belias.atlassian.net`)  
**Triage sessions to date:** `triage-2026-05-30-001`, `triage-2026-05-30-002`, `triage-2026-05-31-001`

### 5.1 Epics (10 total)

| Key | Summary | Priority | Phase | Fix Version |
|---|---|---|---|---|
| WEL-12 | E1: Health Thread Core | P0 / Highest | MVP | 10000 |
| WEL-13 | E2: Care Continuity | P1 / High | MVP | 10000 |
| WEL-14 | E3: Memory Layer | P1 / High | MVP | 10000 |
| WEL-15 | E4: Safety and Privacy | P0 / Highest | MVP | 10000 |
| WEL-16 | E5: Knowledge Graph | P2 / Medium | Post-MVP | 10001 |
| WEL-17 | E6: Intelligence Engines | P2 / Medium | Post-MVP | 10001 |
| WEL-18 | E7: Data Capture | P1 / High | MVP | 10000 |
| WEL-19 | E8: External Intelligence | P3 / Low | Post-MVP | 10001 |
| WEL-20 | E9: Integrations | P3 / Low | Post-MVP | 10001 |
| WEL-21 | E10: UI Layer | P2 / Medium | Post-MVP | 10001 |

### 5.2 Stories — MVP core (fully unblocked, ready to implement)

| Key | Summary | Epic | Component | Status | Blocked by |
|---|---|---|---|---|---|
| WEL-72 | OIDC/passkey auth + consent-share domain model (WB-DEV-001/002) | WEL-15 | C1 | To Do | — (Spike Done) |
| WEL-80 | Immutable append-only Raw Context Event store (WB-DEV-004) | WEL-18 | C2 | To Do | — (Spike Done) |
| WEL-81 | Ingestion Layer adapter framework + adapters (WB-DEV-005/006) | WEL-18 | C3+C4 | To Do | — (Spikes Done) |
| WEL-82 | Hybrid OCR pipeline PaddleOCR + vision-LLM fallback (WB-DEV-007) | WEL-18 | C4 | To Do | — (Spike Done) |
| WEL-83 | Evidence-link service, no-orphan-claims enforcement (WB-DEV-008) | WEL-18 | C5 | To Do | — (Spike Done) |
| WEL-64 | Health Thread object + lifecycle state machine (WB-DEV-011) | WEL-12 | C7 | To Do | — (Spike Done) |

### 5.3 Stories — MVP core (not yet unblocked — need research)

| Key | Summary | Epic | Component | Blocked by |
|---|---|---|---|---|
| WEL-65 | Six Memories store (WB-DEV-012) | WEL-12 | C8 | No Spike yet |
| WEL-66 | Pending Item Ledger + Temporal timers (WB-DEV-013) | WEL-13 | C9 | No Spike yet |
| WEL-67 | Referral + result tracker (WB-DEV-014) | WEL-13 | C9 | No Spike yet |
| WEL-68 | Safety Gate — layered service C10 (WB-DEV-015) | WEL-15 | C10 | No Spike yet |
| WEL-69 | Correction Service C11 (WB-DEV-016) | WEL-12 | C11 | No Spike yet |
| WEL-70 | Notification + Audit Service C12 (WB-DEV-017) | WEL-15 | C12 | No Spike yet |
| WEL-71 | API & Contract Layer C13 (WB-DEV-018) | WEL-12 | C13 | No Spike yet |

### 5.4 Stories — MVP platform enablement

| Key | Summary | Component |
|---|---|---|
| WEL-73 | Event backbone: transactional outbox + Redis Streams (WB-DEV-019) | Platform |
| WEL-74 | Temporal deployment + base workflow library (WB-DEV-020) | Platform |
| WEL-75 | Profile A infra (Fly.io + managed Postgres + Redis + MinIO) (WB-DEV-201) | Infra |
| WEL-76 | OpenTofu IaC + GitHub Actions CI (WB-DEV-202) | Infra |

### 5.5 Spikes (all resolved)

| Key | Summary | Status | Unblocks |
|---|---|---|---|
| WEL-92 | [Spike] C7 Health Thread state machine enforcement | Done | WEL-64 |
| WEL-93 | [Spike] C1 consent scope model + Share Grant schema | Done | WEL-72 |
| WEL-94 | [Spike] C2 Raw Context Vault immutability enforcement | Done | WEL-80 |
| WEL-95 | [Spike] C3 Ingestion Layer adapter interface | Done | WEL-81 |
| WEL-96 | [Spike] C4 Processing Pipeline orchestration | Done | WEL-81, WEL-82 |
| WEL-97 | [Spike] C5 Evidence link schema + no-orphan enforcement | Done | WEL-83 |
| WEL-98 | [Spike] C6 Knowledge Graph node/edge types | Done | WEL-77 |

---

## 6. Approved Architectural Decisions

All seven core architectural decisions are Approved with full Decision Records in `docs/decisions/`.

| Component | Key decision | File |
|---|---|---|
| C7 | Domain-owned `transition_thread` command; Postgres defensive enforcement; status column + append-only log; transactional outbox; C9 owns Temporal timers | `health-thread-state-machine-enforcement.md` |
| C1 | ZITADEL coarse OIDC scopes + WellBe Postgres consent/Share Grant tables as source of truth; synchronous revocation; cross-patient gate with `authorized_population_scope()` guard | `trust-consent-scope-enforcement-pattern.md` |
| C2 | Four-layer immutability (app + role + trigger + S3 GOVERNANCE object-lock); lookup table for source_type; per-patient hash namespace; crypto-shred for GDPR | `raw-context-vault-immutability-enforcement.md` |
| C3 | `validate / extract / metadata` adapter protocol; Vault Writer as single write path; Temporal for long-running ingestion; FHIR Provenance model | `ingestion-adapter-provenance-pattern.md` |
| C4 | Async-first (triggered by `raw_context.received`); Dramatiq for lightweight; Temporal for OCR/FHIR/degraded; separate `ExtractedFact` and `HealthSignal` types | `processing-pipeline-extraction-orchestration.md` |
| C5 | Relational `evidence_links` join table; deferred Postgres constraint trigger; four link types (primary/corroborating/contradicting/contextual); C6 owns PotentialScore | `evidence-provenance-no-orphan-enforcement.md` |
| C6 | Relational `kg_nodes`/`kg_edges` for hot paths; Apache AGE for Cypher/exploration; `may_explain` is strongest causal edge; `causes`/`diagnoses` prohibited; PotentialScore materialized on edge | `knowledge-graph-node-edge-schema.md` |
| C6 viz | Expandable radial/mind-map layout; Health Thread root as graph root; 4-layer expansion (root→categories→entities→details); one click = one layer only; evidence drawer on node click | `research-brief-c6-graph-visualization.md` |

---

## 7. Services That Will Exist (Implementation View)

Based on the component map and tech stack, these are the expected runtime services:

| Service | Component(s) | Runtime | Notes |
|---|---|---|---|
| `api` | C13 | FastAPI / Uvicorn | Main REST entry point; single external boundary |
| `auth` (ZITADEL) | C1 (IdP part) | ZITADEL container | External IdP; configured, not built |
| `consent-service` | C1 (domain part) | Python service | Consent tables, Share Grants, revocation |
| `vault-writer` | C2, C3 | Python service | Immutable event store + Vault Writer |
| `ingestion-workers` | C3 | Dramatiq + Temporal activities | Adapter execution |
| `processing-workers` | C4 | Dramatiq + Temporal activities | Entity extraction, OCR pipeline |
| `ocr-service` | C4 | Python (PaddleOCR-VL) | Self-hosted OCR; hash-cached |
| `evidence-service` | C5 | Python service | Evidence links; no-orphan enforcement |
| `graph-service` | C6 | Python service | kg_nodes/kg_edges writes; PotentialScore worker |
| `thread-engine` | C7 | Python service | `transition_thread` command; state machine |
| `memory-service` | C8 | Python service | Six memory types per thread |
| `continuity-engine` | C9 | Python + Temporal workflows | Pending item ledger; referral/result tracker; due-date timers |
| `safety-gate` | C10 | Python service (NeMo Guardrails + Llama Guard) | Mandatory gate; fail-closed |
| `correction-service` | C11 | Python service | Source-linked correction layers |
| `audit-service` | C12 | Python service | Append-only audit trail; notifications |
| `temporal-worker` | C3, C4, C9, C10 | Temporal worker | All durable workflows |
| `web` | Frontend | Next.js | Patient dashboard |
| `mobile` | Frontend | Expo / React Native | iOS + Android |
| PostgreSQL | All | Postgres 17 + extensions | AGE + pgvector + TimescaleDB |
| Redis | C4, C1 | Redis | Dramatiq broker + revocation cache + Streams |
| S3 / MinIO | C2 | Object storage | Raw blob store with object-lock |
| Temporal Server | C9, C4, C3 | Temporal | Durable workflow engine |
| ZITADEL | C1 | ZITADEL | Identity provider |

---

## 8. Open Questions for Repo Structure Consultation

These are the specific decisions the external consultation should answer:

### Q1 — Monorepo vs. multi-repo

Given 10+ backend services (Python), 2 frontend apps (TypeScript), shared DB migrations, shared Pydantic schemas (C4's `ExtractedFact` used by C5 and C6), and shared OpenAPI contract (C13 generates TS client):

- **Monorepo (single repo, e.g. Turborepo or plain directories):** all services share the same git history; schema changes are atomic; easier to enforce component boundaries via directory structure
- **Multi-repo (separate repo per service):** stronger isolation; more independent CI; more overhead for cross-service changes
- **Hybrid:** one repo for backend Python services + one for frontend TypeScript apps

Which model fits best given: 1 team (2 people), ~10 backend Python services, 2 frontend apps, Temporal workflows, shared schema types?

### Q2 — Backend directory structure

Inside the Python backend, how should services be laid out?

**Option A — Service-per-directory (microservice-style):**
```
backend/
  services/
    consent/        ← C1 domain logic
    vault/          ← C2 + C3
    processing/     ← C4
    evidence/       ← C5
    graph/          ← C6
    thread-engine/  ← C7
    safety-gate/    ← C10
  workers/
    ingestion/
    extraction/
    temporal/
  shared/
    schemas/        ← Pydantic models shared across services
    outbox/         ← Outbox writer shared library
    db/             ← Database connection, migrations
```

**Option B — Domain-per-module (modular monolith first, split later):**
```
backend/
  wellbe/
    c1_consent/
    c2_vault/
    c3_ingestion/
    c4_processing/
    c5_evidence/
    c6_graph/
    c7_thread/
    c10_safety/
  workers/
  api/
  shared/
```

**Option C — Layer-based:**
```
backend/
  core/
    data_factory/   ← C2, C3, C4, C5
    thread_engine/  ← C7
    knowledge_graph/← C6
    memories/       ← C8
    continuity/     ← C9
  infra/
    auth/           ← C1
    safety/         ← C10, C11, C12
  api/              ← C13
```

Which structure best supports: independent deployment per service, shared Pydantic schemas, Temporal workflow definitions that span components, and a small team?

### Q3 — Database migrations

All services share a single Postgres database at MVP. Should migrations be:
- A single `migrations/` directory at the repo root (all Alembic migrations together)
- Per-service migrations directories that run in dependency order
- Or a separate `db/` package that every service imports as a dependency

### Q4 — Temporal workflow definitions — where do they live?

Temporal workflows (C3 FHIR/OCR imports, C4 extraction pipeline, C9 pending-item timers, C10 safety agent) span multiple components. Should workflow definitions live:
- In the service that owns the workflow's business logic (e.g. C4's `DocumentOCRWorkflow` lives in the `processing` service)
- In a shared `workflows/` package that all services import
- In a dedicated `temporal-worker/` service that imports activities from other services

### Q5 — Shared Pydantic schemas

`ExtractedFact` (C4) is consumed by C5, C6, C7, and C13. `RawContextEvent` (C2) is produced by C3 and consumed by C4, C5. Should shared schemas live in:
- A `shared/schemas/` package published as an internal Python package
- A `contracts/` directory at the repo root (as Python + generated TypeScript types)
- Within the owning component's package, imported by others

### Q6 — OpenAPI contract and TypeScript client generation

The C13 API must generate a TypeScript client for the web and mobile apps. Should this be:
- Auto-generated in CI on every API change and committed to the frontend repo
- Published as an internal npm package
- Co-located in the monorepo under `packages/api-client/`

### Q7 — Safety Gate isolation

C10 (Safety Gate) is the most sensitive component — it must never fail open. Should it be:
- A completely separate repository with its own CI pipeline and deployment
- A separate directory in the monorepo with strict CI gate (every PR touching it runs the safety evaluation harness)
- Co-located with the API service

### Q8 — Environment configuration

With 10+ services, ZITADEL, Postgres, Redis, S3, Temporal — how should environment config/secrets be structured for:
- Local development (docker-compose? individual service dev servers?)
- CI/CD (GitHub Actions)
- Production (OpenTofu + OpenBao secrets)

---

## 9. Research Results (received 2026-05-31)

The following recommendations were provided by external consultation. Recorded verbatim.

### Summary recommendation

> Use a single monorepo, but structure the backend as separate component-owned Python packages plus thin deployable service apps.
> Monorepo → Python workspace → component packages → service entrypoints → strict import and CI boundaries.

### Q1 — Monorepo: Yes

Single monorepo. Team is small; multi-repo coordination adds overhead before it adds value. Schema, API, safety, and frontend client changes can be committed atomically. C1–C13 remain visible and separately owned in code. Services can be split later without reorganizing domain code.

### Q2 — Top-level structure

```
wellbe-2/
├── docs/
├── archive/
├── .cursor/
├── .github/
│   ├── CODEOWNERS
│   └── workflows/
│       ├── ci.yml
│       ├── backend.yml
│       ├── frontend.yml
│       ├── db-migrations.yml
│       ├── api-contract.yml
│       └── safety-gate.yml          ← required CI for any C10-touching PR
├── apps/
│   ├── web/                         ← Next.js
│   └── mobile/                      ← Expo / React Native
├── packages/
│   ├── api-client/                  ← Generated TypeScript client (co-located)
│   ├── ui/
│   ├── eslint-config/
│   └── tsconfig/
├── backend/
│   ├── pyproject.toml               ← Python workspace root
│   ├── uv.lock
│   ├── apps/                        ← Deployable Python processes
│   └── packages/                   ← Importable Python packages
├── db/
│   └── migrations/                  ← Single central Alembic stream
├── contracts/
│   ├── openapi/                     ← Generated OpenAPI JSON
│   └── events/
├── evals/
│   └── safety/                      ← Safety evaluation harness
├── infra/
│   ├── local/                       ← Docker Compose
│   ├── opentofu/
│   └── terramate/
├── config/
│   └── local/*.example.env
└── scripts/
```

### Q2 — Backend structure (component packages + service apps)

```
backend/
├── apps/
│   ├── api/                         ← C13 FastAPI external boundary
│   ├── vault-writer/                ← ONLY process with C2 INSERT role
│   ├── ingestion-worker/            ← C3 lightweight workers (Dramatiq)
│   ├── processing-worker/           ← C4 lightweight workers (Dramatiq)
│   ├── temporal-worker/             ← Registers all Temporal workflows/activities
│   ├── safety-gate/                 ← C10 isolated runtime service
│   ├── continuity-worker/           ← C9 timers, referrals, results
│   └── notification-worker/         ← C12 notifications + audit sinks
└── packages/
    ├── contracts/                   ← Shared Pydantic DTOs/events ONLY
    ├── platform/                    ← Config, logging, tracing, PHI scrubbers
    ├── db/                          ← DB sessions, roles, Alembic helpers
    ├── events/                      ← Transactional outbox writer + types
    ├── testkit/                     ← Synthetic fixtures only; NEVER real PHI
    ├── c1_consent/
    ├── c2_vault/
    ├── c3_ingestion/
    ├── c4_processing/
    ├── c5_evidence/
    ├── c6_graph/
    ├── c7_thread/
    ├── c8_memories/
    ├── c9_continuity/
    ├── c10_safety/
    ├── c11_correction/
    └── c12_audit/
```

### Import dependency rules (enforced by CI / linting)

- `apps/*` may import `packages/*`
- `packages/*` may NOT import `apps/*`
- Component packages do not import other component internals — share through `contracts`, `events`, DB boundaries, or C13 APIs
- `contracts`, `platform`, `db`, `events` must NEVER import component implementations
- C13 (`api` app) may import component public interfaces (it is the single boundary)
- C10 policy internals are not imported by other components; call through public gate interface only

### Q3 — Database migrations

Single central Alembic migration stream at MVP (all services share one Postgres instance).

```
db/migrations/versions/
  20260601_0001_c1_consent_base.py
  20260601_0002_c2_raw_context_events.py
  20260601_0003_outbox_events.py
  20260601_0004_c3_ingestion_jobs.py
  20260601_0005_c4_extracted_facts.py
  20260601_0006_c5_evidence_links.py
  20260601_0007_c7_health_threads.py
```

Use Postgres schemas for ownership isolation: `consent.*`, `vault.*`, `ingestion.*`, `processing.*`, `evidence.*`, `graph.*`, `thread.*`, `memory.*`, `continuity.*`, `safety.*`, `audit.*`, `outbox.*`

### Q4 — Temporal workflows

Workflow and activity code lives in the **component package** that owns the business logic. A single `temporal-worker` app imports and registers all of them.

```
c3_ingestion/workflows.py     ← FHIRImportWorkflow
c3_ingestion/activities.py
c4_processing/workflows.py    ← DocumentOCRWorkflow, ExtractionWorkflow
c4_processing/activities.py
c9_continuity/workflows.py    ← PendingItemTimerWorkflow
c9_continuity/activities.py
c10_safety/workflows.py       ← SafetyReviewWorkflow (if needed)
c10_safety/activities.py

backend/apps/temporal-worker/registry.py  ← imports and registers all of the above
```

### Q5 — Shared Pydantic schemas

Pure `contracts` package. No component package imports another component's implementation code just to get a DTO.

```
backend/packages/contracts/src/wellbe_contracts/
  primitives/
  c1_consent/
  c2_vault/
  c4_processing/
    extracted_fact.py
    health_signal.py
  c5_evidence/
  c7_thread/
  c10_safety/
  events/
```

### Q6 — OpenAPI / TypeScript client

```
C13 FastAPI app
  → contracts/openapi/wellbe.openapi.json    (committed, generated in CI)
  → packages/api-client/                    (generated TS client, used by web + mobile)
```

### Q7 — C10 Safety Gate isolation

Stay in monorepo. Isolated by: package directory, runtime service, CODEOWNERS, dedicated CI workflow (`safety-gate.yml`), and separate production deployment.

**Fail rules (all absolute — no exceptions):**
- Timeout from C10 → deny
- C10 error → deny
- Missing provenance → deny
- Diagnosis language detected → deny
- Panic language detected → deny

### Q8 — Environment configuration

- **Local:** Docker Compose for data services only (Postgres, Redis, MinIO, Temporal dev server, ZITADEL). Python application services run directly via `uv` or against a local `k3d`/`KinD` cluster.
- **CI:** ephemeral services, synthetic data only (`testkit` package), no production secrets
- **Staging / Production:** Kubernetes-native. CloudNativePG for Postgres HA. Cilium for mTLS + network policy. Flux for GitOps delivery. OpenTofu provisions the cluster; OpenBao stores secrets; each service gets only its own K8s ServiceAccount and Postgres role. No Fly.io or PaaS container platforms. See `docs/architecture/infra-stack.md`.

### MVP deployment shape (6 deployable processes + 2 frontends)

| Deployable | Components served |
|---|---|
| `api` | C13 routes into component public interfaces |
| `vault-writer` | C2/C3 immutable write boundary |
| `worker` | C3/C4 Dramatiq lightweight jobs |
| `temporal-worker` | C3/C4/C9/C10 durable workflows |
| `safety-gate` | C10 isolated runtime |
| `web` | Next.js patient dashboard |
| `mobile` | Expo / React Native app |

### Final principle from research

> Organize the repo by ownership and dependency direction, not by today's deployment topology. Runtime services will change. C1–C13 ownership boundaries, C10 safety, C2 immutability, C13 API contracts, shared migrations, and the shared outbox should remain stable.

---

## 10. Constraints the Repo Structure Must Respect

1. **C10 Safety Gate CI gate:** any PR touching C10 or any AI feature must pass the safety evaluation harness before merge. The repo structure must make it easy to identify C10-touching changes.

2. **C2 immutability enforced at DB role level:** the `vault-writer` service has a distinct Postgres role (INSERT/SELECT only on `raw_context_events`). Other services must not share this role.

3. **C3 as the only ingress into C2:** the only code that can call the `VaultWriter` is in the `ingestion` layer. The directory structure should make it obvious if another service tries to import the Vault Writer directly.

4. **One transactional outbox:** every component that emits events must write to the same `outbox_events` table. This is shared infrastructure — it must not be duplicated per service.

5. **Shared Pydantic schemas cannot be circular:** `ExtractedFact` (C4) is consumed by C5, C6, C7. C7's `HealthThread` object is consumed by C8, C9, C10, C13. The import graph must be a DAG — no circular dependencies.

6. **Temporal activities must be importable by the Temporal worker:** whatever service owns an activity must be importable by the single `temporal-worker` process (or each service owns a worker process for its own activities).

7. **PHI must not appear in logs, test fixtures, or CI artifacts:** the directory structure should isolate test data generation so real PHI (from future production) can never end up in the repo.

---

## 10. Key Numbers for Calibration

| Metric | Value |
|---|---|
| Total Jira Epics | 10 |
| Total Jira Stories (filed) | 28+ |
| Architectural Decision Records (Approved) | 7 (C1–C7) |
| Core components (C1–C13) | 13 |
| Feature components | 13 |
| Backend services (estimated) | 10–14 |
| Shared Postgres DB at MVP | 1 |
| Team size | 1–2 engineers |
| MVP target | Phase: WEL-12, WEL-13, WEL-14, WEL-15, WEL-18 stories |
| Post-MVP | WEL-16, WEL-17, WEL-19, WEL-20, WEL-21 |
| Implementation code exists today | 0 lines |
| Python version | 3.13 |
| TypeScript version | 5.x |
| Postgres version | 17 |

---

## 12. Approval

**Status:** APPROVED  
**Date approved:** 2026-05-31  
**Approved by:** Ben Elias

All 8 structural decisions above are locked and may be used as the basis for scaffolding the implementation repository.
