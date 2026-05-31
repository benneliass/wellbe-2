# WellBe — Core Components Research Brief (C1–C6)

**Prepared:** 2026-05-31  
**Purpose:** Research brief for the six foundational components of WellBe. Each section contains full project context, component-specific background, and the specific open questions that must be answered before implementation can begin. Answers feed directly into the Decision Records that unblock the implementation Stories.

**Corresponding Jira Spikes:** WEL-93 (C1), WEL-94 (C2), WEL-95 (C3), WEL-96 (C4), WEL-97 (C5), WEL-98 (C6)

---

## Project Overview

WellBe is a **Personal Shared Health Memory OS** — a user-controlled memory layer for unresolved health concerns.

**Core product promise:**
> Help a person carry their health context forward until an issue is resolved, explained, monitored, or safely handed off.

**Operating loop:** Capture → Connect → Clarify → Close → Correct

Everything is organized around **Health Threads** — one thread per unresolved concern. A thread holds: the patient's own words, timeline, symptoms, test results, referrals, pending items, corrections, and a shareable summary.

**Non-negotiable design principles:**
- Personal-first, always — the individual is the data controller
- Every output has provenance — no unsourced claims
- Investigate, never diagnose — the platform asks better questions; it does not give final medical answers
- Correction is safety infrastructure — the user can repair wrong, missing, or stale memory
- No institutional overreach — sharing, clinician access, and integrations are always user-controlled

**Technology stack (already decided):**

| Concern | Choice |
|---|---|
| Backend language | Python 3.13 |
| Backend framework | FastAPI + Pydantic v2 |
| Primary datastore | PostgreSQL 17 |
| Durable workflows | Temporal |
| Lightweight jobs | Dramatiq + Redis |
| Events | Transactional outbox (Postgres) + Redis Streams |
| Graph store | Apache AGE (Cypher on Postgres) + pgvector |
| Auth / Identity | ZITADEL (OIDC + WebAuthn/passkeys) |
| Object storage | S3-compatible with object-lock |
| Deployment (MVP) | Fly.io + managed Postgres |

---

## System Architecture (Layer Summary)

The 13 core components are organized into layers. **C1–C6 are the bottom half** — the foundation everything else rests on:

```
L0  C1  Trust & Consent          ← identity, tokens, consent scopes, share grants
L1  C2  Raw Context Vault        ← immutable, append-only store of every raw input
    C3  Ingestion Layer           ← source-type adapters that write into the Vault
L2  C4  Processing Pipeline      ← entity/fact/signal extraction + confidence scoring
    C5  Evidence & Provenance     ← links every derived fact back to its raw source
    C6  Knowledge Graph           ← typed nodes + evidence-weighted edges
────────────────────────────────
    C7  Health Thread Engine      ← (already decided — Decision Record approved)
    C8  Six Memories
    C9  Continuity & Closure
    C10 Safety Gate
    C11 Correction Service
    C12 Notification & Audit
    C13 API & Contract Layer
```

**Dependency direction:** Lower layers must not depend on upper layers. C1 is the root — it reads from nothing; everything reads from it. C2 is append-only and immutable — nothing rewrites it.

---

---

## C1 — Trust & Consent Service

**Jira Spike:** WEL-93 | **Blocks:** WEL-72 | **Decision Record:** `trust-consent-scope-enforcement-pattern.md`

### What C1 does

C1 owns identity, authentication, and all consent/sharing semantics for the system. It sits at L0 — the root of trust. Every API call goes through C1 token validation; every cross-patient or share operation checks C1 consent scopes.

**Responsibilities:**
- OIDC authentication via ZITADEL (WebAuthn/passkeys)
- Session and token issuance with correct scopes
- Consent Scope model — which data types a user has permitted for which purpose
- Share Grant model — scoped, time-boxed, revocable permissions for a specific recipient
- Revocation log — append-only record of every consent and share grant action
- Cross-patient opt-in gate — **off by default, no data path enabled without explicit per-user activation**

**What depends on C1:** Everything. C2 writes provenance attributed to a user identity from C1. C3 checks ingestion consent at the adapter boundary. C13 enforces scope on every API call. C12 logs events attributed to identities from C1.

**Key constraint:** Consent scopes and Share Grants are WellBe's own domain logic — not the IdP's. ZITADEL handles authentication; WellBe handles consent semantics in its own Postgres tables, enforced at C13 on every request.

### Open questions for research

**Q1 — Consent scope model:**
Should WellBe use flat named scopes (e.g. `thread:read`, `thread:share`, `memory:write`), a hierarchical scope tree (e.g. `thread:*`), or a resource+action ACL model (subject + resource_type + resource_id + action)? What are the trade-offs in terms of expressiveness vs. enforcement complexity at the API boundary?

**Q2 — Share Grant schema:**
What fields should a Share Grant carry — at minimum: `id`, `grantor_id`, `grantee_identifier`, `scope`, `thread_ids` (or all threads?), `purpose`, `expires_at`, `revoked_at`, `created_at`. How should expiry and revocation interact — is a revoked grant immediately invalid or does it use a TTL cache? What is the lifecycle (pending → active → expired/revoked)?

**Q3 — Cross-patient opt-in gate implementation:**
How should the gate be implemented in code — as a boolean flag on the user record, as a separate named consent scope, or as a data-path guard that checks at query time? What prevents a bug from accidentally enabling the cross-patient path for a user who hasn't opted in?

**Q4 — Revocation propagation:**
When a user revokes a Share Grant, how quickly must access be terminated? Synchronous (cache bust on every request) or eventually consistent (revocation log with short TTL cache)? What are the HIPAA/GDPR implications of each approach?

---

---

## C2 — Raw Context Vault

**Jira Spike:** WEL-94 | **Blocks:** WEL-80 | **Decision Record:** `raw-context-vault-immutability-enforcement.md`

### What C2 does

C2 is the immutable, append-only store of every raw input — the "source of truth" layer. Every piece of health context that enters WellBe — symptoms, lab PDFs, referral messages, wearable metrics, manual notes — is written here first, before any processing or interpretation.

**What C2 is not:** C2 is not a processed store. It holds raw data exactly as it arrived, with provenance metadata. Processing, extraction, and linking happen in C4 and C5 after the raw event is safely stored.

**Why immutability matters:** The system principle "every output has provenance" and the safety model's "corrections never overwrite raw data" (C11 adds new layers on top) both depend on C2 being truly append-only. If a raw event can be mutated or deleted, provenance breaks across every downstream component. The user's ability to trust that WellBe remembers what they actually said — not an interpreted version — depends on C2.

**Per-user envelope encryption:** Each user's raw context is encrypted with their own key. Deleting the key (crypto-shred) destroys the PHI without mutating records. This must be compatible with the immutability enforcement.

**Backing technology:** PostgreSQL 17 for structured metadata rows + S3-compatible object storage with object-lock for raw blobs (PDFs, images, audio).

### Open questions for research

**Q1 — Postgres-level immutability enforcement:**
What is the recommended pattern for enforcing append-only semantics in PostgreSQL 17 — a row-level security policy that prohibits UPDATE/DELETE for all roles except a superuser migration role, a trigger that raises an exception on any UPDATE/DELETE attempt, or a combination? What are the failure modes and escape hatches for legitimate data deletion (e.g. GDPR erasure via crypto-shred)?

**Q2 — `RawContextEvent` schema:**
What fields must every raw context event carry at write time? Candidate schema:
```
id, patient_id, source_type, source_id, actor_id,
captured_at, ingested_at, content_hash, blob_ref,
source_metadata (jsonb), ingestor_version
```
Are there missing fields? What is the right type for `source_type` — a string enum, a separate lookup table, or an extensible string?

**Q3 — S3 object-lock configuration:**
What retention mode (GOVERNANCE vs. COMPLIANCE) should be used for raw document blobs? What key naming convention supports per-user crypto-shred (delete envelope key → data unreadable) while preserving the object-lock integrity guarantee? How should versioning interact with immutability?

**Q4 — Deduplication:**
Should hash-based deduplication happen before writing to the Vault (check content_hash, skip if exists) or after (write all, deduplicate on read)? What are the privacy implications of a shared hash namespace across users vs. per-user hash namespaces?

---

---

## C3 — Ingestion Layer

**Jira Spike:** WEL-95 | **Blocks:** WEL-81 | **Decision Record:** `ingestion-adapter-provenance-pattern.md`

### What C3 does

C3 is the only path into C2. Every data capture feature is an adapter on C3. No feature component is permitted to write directly to the Vault — they must write through an adapter that enforces provenance at the boundary.

**Source types at MVP:** manual text entry, photo, PDF, SMS  
**Source types post-MVP:** wearable devices (HealthKit/Health Connect), environmental data, FHIR patient records

**Why the adapter pattern matters:** The system has ~8 source types planned. If each adapter has its own bespoke write path, provenance will be inconsistent and "no orphan claims" will be impossible to enforce. The adapter interface must be stable enough that adding a new source type is purely additive — a new class, no changes to core code.

**Temporal for durable ingestion:** FHIR imports and bulk wearable backfills are long-running operations that must survive crashes. These run as Temporal workflow activities, not simple API calls or Dramatiq jobs.

### Open questions for research

**Q1 — Adapter interface contract:**
What is the minimal Python abstract base class / protocol that every adapter must implement? Candidate interface:
```python
class IngestionAdapter(Protocol):
    source_type: str
    def ingest(self, payload: RawPayload, actor: ActorRef) -> RawContextEvent: ...
    def validate(self, payload: RawPayload) -> ValidationResult: ...
```
What is missing? Should adapters be stateless functions or stateful classes? Should they handle their own deduplication check or delegate to the Vault writer?

**Q2 — Provenance attachment:**
Which provenance fields must an adapter populate before the Vault writer accepts the event? Who is responsible for computing the `content_hash` — the adapter, the Vault writer, or both? What happens if an adapter provides incorrect `source_type`?

**Q3 — Durable ingestion pattern:**
For long-running ingestion (FHIR, bulk wearable backfill), should the adapter be wrapped as a Temporal activity directly, or should there be a Temporal workflow that orchestrates calls to a standard synchronous adapter? What is the retry/timeout policy for durable ingestion activities?

**Q4 — Partial failure handling:**
If an adapter processes a batch (e.g. a multi-page PDF with 20 pages, 18 extracted successfully) and partially fails — should it write the 18 successful events and log the 2 failures, write nothing until all succeed, or write a single partial-ingest event with a `coverage_score`? What does C4 do with a partial-ingest event?

---

---

## C4 — Processing Pipeline

**Jira Spike:** WEL-96 | **Blocks:** WEL-81, WEL-82 | **Decision Record:** `processing-pipeline-extraction-orchestration.md`

### What C4 does

C4 reads raw events from C2 and extracts structured entities, facts, and health signals. It also runs the OCR pipeline for documents and images. Its output feeds directly into C5 (provenance linking) and C6 (graph indexing).

**What C4 extracts:** entities (symptoms, medications, lab values, dates, people), facts (structured claims), health signals (timestamped metric observations), quality/confidence scores per extraction.

**Named output events:** `fact.extracted` and `health_signal.created` — these are consumed by C5 and C6.

**OCR pipeline:** Self-hosted PaddleOCR-VL / Tesseract as tier-1; vision-LLM fallback for degraded scans/handwriting. Hash-based caching — never reprocess a document with the same content hash.

**Why the schema matters:** The `ExtractedFact` and `HealthSignal` schemas are the contract between C4, C5, and C6. All three components must agree on these types before any of them can be built. Changing the schema later requires migrations across all three simultaneously.

### Open questions for research

**Q1 — Orchestration model:**
Should extraction run as: (A) a synchronous step triggered in the same request that ingests the raw event, (B) an async Dramatiq job triggered by `raw_context.received`, or (C) a Temporal workflow activity for all extractions? What is the right choice for MVP given that OCR can take seconds to minutes but simple text extraction is fast?

**Q2 — `ExtractedFact` schema:**
What fields must a fact carry before it is passed to C5? Candidate schema:
```
id, raw_context_event_id, patient_id,
fact_type (enum: symptom | lab_value | medication | date | entity | other),
value (jsonb), unit, normalized_value,
confidence_score (float 0-1), quality_score (float 0-1),
extraction_method (string), extracted_at
```
What is missing? How should facts with multiple possible interpretations be represented?

**Q3 — `HealthSignal` schema:**
How is a `HealthSignal` different from an `ExtractedFact`? A signal is a timestamped metric observation (e.g. heart rate, lab value at a specific time). Candidate schema:
```
id, raw_context_event_id, patient_id,
signal_type, value, unit, observed_at,
source_device (optional), confidence_score
```
Should signals and facts be the same table with a type discriminator, or separate tables?

**Q4 — OCR integration point:**
Should OCR be a Dramatiq job (fire-and-forget, fast path for async processing), a Temporal activity (durable, retryable, with replay history), or a synchronous pre-processing step within the PDF adapter in C3? Who holds the document hash cache — C3, C4, or a shared service?

---

---

## C5 — Evidence & Provenance Service

**Jira Spike:** WEL-97 | **Blocks:** WEL-83 | **Decision Record:** `evidence-provenance-no-orphan-enforcement.md`

### What C5 does

C5 links every derived fact, signal, memory entry, and AI output back to its originating raw context event in C2. It enforces the "no orphan claims" invariant: nothing may exist in the system without a traceable source link.

**Why this is safety-critical:** C10 (Safety Gate) queries C5 provenance when evaluating whether an AI output can be shown to a user. If provenance is missing or incomplete, the gate must block the output. A bug in C5 that allows orphan claims to exist would silently degrade the safety model.

**C11 (Correction Service) writes through C5:** When a user corrects a fact, C11 adds a new source-linked correction layer. It never modifies the original evidence link. C5 must support this append-only correction pattern from the start.

**C5 is also queried by C7 and C13:** When a Health Thread displays its supporting evidence, C7 queries C5 for the evidence links. When C13 renders a thread for the API consumer, it includes source references that trace back through C5 to C2.

### Open questions for research

**Q1 — Evidence link schema:**
What is the right data model for linking a derived fact to its source(s)? Option A: a many-to-many `evidence_links` table (`fact_id`, `raw_context_event_id`, `confidence`, `reason`). Option B: an embedded `source_refs` array (jsonb) on each fact row. Option C: a separate evidence graph in AGE. What are the trade-offs for query performance, append-only compatibility, and join complexity at C7/C10 query time?

**Q2 — No-orphan enforcement:**
Should "no orphan claims" be enforced at: (A) the application layer only — the C5 service raises an error if a fact write has no `evidence_link_ids`, (B) the DB layer — a deferred FK constraint that prevents committing a fact row without at least one evidence link row, or (C) both? What is the failure mode if enforcement is application-only?

**Q3 — Multi-source facts:**
How should a fact derived from multiple raw sources be represented? For example, a symptom confirmed in both a PDF and a manual entry. Should there be multiple rows in `evidence_links` (one per source), a single row with a `source_refs` array, or a "compound provenance" object that groups the sources with a derivation reason? How does this interact with confidence scoring?

**Q4 — Confidence / weight model:**
Should the confidence on an evidence link be: (A) a float derived from C4's `confidence_score` on the extracted fact, (B) an independent score set by C5 based on source type and recency, or (C) both (C4 confidence is input; C5 adjusts based on source metadata)? What inputs should feed the final confidence value that C7 and C10 read?

---

---

## C6 — Knowledge Graph Store

**Jira Spike:** WEL-98 | **Blocks:** WEL-77 | **Decision Record:** `knowledge-graph-node-edge-schema.md`

### What C6 does

C6 is the shared substrate for the intelligence layer. It stores typed nodes and evidence-weighted edges connecting entities across threads, time, and sources. Every connection the system surfaces — "these two concerns may be related", "this symptom co-occurs with that lab value", "this pattern appears across three visits" — is an edge in C6.

**Phase:** C6 is post-MVP. The minimal graph (node/edge storage + basic scoring) ships first; the auto-linking background worker (semantic + temporal + co-occurrence) ships post-MVP. The schema must be decided before the minimal graph is built.

**What depends on C6:** C7 (Health Thread Engine) reads the graph to link thread context. C8 (Six Memories) reads it for pattern memory. The Intelligence Engines (F-ENGINES, post-MVP) read and annotate it. The Knowledge Graph Visualization (F-KG-VIZ) renders it.

**Technology:** Postgres + Apache AGE (Cypher on Postgres) + pgvector for semantic embeddings. Flagged risk: AGE's Cypher-wrapper overhead is significant for 6+ hop traversals — but WellBe's dominant pattern is 1–2 hop, per-user, thread-scoped reads. Hot-path queries may need recursive CTE fallback.

**Hard constraint from the safety model:** `may_explain` is the strongest causal edge permitted. Edges like `causes` or `diagnoses` are prohibited — they would violate "investigate, never diagnose."

### Open questions for research

**Q1 — Node type taxonomy:**
What are the canonical node types? Candidate list: `Symptom`, `LabResult`, `Medication`, `Condition`, `Visit`, `Referral`, `HealthSignal`, `Person`, `BodyRegion`, `TimePoint`. Are these the right types? Are any missing or wrong? What fields are required on each node (at minimum: `id`, `patient_id`, `node_type`, `label`, `created_at`, `evidence_refs`)?

**Q2 — Edge type taxonomy and semantics:**
What are the allowed edge types and what does each mean? Candidate list:
- `may_explain` — one entity could be a contributing factor to another (strongest causal edge allowed)
- `co_occurs_with` — two entities appear together in the same context
- `temporally_precedes` — one entity was observed before another
- `is_same_as` — two nodes refer to the same real-world entity (entity resolution)
- `part_of` — one node is a component of another

Are these the right types? Are any missing? What prevents a developer from accidentally adding a `causes` edge?

**Q3 — PotentialScore:**
How is the PotentialScore (edge weight) computed? What inputs should feed it — co-occurrence frequency, temporal proximity, evidence confidence from C5, user correction signal, source type quality? Should it be computed at write time (stored on the edge) or at query time (computed from raw signals)? Who is responsible for recomputing scores when new evidence arrives?

**Q4 — Per-thread subgraph isolation:**
How should per-thread subgraphs be isolated in Apache AGE? Option A: `thread_id` property on every node and edge, with Cypher `WHERE` filters. Option B: a separate AGE graph per thread (e.g. `graph_<thread_id>`). Option C: label-based partitioning in AGE. What are the query performance, storage, and graph-traversal trade-offs for each approach given the expected 1–2 hop pattern?

**Q5 — Hot path queries:**
Which graph queries are expected to run most frequently and must be identified as hot paths for recursive CTE optimization? Candidate hot paths: (a) fetch all nodes within 2 hops of a given thread, (b) find all edges between a set of symptom nodes, (c) retrieve the highest-PotentialScore edges for a given node. Should these be CTE-only, or should AGE Cypher be the default with CTE as a fallback?

---

---

## How to return research results

For each component (C1–C6), provide your research findings in any format — text, document, links, or verbal summary. For each component, cover:
1. Your recommended approach to each numbered question above
2. Any trade-offs you considered
3. References or sources that support the recommendation

You do not need to cover all six at once. Results can be returned one component at a time or in any grouping. Each set of results will be recorded in the corresponding Decision Record and presented for approval before any implementation begins.
