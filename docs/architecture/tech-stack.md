# Technology Stack

Chosen technologies per concern, with version (verified current as of 2026-05), the requirement it serves, alternatives considered, and the risk flag. Selection bias: **mature, well-supported, privacy-friendly, self-hostable**. Anything bleeding-edge is flagged explicitly.

Component references (`Cn`, `F-*`) map to `component-map.md`.

---

## 1. Languages & runtimes

| Concern | Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|---|
| Backend language | Python | 3.13 | Richest ecosystem for FHIR, LLM orchestration, ML, OCR — the integration-heavy half of the product. | Go, Node/TS | Low |
| Frontend/mobile language | TypeScript | 5.x | Type-safe UI; shared types generated from the OpenAPI contract (C13). | — | Low |

Rationale: the product's hard parts (LLM safety gating, FHIR, document extraction, intelligence engines) all have first-class Python libraries. UI and mobile are TypeScript so device-native modules (HealthKit/Health Connect) and web share one language.

---

## 2. Backend framework

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **FastAPI** (+ Pydantic v2, Uvicorn/Gunicorn) | 0.115+ | Typed REST contract (C13), auto OpenAPI 3.1, async I/O for many parallel external calls (FHIR, wearables, env APIs). | Litestar (~2× faster), Django REST | Low |

Why not Litestar: benchmarks put Litestar ahead on raw throughput, but WellBe is integration- and ecosystem-bound, not throughput-bound at MVP. FastAPI's larger plugin/auth/ORM ecosystem and talent pool outweigh the perf gap. Revisit only if a specific service becomes latency-critical.
Sources: [byteiota Litestar vs FastAPI 2026](https://byteiota.com/litestar-vs-fastapi-python-speed-test-2026-analysis/), [rollbar Python backend frameworks](https://rollbar.com/blog/python-backend-frameworks/).

---

## 3. Async / task workers

Two-tier model, chosen deliberately:

| Tier | Choice | Version | Requirement served | Risk |
|---|---|---|---|---|
| Durable workflows | **Temporal** | 1.2x server / latest SDK | Long-running, must-not-lose-progress, multi-step flows: FHIR import (C3/F-FHIR), wearable backfill (F-WEAR), pending/referral timers that wait **days–weeks** (C9 / Responsibility Memory), the multi-engine pipeline (F-ENGINES), and LLM agent steps that need human-in-the-loop + safety gating. Event-sourced history gives a free audit/replay trail aligned with provenance. | Medium (ops complexity) |
| Lightweight jobs | **Dramatiq** (Redis broker) | 1.17+ | Fire-and-forget jobs: enqueue OCR, thumbnailing, single-fact re-index. Simpler/cleaner than Celery. | Low |

Why Temporal despite ops cost: the Continuity & Closure Engine (C9) is defined by loops that stay open for weeks (pending results, referrals, follow-ups). A plain task queue would require hand-rolled state, polling, and crash recovery; Temporal gives durable timers, automatic retries, and replay that doubles as an audit log — directly serving "closure beats visibility" and "every output has provenance". Flagged as the single highest-ops-cost choice; keep it on managed Temporal Cloud or a small self-hosted cluster, and keep simple jobs on Dramatiq so not everything pays the Temporal tax.
Sources: [Temporal vs Celery 2026](https://markaicode.com/vs/temporal-vs-celery/), [Temporal durable execution](https://dev.to/piotrwachowski/your-ai-agent-just-crashed-at-step-9-of-12-heres-how-to-make-that-not-matter-1ijb).

---

## 4. Datastore, vector, graph, time-series — one Postgres, several extensions

The privacy-first, low-ops choice is to **consolidate on PostgreSQL** and add capability through extensions, avoiding a multi-database "sync tax" and keeping all of a user's data in one ACID boundary.

| Concern | Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|---|
| Primary datastore | **PostgreSQL** | 17 | Relational separation of raw / derived / correction / generated / shared layers (C2, C5, C11) with ACID. | MySQL, managed cloud DBs | Low |
| Vector / embeddings | **pgvector** (+ pgvectorscale for scale) | pgvector 0.8+ | Semantic linking, Research Agent retrieval, similarity edges in C6. Same transaction as graph writes. | Qdrant, Milvus | Low |
| Graph storage | **Apache AGE** (Cypher) on Postgres, recursive-CTE for hot paths | AGE 1.6+ on PG 17 | C6 typed-node/scored-edge store; per-user subgraphs are small and queries are 1–2 hop (thread-scoped). | Neo4j, MemGraph, FalkorDB | **Medium — see note** |
| Time-series | **TimescaleDB** | 2.x | Wearable/metric streams (F-WEAR), continuous aggregates for personal baselines. | InfluxDB, ClickHouse | Low |

**Graph risk note (flagged):** AGE routes Cypher through a `cypher()` wrapper; benchmarks show large overhead vs native graph engines under high write throughput or deep (6+ hop) traversal. WellBe's dominant pattern is 1–2 hop, per-user, thread-scoped reads, so AGE/CTE is the right MVP fit. **Mitigation:** use recursive CTEs for the hottest read paths; treat **Neo4j** as a post-MVP option *only if* full-graph algorithms (PageRank, community detection across the "investigation landscape") become a core requirement. Do not adopt a second graph DB pre-emptively.
Sources: [pgvector + Apache AGE single engine (Microsoft)](https://techcommunity.microsoft.com/blog/adforpostgresql/combining-pgvector-and-apache-age---knowledge-graph--semantic-intelligence-in-a-/4508781), [GraphDB benchmark RCTE vs AGE](https://jaesolshin.com/posts/graph-db-benchmark-rcte-vs-age/), [Neo4j vs Postgres AGE](https://markaicode.com/vs/neo4j-vs-postgres/), [pgvectorscale](https://github.com/timescale/pgvectorscale/).

---

## 5. Events / streaming

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **Transactional outbox (Postgres) + Redis Streams** for internal events; Temporal for orchestration | — | The event taxonomy in `../implementation/technical_architecture_notes.md` (`raw_context.received`, `thread.state_changed`, `ai_output.blocked`, …) with at-least-once delivery and ordering per thread. | Kafka, NATS JetStream | Low |

Why not Kafka at MVP: single-tenant-per-user event volumes are modest; an outbox + Redis Streams keeps ops light and consistency simple. Postgres logical replication (Debezium) can later stream to analytics without a broker rewrite. Flag Kafka/NATS as a scale-out option, not an MVP need.

---

## 6. API layer & contracts

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **REST + OpenAPI 3.1** (FastAPI), JSON; webhooks for inbound device/aggregator callbacks | OAS 3.1 | C13 single contract boundary; resources per `../implementation/api_event_model.md` (`/health-threads`, `/corrections`, `/share-grants`, `/safety-flags`). | gRPC, GraphQL | Low |
| **GraphQL read layer** (Strawberry) for graph/thread exploration | post-MVP | Nested thread/subgraph reads for F-KG-VIZ without N+1 REST round-trips. | — | Low (additive) |

Decision: REST/OpenAPI is the system of record for contracts (generates the TS client). A thin GraphQL read-only layer is additive for the graph explorer post-MVP.

---

## 7. Auth / identity / consent

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **ZITADEL** (self-hostable OIDC/OAuth2 IdP) + WebAuthn/passkeys | latest | C1 identity & token issuance; user-first, self-hostable, no vendor lock. | Keycloak, Ory (Kratos+Hydra) | Low |
| **Consent Scopes / Share Grants / Cross-patient Opt-In** as app-domain logic in Postgres, enforced at C13 | — | Vision guardrails: scoped, revocable, user-controlled sharing; cross-patient is explicit opt-in only. | — | High (correctness-critical) |

Identity is delegated to a mature IdP; **consent and sharing semantics are WellBe's own domain logic** (not the IdP's), stored in Postgres, audited (C12), and enforced at every API call. This keeps the guardrail "the institution is a distribution channel, not a data controller" enforceable in code.
Sources: ZITADEL/Keycloak feature parity per [cloud-native-ref](https://github.com/Smana/cloud-native-ref/blob/main/README.md).

---

## 8. LLM orchestration + safety gating

| Concern | Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|---|
| Agent orchestration | **LangGraph** (stateful graphs, checkpointing, HITL), run **inside Temporal activities** | latest | Multi-step Research Agent (F-RESEARCH) and Myth Buster (F-MYTH) with branching, retries, human-in-the-loop, and durable replay. | OpenAI Agents SDK, CrewAI, custom loop | Medium |
| Model access | **Provider-abstracted**; default to a BAA-covered hosted model OR self-hosted open-weight (Llama / gpt-oss) for PHI-sensitive ops | — | Privacy: PHI-touching calls can stay self-hosted; non-PHI lookups can use hosted models. | Single-vendor lock-in | Medium |
| **Safety & Governance Gate (C10)** | **Layered**: deterministic rule checks (do-not-diagnose lexicon, panic-language, provenance-present) + **NeMo Guardrails** (Colang rails) + a safety classifier (**Llama Guard 4** / gpt-oss-safeguard) | latest | The hard rule: every user-facing AI output passes the gate before render; investigate-never-diagnose; bias controls. See `../safety/`. | Guardrails AI, single-layer filter | High (must not fail open) |

Architectural rule: **C10 is not optional and is provider-independent.** It runs as its own service; if it is unavailable, AI output is blocked (`ai_output.blocked`), never passed through. LangGraph gives auditable, interruptible agent steps; running them as Temporal activities makes the safety checkpoint durable and replayable.
Sources: [LangGraph production 2026](https://www.kalviumlabs.ai/blog/langgraph-vs-langchain-production/), [AI agent frameworks 2026 ranking](https://alicelabs.ai/en/insights/best-ai-agent-frameworks-2026) (NeMo Guardrails / Llama Guard layering).

---

## 9. OCR / document ingestion

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **Hybrid pipeline**: Tier-1 self-hosted OCR (**PaddleOCR-VL** / docTR / Tesseract 5) → Tier-2 vision-LLM fallback for degraded scans/handwriting → structured extraction into Pydantic schemas | — | Patient-held record import (WB2-F014), lab PDFs, photos, SMS. Privacy-first: PHI stays in-house by default. | AWS Textract, Google Document AI, Azure Document Intelligence | Medium |

Default to **self-hosted OCR** to avoid sending PHI to third parties; cloud Document AI (Textract/Google) is an **opt-in accelerator** behind a BAA. Cache by document hash (never by filename) to avoid re-processing. Chunk along document structure, attach `{source_document_id, page, bbox}` to every extracted fact for C5 provenance.
Sources: [LLM vs traditional OCR 2026](https://parsli.co/blog/llm-ocr-vs-traditional-ocr), [pharma OCR benchmarks](https://intuitionlabs.ai/articles/pharma-document-ai-ocr-benchmarks), [best document AI platforms 2026](https://www.llamaindex.ai/insights/best-document-ai-platforms).

---

## 10. FHIR integration (F-FHIR, deferred)

| Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|
| **fhir.resources** (R4 Pydantic v2 models) + **Authlib** for the SMART-on-FHIR patient-access OAuth flow; import runs as a Temporal workflow | FHIR R4 | User-pull import of own records (conditions, meds, labs, immunizations, notes, imaging). User authenticates with the institution directly; scoped token, user-approved resource types only. | smart-on-fhir/client-py (`fhirclient`), fhirpy | **High — compliance** |

Strictly user-initiated (never institution-push), per `../system-design/integrations.md` and the vision guardrails. **Deferred** pending jurisdiction-specific compliance review. WellBe never writes back to EHRs and never receives other patients' data.
Sources: [smart-on-fhir/client-py](https://github.com/smart-on-fhir/client-py), [SMART on FHIR Python client docs](https://docs.smarthealthit.org/client-py/).

---

## 11. Wearable / health-data integration (F-WEAR / F-XDEV)

| Path | Choice | Requirement served | Risk |
|---|---|---|---|
| On-device (iOS/Android) | Native **Apple HealthKit** + **Android Health Connect** via the mobile app (these require on-device code, not server OAuth). | First-party device data with user consent. | Low |
| Server-side device APIs (Fitbit, Garmin, Oura, Whoop, Dexcom CGM) | **Privacy-first default: self-hosted aggregator (Open Wearables)**; commercial aggregator (**Terra** / **ROOK**) flagged as a faster alternative. | Avoid maintaining N vendor integrations; normalize into `RawContextEvent`. | Medium |

Tradeoff (flagged): commercial aggregators (Terra/ROOK) are the fastest path and offer health-grade normalization, **but user PHI flows through the vendor's servers** — a data-sovereignty conflict with the personal-first vision. Default to the **self-hosted** aggregator to keep PHI in-house and avoid per-active-user SaaS fees; use a commercial aggregator only with an explicit data-processing agreement. **Location stored at city-level only**; raw biometric streams never shared with third parties.
Sources: [Wearables interoperability stack](https://healthapiguy.substack.com/p/the-wearables-interoperability-stack), [Open Wearables (self-host)](https://www.themomentum.ai/blog/open-wearables-faq-how-to-integrate-multiple-wearables-without-vendor-lock-in), [ROOK API overview](https://www.tryrook.io/api-overview).

---

## 12. Frontend + graph visualization + health-adaptive UI

| Concern | Choice | Version | Requirement served | Alternatives | Risk |
|---|---|---|---|---|---|
| Web framework | **Next.js (App Router) + React** | Next 15 / React 19 | Patient dashboard, thread views, visit packet, share. TanStack Query for data. | Remix, SvelteKit | Low |
| Mobile | **Expo / React Native** | latest | Native HealthKit/Health Connect modules; shared TS types. | Native Swift/Kotlin | Medium |
| UI kit / a11y | **Tailwind + Radix/shadcn** | latest | Accessible, WCAG-friendly components. | MUI, Chakra | Low |
| Graph viz — thread scope | **Cytoscape.js** | 3.x | Thread-scoped view (<5k nodes): rich layouts, centrality, styling, click-to-source. | vis-network | Low |
| Graph viz — investigation landscape | **Sigma.js v3 + graphology** | v3 | Full-user "investigation landscape" (10k–100k nodes) via WebGL. | Cosmograph, react-force-graph | Low |
| Health-Adaptive UI (F-AUI) | **State-driven design tokens**: triage state (from C10) + baseline deviation (C7) → token set (color/density/prominence), with `prefers-reduced-motion` and a strict **never-alarm** rule | — | Ambient signal of health state without panic language; respects safety model. | Ad-hoc theming | Low |

Two graph libraries by design: Cytoscape.js for the small, analysis-rich default thread view; Sigma.js for the large-graph exploration mode. Health-Adaptive UI is implemented as a theming/state system (no bleeding-edge tech), gated so it can never produce alarming presentation — consistent with `../safety/safety_model.md`.
Sources: [Cytoscape vs vis-network vs Sigma 2026](https://www.pkgpulse.com/guides/cytoscape-vs-vis-network-vs-sigma-graph-visualization-2026), [react-force-graph](https://vasturiano.github.io/react-force-graph/).

---

## Bleeding-edge / risk register (summary)

| Item | Why flagged | Mitigation |
|---|---|---|
| Apache AGE for graph | Cypher-wrapper overhead at scale/deep traversal | CTE for hot paths; Neo4j only if full-graph algorithms become core |
| Temporal | Highest ops complexity in the stack | Managed Temporal Cloud or small cluster; keep simple jobs on Dramatiq |
| Hosted LLM / cloud OCR on PHI | Third-party PHI exposure | Self-host by default; BAA + opt-in for cloud; C10 never fails open |
| Commercial wearable aggregator | PHI flows through vendor | Self-hosted Open Wearables default; DPA required for commercial |
| FHIR patient-access | Jurisdiction compliance | Deferred until compliance review (WB2-F041) |

Deployment, observability, secrets, and CI/CD are in `infra-stack.md`. Core component relationships are in `core-stack-relations.md`.
