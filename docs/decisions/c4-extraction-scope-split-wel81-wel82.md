# Decision: C4 Processing Pipeline scope split between WEL-81 and WEL-82

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** (fill on approval)  
**Approved by:** User  
**Jira Spike:** n/a — this is a scope/structure decision, not an external research question. All architecture is already resolved by WEL-96 / `processing-pipeline-extraction-orchestration.md`.  
**Blocks:** WEL-81, WEL-82 — implementation cannot start until scope boundaries are confirmed.

---

## Question

Should WEL-81 cover **both** C3 ingestion adapter framework **and** C4 entity/fact/signal extraction (current Jira title), making WEL-82 strictly the OCR pipeline (current Jira title) — or should WEL-81 be narrowed to C3 adapters only, with WEL-82 covering the full C4 extraction pipeline including confidence scoring?

In concrete terms: where does C3's responsibility end and C4's begin in the story boundary, and which Jira story owns the `ExtractedFact` / `HealthSignal` schemas and the Dramatiq `extract_facts_worker`?

---

## Context

### System position

```
L0  C1  Trust & Consent          ✅ implemented
L1  C2  Raw Context Vault        ✅ implemented
    C3  Ingestion Layer           ✅ implemented
─────────────────────────────────────────────────── ← implementation frontier
L2  C4  Processing Pipeline      ⬜ WEL-81 / WEL-82
    C5  Evidence & Provenance     ⬜ WEL-83
    C6  Knowledge Graph           ⬜ WEL-77 (post-mvp)
─────────────────────────────────────────────────── ← everything below depends on C4+C5
    C7  Health Thread Engine      ⬜ WEL-64
    C8  Six Memories              ⬜ WEL-70
    C9  Continuity & Closure      ⬜ WEL-67
    C10 Safety Gate               ⬜ WEL-74
    C11 Correction Service        ⬜ WEL-71
    C12 Notification & Audit      ⬜ WEL-75
    C13 API & Contract Layer      ⬜ WEL-65
```

C4 sits at the narrowest bottleneck in the build sequence. **Nothing in C5, C6, C7, C8, C9, C10, or C13 can be implemented until C4's `ExtractedFact` and `HealthSignal` types are live in `contracts/c4_processing/`.** The scope boundary between WEL-81 and WEL-82 determines which story delivers those types and when.

### What is already architecturally decided (WEL-96 / `processing-pipeline-extraction-orchestration.md` — Approved)

1. **C3 boundary:** C3 adapters produce `AdapterInput → NormalizedPayload + AdapterProvenance` and call the Vault Writer. C3 is done when the `RawContextEvent` is safely written to C2 and `raw_context.received` is emitted on the outbox.

2. **C4 trigger:** C4 consumes `raw_context.received` from the outbox. It does not call C3 or C2 directly.

3. **C4 orchestration — two-tier:**

   | Work type | Orchestration |
   |---|---|
   | Structured text, simple JSON, short records | Dramatiq worker (`extract_facts_worker`) |
   | Long/complex documents, degraded quality | Temporal `DocumentExtractionWorkflow` |
   | OCR on photo/PDF | Temporal `DocumentOCRWorkflow` |
   | FHIR/bulk imports | Temporal `FHIRProcessingWorkflow` |
   | Vision model fallback (OCR failed) | Temporal `VisionExtractionWorkflow` |

4. **C4 output schemas (fully specified, approved):**

   ```
   ExtractedFact:
     id, patient_id, raw_context_event_id (FK → vault.raw_context_events),
     fact_type (symptom | finding | medication | lab_result | allergy |
                procedure | dx_mention | ...),
     entity_label, normalized_key, code_system, code,
     text_span_start, text_span_end, source_text_excerpt_hash,
     extraction_confidence (float 0–1),
     extraction_model, model_version, pipeline_version,
     quality_flag (clean | low_confidence | requires_review | partial),
     quality_metadata (jsonb),
     is_negated, is_historical, is_hypothetical,
     subject (patient | family_member | other),
     captured_at, extracted_at, correlation_id, trace_id,
     schema_version, created_at

   HealthSignal:
     id, patient_id, raw_context_event_ids (array FK),
     signal_type (pain_level | mood_score | fatigue | sleep_quality | ...),
     signal_value, signal_unit, signal_direction,
     aggregation_method, observation_window,
     extraction_confidence, extraction_model, model_version, pipeline_version,
     quality_flag, quality_metadata (jsonb),
     captured_at_start, captured_at_end, extracted_at,
     correlation_id, trace_id, schema_version, created_at
   ```

5. **C4 outbox events:** `fact.extracted`, `health_signal.created`, `document.ocr_completed`, `document.ocr_failed`

6. **OCR pipeline path (approved):**
   ```
   raw_context.received (mime_type = image/*, application/pdf)
     → C4 dispatcher → DocumentOCRWorkflow
     → activity: PaddleOCR primary, vision-LLM fallback
     → success: document.ocr_completed → ExtractedFacts created
     → failure: document.ocr_failed, quality_flag = requires_review
   ```

### What is currently in Jira

| Key | Current Jira title | WB-DEV ref | Phase | Priority |
|---|---|---|---|---|
| WEL-81 | Build ingestion adapter framework and entity/fact/signal extraction pipeline | WB-DEV-005/006 | mvp | P1-critical (High) |
| WEL-82 | Implement hybrid OCR pipeline with PaddleOCR/Tesseract and vision-LLM fallback | WB-DEV-007 | mvp | P2-important (Medium) |

### The discrepancy

The approved C4 decision record (`processing-pipeline-extraction-orchestration.md`) lists:

> **Blocks:** WEL-81 — Build pluggable Ingestion Layer with unified adapter protocol  
> **Also blocks:** WEL-82 — Build Processing Pipeline (entity/fact extraction, confidence scoring, quality metadata)

WEL-82's title in that record ("Build Processing Pipeline — entity/fact extraction, confidence scoring, quality metadata") does not match its current Jira title ("Implement hybrid OCR pipeline"). One of these is wrong:

- **Either** WEL-82 was originally intended to be the full C4 extraction story and was later narrowed to OCR only (with extraction bundled into WEL-81), and the decision record was never updated.
- **Or** the decision record wrote the wrong title and WEL-82 was always meant to be OCR only.

WB-DEV-005 = ingestion adapters, WB-DEV-006 = entity extraction pipeline, WB-DEV-007 = OCR pipeline.  
WEL-81 references WB-DEV-005 **and** 006. WEL-82 references WB-DEV-007.

This means the **current Jira structure already has WEL-81 covering both C3 (WB-DEV-005) and C4 extraction (WB-DEV-006)**, and WEL-82 as OCR only (WB-DEV-007). The decision record title for WEL-82 appears to be a documentation error.

---

## The decision to make

Choose one of the two options below.

---

### Option A — Keep current Jira structure (WEL-81 = C3 adapters + C4 extraction, WEL-82 = OCR only)

**What WEL-81 delivers:**
- `BaseAdapter` protocol already live in C3 (✅ done) — WEL-81 adds concrete adapters for any missing source types and then immediately proceeds to the C4 extraction pipeline
- Dramatiq `extract_facts_worker` subscribing to `raw_context.received`
- C4 dispatcher routing by `source_type` / `mime_type`
- `ExtractedFact` and `HealthSignal` schemas in `contracts/c4_processing/__init__.py`
- `ExtractedFact` and `HealthSignal` Postgres tables (schema `processing`)
- `fact.extracted` and `health_signal.created` outbox events
- Unit tests for extraction, confidence scoring, quality flags

**What WEL-82 delivers:**
- Temporal `DocumentOCRWorkflow` (PaddleOCR primary, Tesseract fallback, vision-LLM final fallback)
- `document.ocr_completed` / `document.ocr_failed` outbox events
- Hash-based document caching (never reprocess same content_hash)
- `quality_flag = requires_review` path for failed OCR

**Dependency chain if Option A:**
```
WEL-81 done → contracts/c4_processing populated → WEL-83 (C5) can start in parallel with WEL-82
WEL-82 is not on the critical path for WEL-83 or WEL-83→WEL-64 (C7)
```

**Pros:**
- WEL-81 is already written and linked — no Jira changes except title cleanup on the decision record
- C5 (WEL-83) unblocks faster — only WEL-81 needs to finish before C5 can start
- OCR is correctly isolated as a separable, testable unit
- Matches how WB-DEV numbers were assigned

**Cons:**
- WEL-81 carries a large scope: C3 adapter work + the entire C4 extraction pipeline in one story
- If WEL-81 stalls, both the adapter work and extraction are blocked together
- `ExtractedFact` schema (which C5, C6, C7 all depend on) is not independently shippable from the adapter work

---

### Option B — Split: WEL-81 = C3 adapters only, WEL-82 = full C4 pipeline (extraction + OCR)

**What WEL-81 delivers (narrowed):**
- Only: complete the C3 adapter set for all MVP source types (if any adapters beyond `ManualTextAdapter` + `DocumentAdapter` are missing)
- No extraction logic — C3 ends when `raw_context.received` is emitted

**What WEL-82 delivers (broadened):**
- Dramatiq `extract_facts_worker`
- C4 dispatcher
- `ExtractedFact` + `HealthSignal` schemas and tables
- `fact.extracted` + `health_signal.created` outbox events
- Temporal `DocumentOCRWorkflow` (PaddleOCR + fallbacks)
- Hash-based document cache
- All C4 outbox events

**Dependency chain if Option B:**
```
WEL-81 done (adapters) → WEL-82 (full C4) must finish before WEL-83 (C5) can start
WEL-82 is now on the critical path for C5 → C7 → everything
```

**Pros:**
- Clean architectural boundary: one story per component (C3 = WEL-81, C4 = WEL-82)
- `ExtractedFact` schema ownership is unambiguous — it belongs entirely to WEL-82
- Smaller, better-scoped WEL-81 (C3 adapters only)

**Cons:**
- Requires retitling WEL-82 and updating the decision record — Jira changes needed
- C3 adapters at MVP are mostly already implemented (`ManualTextAdapter`, `DocumentAdapter` are live). WEL-81 may become very thin.
- WEL-82 becomes very large: extraction engine + OCR + Temporal workflows + schemas in one story
- WEL-82 is now a blocker for WEL-83 (C5), extending the critical path

---

## Current C3 adapter status (relevant to both options)

From the implemented code (`backend/packages/c3_ingestion/`):

| Adapter | Implemented |
|---|---|
| `ManualTextAdapter` | ✅ live |
| `DocumentAdapter` | ✅ live |
| `SMSAdapter` | ❓ not seen in file list |
| `DeviceAdapter` (wearable — post-mvp) | post-mvp scope, WEL-89 |
| `FHIRAdapter` (deferred) | deferred scope, WEL-90 |
| `EnvironmentalAdapter` (post-mvp) | post-mvp scope, WEL-88 |

At MVP, only `manual_text`, `photo`, `pdf`, `sms` are in scope. `ManualTextAdapter` and `DocumentAdapter` are live. An `SMSAdapter` may or may not be needed — SMS ingestion is MVP scope (`SourceTypeCode.SMS` exists in contracts).

If `ManualTextAdapter` and `DocumentAdapter` already cover the MVP adapter surface, Option A's WEL-81 is almost entirely C4 extraction work and the "adapter framework" part is complete.

---

## C4 → C5 → C6: Component responsibilities and relationship

This section exists to validate that the three components are coherent with each other — not just individually. Read it before starting any of WEL-81, WEL-83, or WEL-77.

---

### What each component is responsible for (and what it is NOT)

| | C4 — Processing Pipeline | C5 — Evidence & Provenance | C6 — Knowledge Graph |
|---|---|---|---|
| **Core job** | Transform raw events into typed, structured facts and signals | Enforce that every derived object has a traceable raw source | Maintain a typed, evidence-weighted graph of health entities and relationships |
| **Input** | `RawContextEvent` (via `raw_context.received` event from C2 outbox) | `ExtractedFact`, `HealthSignal` (via `fact.extracted`, `health_signal.created` events from C4) | `evidence.linked` events from C5 + `fact.extracted`, `health_signal.created` from C4 |
| **Output** | `ExtractedFact` rows, `HealthSignal` rows, outbox events | `EvidenceLink` rows, `evidence.linked` events | `kg_nodes`, `kg_edges`, `potential_score` on edges, outbox events |
| **What it does NOT do** | Does not write to C2. Does not call C3. Does not enforce provenance. | Does not extract facts. Does not score. Does not own PotentialScore computation. | Does not extract facts. Does not enforce provenance. Does not diagnose or assert causation. |
| **Safety constraint** | Must emit `quality_flag` on every output — never silently suppress a fact | Must enforce "no orphan claims" — a derived object that has no traceable raw source is rejected, not silently stored | Must prohibit causal/diagnostic edge types (`causes`, `diagnoses`, `rules_out`, `proves`) — `may_explain` is the ceiling |
| **Jira stories** | WEL-81 (extraction), WEL-82 (OCR) | WEL-83 | WEL-77 (post-mvp) |
| **Decision record** | `processing-pipeline-extraction-orchestration.md` (WEL-96, Approved) | `evidence-provenance-no-orphan-enforcement.md` (WEL-97, Approved) | `knowledge-graph-node-edge-schema.md` (WEL-98, Approved) |

---

### Data contracts at each boundary

#### Boundary 1: C4 → C5 (via event)

C4 emits `fact.extracted` on the outbox. C5 consumes it. This is the only path through which C4 output enters C5.

```
C4 fact.extracted event payload (minimum required for C5):
  fact_id           → source_id in EvidenceLink
  patient_id
  raw_context_event_id   → raw_context_event_id in EvidenceLink (the FK C5 validates)
  fact_type
  extraction_confidence  → used as confidence basis in EvidenceLink
  quality_flag           → C5 stores it on the EvidenceLink; quality_flag = requires_review
                           does not block evidence linking but is flagged
  correlation_id, trace_id

C4 health_signal.created event payload (minimum required for C5):
  signal_id
  patient_id
  raw_context_event_ids  → one EvidenceLink row per event ID in this array
  signal_type
  extraction_confidence
  quality_flag
  correlation_id, trace_id
```

**C5's action on receiving these events:**
1. Validate all `raw_context_event_id`(s) exist in C2's `raw_context_events` table
2. If any are missing → reject with `provenance.orphan_rejected` event, do not write the fact
3. If valid → write `EvidenceLink` row(s) atomically with the fact/signal in the same transaction
4. Emit `evidence.linked` event for C6 to consume

**Contract file location (to be populated before WEL-81 begins):**
`backend/packages/contracts/wellbe_contracts/c4_processing/__init__.py`

---

#### Boundary 2: C5 → C6 (via event)

C5 emits `evidence.linked` on the outbox. C6's scoring worker consumes it. C6 also independently consumes `fact.extracted` and `health_signal.created` from C4 — for node creation, not scoring.

```
C5 evidence.linked event payload (minimum required for C6 scoring):
  source_type        → determines node type in C6 (extracted_fact → ExtractedFact node)
  source_id          → id of the fact/signal node in C6
  raw_context_event_id
  link_type          → primary | corroborating | contradicting | contextual
  confidence         → used as C5 evidence confidence input to PotentialScore formula
  patient_id
  correlation_id

C6 uses these fields to:
  1. Create or update the kg_node for source_id if it doesn't exist
  2. Find candidate kg_edges where this node is involved
  3. Set needs_rescore = true on affected edges
  4. Scoring worker recomputes PotentialScore asynchronously using all scoring inputs
```

**C6 scoring inputs for PotentialScore (all sources):**

| Input | Source |
|---|---|
| C5 evidence confidence | `evidence.linked` event |
| Co-occurrence frequency | C6 internal graph query |
| Temporal proximity | `ExtractedFact.captured_at` + `TimePoint` node |
| Source quality | `RawContextEvent.source_type` (from C3/C2) |
| Semantic similarity | pgvector cosine distance between node embeddings |
| Same-thread boost | `kg_nodes.thread_ids` overlap |
| Cross-thread recurrence | count of threads where both nodes appear |
| User confirmation/correction weight | `correction.applied` event from C11 |
| Contradiction penalty | `link_type = contradicting` in `evidence_links` (C5) |
| Recency decay | `ExtractedFact.captured_at` relative to now |

C6 scoring workers receive the C5 confidence in the event payload — they do **not** call C5 synchronously. C5 is not a dependency for C6 scoring latency.

---

#### Boundary 3: C4 → C6 (node creation, not scoring)

C6 also consumes `fact.extracted` and `health_signal.created` directly for **node creation** — independently of C5. A `kg_node` can be created when a fact is extracted, before C5 has linked its evidence.

```
C6 node creation on fact.extracted:
  kg_nodes row:
    id                = ExtractedFact.id
    patient_id        = ExtractedFact.patient_id
    node_type         = derived from fact_type
                        (symptom → Symptom, dx_mention → ConditionHypothesis,
                         medication → Medication, lab_result → LabResult, ...)
    label             = ExtractedFact.entity_label
    normalized_key    = ExtractedFact.normalized_key
    thread_ids        = [] (populated later when C7 links the thread)
    evidence_refs     = [ExtractedFact.id]  ← provisional; C5 is authoritative
    confidence        = ExtractedFact.extraction_confidence
    status            = pending_evidence    ← becomes active once C5 links it
    metadata          = { fact_type, code_system, code, quality_flag }
```

**Important:** C6 does not create edges until C5 has linked the evidence. Node creation is immediate on `fact.extracted`; edge creation and scoring require `evidence.linked`. This prevents the graph from showing connections with no provenance.

---

### Full end-to-end flow: raw text → graph edge

```
User inputs text (e.g., "I've had a headache for 3 days")
         │
         ▼
[C3] ManualTextAdapter
  → validates, normalizes → NormalizedPayload
  → calls Vault Writer → C2 stores RawContextEvent
  → C2 emits: raw_context.received
         │
         ▼
[C4] extract_facts_worker (Dramatiq, consumes raw_context.received)
  → dispatcher: source_type=manual_text → Dramatiq path
  → NER/extraction model runs
  → produces ExtractedFact:
      fact_type = symptom
      entity_label = "headache"
      normalized_key = "headache"
      extraction_confidence = 0.94
      quality_flag = clean
      raw_context_event_id = <C2 event id>
  → writes ExtractedFact to processing.extracted_facts
  → emits: fact.extracted (carries fact_id, raw_context_event_id, confidence)
         │
         ├──────────────────────────────────────────┐
         ▼                                          ▼
[C5] evidence_linker (consumes fact.extracted)    [C6] graph_node_creator (consumes fact.extracted)
  → validates raw_context_event_id exists in C2     → creates kg_node (node_type=Symptom, status=pending_evidence)
  → writes EvidenceLink:
      source_type = extracted_fact
      source_id = <fact_id>
      raw_context_event_id = <C2 event id>
      link_type = primary
      confidence = 0.94
      confidence_basis = extraction_model
  → emits: evidence.linked (carries confidence, link_type, patient_id)
         │
         ▼
[C6] graph_edge_scorer (consumes evidence.linked)
  → updates kg_node status: pending_evidence → active
  → finds candidate edges (e.g., headache co-occurs with Thread T1)
  → sets needs_rescore = true on candidate edges
  → scoring worker runs:
      potential_score = f(confidence=0.94, co_occurrence, recency, thread_boost, ...)
  → writes potential_score to kg_edges
  → emits: graph.edge_scored
         │
         ▼
[C7] Health Thread Engine (consumes graph.edge_scored + evidence.linked)
  → links headache symptom to relevant open threads
  → updates thread context window

[C10] Safety Gate (before any user-visible output)
  → reads provenance chain: kg_edge → kg_node → evidence_links → raw_context_events
  → validates: no diagnostic certainty language
  → validates: no prohibited edge types in reasoning path
```

---

### Where shared responsibility is divided (edge cases)

| Topic | Who owns it | Who does NOT own it |
|---|---|---|
| `ExtractedFact` schema | C4 defines and writes it | C5 reads it (via event), C6 reads it (via event) — neither may modify it |
| `EvidenceLink` schema | C5 defines and writes it | C4 produces the inputs; C6 consumes the confidence value |
| `PotentialScore` computation formula | C6 scoring worker | C5 provides one input (confidence); C4 provides another (co-occurrence via fact timestamps) |
| "No orphan claims" enforcement | C5 (primary) + Postgres deferred trigger (defensive) | C4 must not emit `fact.extracted` with a null `raw_context_event_id`, but C4 is not the enforcer |
| Edge type prohibition (`causes`, `diagnoses`) | C6 at schema + service + test layers | C5 does not police edge types; C4 does not know about edge types |
| `quality_flag` propagation | C4 sets it on `ExtractedFact`; C5 stores it on `EvidenceLink`; C6 stores it in `kg_node.metadata` | Each component propagates it forward — it is never dropped |
| `ConditionHypothesis` vs `Finding` vs `Condition` | C6 determines node type from `fact_type` | C4 emits `fact_type = dx_mention`; C6 maps `dx_mention → ConditionHypothesis` |
| Correction of a fact | C11 (Correction Service) emits `correction.applied` | C5 creates a new `EvidenceLink` with `correction_id`; C6 recomputes `PotentialScore` |

---

### Event spine: what each component emits and consumes

```
                    EMITS                           CONSUMES
C2 Vault        raw_context.received          ←  (from C3 Vault Writer)
C4 Pipeline     fact.extracted                ←  raw_context.received (from C2)
                health_signal.created
                document.ocr_completed
                document.ocr_failed
C5 Evidence     evidence.linked               ←  fact.extracted (from C4)
                evidence.corrected            ←  health_signal.created (from C4)
                provenance.orphan_rejected
C6 Graph        graph.node_created            ←  fact.extracted (node creation)
                graph.edge_created            ←  health_signal.created (node creation)
                graph.edge_scored             ←  evidence.linked (scoring trigger)
                graph.edge_retracted          ←  correction.applied (from C11)
                                              ←  thread.state_changed (from C7)
C7 Thread       thread.state_changed          ←  graph.edge_scored (from C6)
C11 Correction  correction.applied            ←  user action via C13
```

All events flow through the transactional outbox (`wellbe_contracts/events/outbox.py` — `OutboxEvent` model). No component calls another component's service synchronously during the fact → evidence → graph flow.

---

### Safety model checkpoint for C4-C6

Before any implementation begins, confirm these invariants hold across the three components:

| Invariant | Enforced by | Test coverage required |
|---|---|---|
| Every `ExtractedFact` has `raw_context_event_id` (non-null) | C4 at write time | Unit test: assert C4 never emits `fact.extracted` with null source ref |
| Every derived object has at least one `EvidenceLink` before becoming visible | C5 write gate + Postgres deferred trigger | Integration test: attempt to query a fact before C5 links it → should not be visible |
| No prohibited edge types in C6 | C6 service + DB lookup table + migration review gate | Test: insert `causes` edge → constraint violation; insert `may_explain` edge → success |
| `ConditionHypothesis` is never surfaced as a `Condition` | C6 node type mapping + C13 API contract | Test: `dx_mention` fact → node_type = `ConditionHypothesis`, not `Condition` |
| `quality_flag = requires_review` facts are not suppressed | C4 emits them, C5 links them, C6 creates nodes for them — all with the flag | End-to-end test: OCR failure → `quality_flag = requires_review` node appears in graph with flag visible |

---

## Relationship to downstream stories

Every story below depends on `contracts/c4_processing/__init__.py` being populated with `ExtractedFact` and `HealthSignal`:

| Story | Depends on C4 output types | How |
|---|---|---|
| WEL-83 (C5) | `ExtractedFact.raw_context_event_id` is the FK target for `evidence_links` | C5 cannot write evidence links without knowing what a fact looks like |
| WEL-64 (C7 Health Thread) | `ExtractedFact.fact_type` drives thread creation/linking logic | C7 reads facts from C5; C5 reads them from C4 |
| WEL-70 (C8 Six Memories) | `HealthSignal` feeds Pattern Memory and Clinical Memory | C8 cannot be built before the signal type is defined |
| WEL-77 (C6 Graph) | `ExtractedFact` and `HealthSignal` become `kg_nodes` | C6 node creation depends on C4 output schema |
| WEL-74 (C10 Safety Gate) | Provenance chain starts at `ExtractedFact.raw_context_event_id` | C10 traces claims back through C5 → C4 → C2 |
| `contracts/c4_processing/__init__.py` | All of the above | This file is the shared type contract — it must exist before any downstream implementation |

**The critical path is:** WEL-81 (whichever option, the story that populates `contracts/c4_processing/__init__.py`) → WEL-83 (C5) → WEL-64 (C7) → WEL-67 (C9), WEL-70 (C8), WEL-74 (C10).

---

## Recommendation (agent, pending your decision)

**Option A** — keep the current Jira structure.

Reasoning:
1. `ManualTextAdapter` and `DocumentAdapter` are already live. The C3 adapter work in WEL-81 is mostly done. WEL-81 is effectively a C4 story with a small C3 tail.
2. Under Option A, `contracts/c4_processing/__init__.py` gets populated as part of WEL-81, unblocking WEL-83 (C5) before WEL-82 (OCR) is finished. OCR is not on the critical path to C5 or C7.
3. Only one Jira change needed: update the decision record's `Also blocks` line to match WEL-82's actual title. No story retitling, no new links.
4. The WB-DEV numbering (005/006 = adapters+extraction, 007 = OCR) already reflects Option A.

Under Option A, the corrective actions are:
- Update `processing-pipeline-extraction-orchestration.md`: fix the `Also blocks` line to read "WEL-82 — Implement hybrid OCR pipeline with PaddleOCR/Tesseract and vision-LLM fallback"
- Populate `contracts/c4_processing/__init__.py` with `ExtractedFact` and `HealthSignal` as the first commit of WEL-81

---

## What gets unblocked once this decision is made

```
Decision made → Implementation order is confirmed:

  WEL-81 (C3 tail + C4 extraction, mvp, P1)
    ├─ Populates contracts/c4_processing/__init__.py
    ├─ Unblocks WEL-83 (C5, mvp, P1)  ← critical path
    └─ Can run in parallel with WEL-82

  WEL-82 (OCR pipeline, mvp, P2)
    └─ Not on critical path for C5/C7 — can follow WEL-81

  WEL-83 (C5, mvp, P1) — unblocked once WEL-81 done
    └─ Unblocks WEL-64 (C7), WEL-70 (C8), WEL-74 (C10)

  WEL-77 (C6 graph, post-mvp, P2) — unblocked once WEL-83 done
```

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
