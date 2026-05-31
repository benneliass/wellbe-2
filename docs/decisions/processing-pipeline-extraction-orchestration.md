# Decision: Processing Pipeline extraction orchestration and fact schema

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-96  
**Blocks:** WEL-81 — Build ingestion adapter framework and entity/fact/signal extraction pipeline; WEL-82 — Hybrid OCR pipeline

---

## Question

How should the Processing Pipeline (C4) orchestrate entity/fact/signal extraction — as synchronous in-request processing, as Dramatiq workers, or as Temporal workflow activities — and what is the canonical extracted entity/fact/signal schema that feeds into C5 (Evidence & Provenance) and C6 (Knowledge Graph)?

Specifically:
1. What is the orchestration model — are extraction steps synchronous, async Dramatiq jobs, or Temporal activities? What triggers the pipeline (a `raw_context.received` event, an API call, or both)?
2. What is the canonical `ExtractedFact` / `HealthSignal` schema — what fields are required before the output is passed to C5?
3. How are quality/confidence scores computed and stored — is confidence a float on the fact, a separate scoring model, or a derived property of the extraction method?
4. How does the OCR pipeline integrate — is it a Dramatiq job, a Temporal activity, or a synchronous step within an adapter?

## Context

C4 sits at layer L2. It consumes raw events from C2 and produces `ExtractedFact` and `HealthSignal` objects that C5 links back to their raw sources and C6 indexes into the graph. The `ExtractedFact`/`HealthSignal` schema is the contract between C4, C5, and C6 — changing it after any of those three are built requires migrations across all three.

The tech stack has committed to Dramatiq (lightweight, fire-and-forget) and Temporal (durable, long-running) as the two async tiers. The OCR pipeline is explicitly hybrid: self-hosted PaddleOCR-VL/Tesseract as tier-1, vision-LLM fallback as tier-2, with hash-based caching to avoid reprocessing. The pipeline emits two named events: `fact.extracted` and `health_signal.created`, which are the triggers for downstream C5 and C6 work.

**Key constraint:** The pipeline cannot be synchronous on the request path for large documents — a PDF OCR step can take seconds to minutes. But the schema of what the pipeline produces must be decided before C5 and C6 can be built.

## Research provided

_Awaiting user research._

_Research received: —_

## Approaches considered

_To be written after research is received._

## Decision

_To be written after research is received and approved._

## Trade-offs accepted

_To be written after research is received and approved._

## Implementation notes

_To be written after approval._

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
