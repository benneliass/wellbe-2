# Decision: Processing Pipeline entity extraction orchestration

**Status:** Approved  
**Date opened:** 2026-05-31  
**Date approved:** 2026-05-31  
**Approved by:** User  
**Jira Spike:** WEL-96  
**Blocks:** WEL-81 — Build pluggable Ingestion Layer with unified adapter protocol  
**Also blocks:** WEL-82 — Implement hybrid OCR pipeline with PaddleOCR/Tesseract and vision-LLM fallback

---

## Question

How should the Processing Pipeline (C4) orchestrate entity/fact/signal extraction — as synchronous in-request processing, as Dramatiq workers, or as Temporal workflow activities — and what is the canonical extracted entity/fact/signal schema that feeds into C5 (Evidence & Provenance) and C6 (Knowledge Graph)?

Specifically:
1. Does extraction run synchronously in the ingestion HTTP request, as a Dramatiq worker, or as a Temporal workflow?
2. What triggers extraction — a direct call from C3, an event consumed from an outbox/stream, or a scheduled job?
3. What is the canonical `ExtractedFact` and `HealthSignal` schema — what provenance and confidence fields must they carry?
4. How does OCR fit into the pipeline — when does it run and what does it produce?

## Context

C4 is the first transformation step. It reads raw events from C2 and produces structured `ExtractedFact` and `HealthSignal` objects that flow downstream into C5 (evidence linking) and C6 (graph nodes). C4 never writes back to C2 — it only reads it. The quality of C4 output determines the quality of everything in C5 and C6.

The choice of orchestration model has major operational implications: synchronous processing blocks ingestion throughput; Dramatiq workers are lightweight but lack durability and retry semantics for complex multi-step jobs; Temporal workflows provide durability and checkpointing at higher operational cost. OCR is specifically called out as a heavy operation requiring its own pipeline path.

## Research provided

### Executive summary (C4)

Extraction is async-first. C4 is triggered by consuming the `raw_context.received` event (from C2 via the outbox). Lightweight extraction (structured text, simple records) uses Dramatiq workers. Long-running work (OCR, degraded images, FHIR/bulk, vision model fallback) uses Temporal workflows. `ExtractedFact` and `HealthSignal` are separate output types, each carrying extraction confidence, quality metadata, model/pipeline versioning, and source span references back to the originating `RawContextEvent`.

### Q1 — Orchestration model

**Recommended approach:** two-tier async.

| Work type | Orchestration |
|---|---|
| Structured text, simple JSON, short records | Dramatiq worker (`extract_facts_worker`) |
| Long/complex documents, degraded quality | Temporal `DocumentExtractionWorkflow` |
| OCR pass on photo/PDF | Temporal `DocumentOCRWorkflow` |
| FHIR/bulk imports (pages, retries, cursor) | Temporal `FHIRProcessingWorkflow` |
| Vision model fallback (OCR failed) | Temporal `VisionExtractionWorkflow` |

Neither Dramatiq nor Temporal should be called synchronously inside an HTTP request. C4 workers and workflows are triggered by event consumption, not by C13 request cycles.

### Q2 — Trigger model

**Recommended approach:** C4 consumes the `raw_context.received` event.

```
raw_context.received (from C2 outbox)
  → C4 dispatcher decides orchestration path based on source_type / mime_type
  → routes to Dramatiq worker OR Temporal workflow
  → extraction runs; produces ExtractedFact / HealthSignal rows
  → emits fact.extracted / health_signal.created / document.ocr_completed / document.ocr_failed
```

C4 never calls back to C3 or C2 to update the raw event. C4 appends its outputs to its own tables and emits events for C5 and C6 to consume.

### Q3 — Canonical schemas

**`ExtractedFact` (discrete factual claim):**
```
id, patient_id, raw_context_event_id (FK to C2),
fact_type (symptom | finding | medication | lab_result | allergy | procedure | dx_mention | ...),
entity_label, normalized_key, code_system (nullable), code (nullable),
text_span_start, text_span_end, source_text_excerpt_hash,
extraction_confidence, extraction_model, model_version, pipeline_version,
quality_flag (clean | low_confidence | requires_review | partial),
quality_metadata (jsonb),
is_negated, is_historical, is_hypothetical,
subject (patient | family_member | other),
captured_at, extracted_at,
correlation_id, trace_id,
schema_version, created_at
```

**`HealthSignal` (aggregate or computed signal):**
```
id, patient_id, raw_context_event_ids (array FK),
signal_type (pain_level | mood_score | fatigue | sleep_quality | ...),
signal_value, signal_unit, signal_direction,
aggregation_method, observation_window,
extraction_confidence, extraction_model, model_version, pipeline_version,
quality_flag, quality_metadata (jsonb),
captured_at_start, captured_at_end, extracted_at,
correlation_id, trace_id,
schema_version, created_at
```

Both types carry source span references or source event IDs for C5 evidence linking. C5 must never receive a fact or signal without at least one traceable raw source.

### Q4 — OCR pipeline

**Recommended path:**

```
raw_context.received (mime_type = image/*, application/pdf)
  → C4 dispatcher starts DocumentOCRWorkflow
  → activity: OCR extraction (PaddleOCR primary, vision model fallback)
  → on success: emit document.ocr_completed with extracted text
  → on failure (all paths exhausted): emit document.ocr_failed with quality_flag = requires_review
  → ExtractedFacts are created from OCR text, carrying ocr_model, ocr_version, ocr_confidence
```

OCR failures do not block the `RawContextEvent` from being ingested (C2 already has it). They produce a `quality_flag = requires_review` fact and an `ingestion.item_failed` event for the user to see that the document needs attention.

### References

- FHIR Observation — https://build.fhir.org/observation.html
- PaddleOCR documentation — https://www.paddleocr.ai/main/en/index.html
- Temporal Python activity timeouts — https://docs.temporal.io/develop/python/activities/timeouts
- Dramatiq guide — https://dramatiq.io/guide.html

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| Synchronous in-request extraction | Rejected | Blocks ingestion throughput; HTTP timeouts are misaligned with extraction duration |
| Dramatiq workers for all extraction | Rejected | Lightweight work only; no durability, checkpointing, or retry semantics for OCR/FHIR |
| Temporal workflows for all extraction | Rejected | Overkill for simple structured-text extraction; adds unnecessary overhead |
| Two-tier (Dramatiq for lightweight + Temporal for long-running) | **Accepted** | Right tool for each case; both triggered by event consumption |
| C4 triggered by direct C3 call | Rejected | Couples ingestion synchronously to processing; breaks async-first posture |
| C4 triggered by `raw_context.received` event | **Accepted** | Clean decoupling; C4 can replay, scale, and fail independently of C3 |
| `ExtractedFact` and `HealthSignal` merged into one type | Rejected | Different semantics: facts are discrete claims; signals are aggregated/computed values |
| Separate `ExtractedFact` and `HealthSignal` | **Accepted** | Type-safe contracts for C5 and C6 |
| OCR failure blocks ingestion | Rejected | C2 already has the raw event; OCR failure should be a reviewable quality flag |

## Decision

C4 runs asynchronously after raw context is committed to C2. C4 is triggered by consuming the `raw_context.received` event from the outbox. Lightweight extraction uses Dramatiq workers; OCR, degraded documents, FHIR/bulk imports, and vision fallback use Temporal workflows. `ExtractedFact` and `HealthSignal` are separate output types, each carrying source span references, extraction confidence, quality flags, and model/pipeline versioning. OCR failures produce a `quality_flag = requires_review` fact and are surfaced to the user — they do not block the raw event from being stored.

## Trade-offs accepted

- Two-tier orchestration adds operational complexity (both Dramatiq and Temporal must be running) — accepted because the two have genuinely different requirements.
- OCR failures are non-blocking — accepted; a failed OCR still stores the raw blob in C2, which the user can retry or correct later.
- `ExtractedFact` and `HealthSignal` are separate tables — accepted for type safety at the cost of additional schema surface.

## Implementation notes

- C4 dispatcher must make the Dramatiq/Temporal routing decision based on `source_type` and `mime_type` from the `raw_context.received` event payload, not from polling C2 tables.
- Every `ExtractedFact` must have a non-null `raw_context_event_id`. The C5 write gate enforces this, but C4 must also validate it before emitting `fact.extracted`.
- Events emitted via outbox: `fact.extracted`, `health_signal.created`, `document.ocr_completed`, `document.ocr_failed`.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
