# Decision: How C4 extraction types structured lab/vital captures

**Status:** Open  
**Date opened:** 2026-06-18  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-186  
**Blocks:** WEL-185 [C4: type-aware extraction for structured lab/vital captures]

---

## Question

When a capture arrives with a **known, structured type** (e.g. `capture_type="lab"` with `test_name`/`value`/`unit`/`reference_range`, or a vital sign like blood pressure), how should the C4 Processing Pipeline derive its `FactType` (and therefore its C6 `node_type`)?

Specifically:
- Should structured captures get a **dedicated, deterministic extraction path** that emits `LAB_RESULT` / `VITAL_SIGN` facts (parsing value/unit/reference and ideally a code system), instead of being flattened to text and run through the free-text symptom/medication keyword extractor (which has no lab/vital rules and falls back to `OTHER`)?
- What is the contract for `capture_type` + payload → `FactType` (+ optional code/normalization), and where does it live (ingestion adapter, a structured extractor sibling to `TextFactExtractor`, or the dispatcher route)?
- How do we add this without regressing the existing free-text path (symptoms/medications) or the idempotency/redelivery guarantees in the worker?

## Context

This affects **C4 — Processing Pipeline** (`docs/architecture/component-map.md`, entity/fact extraction and classification), with downstream effects on **C6 — Knowledge Graph Store** node typing and any consumer that filters by `node_type` (Home Signals coverage, pattern/genesis logic).

Today the MVP `TextFactExtractor` only matches symptom/medication keywords and falls back to `FactType.OTHER`. Structured `lab`/`vital` captures are stringified and therefore land as `node_type="Other"`. The `FACT_TYPE_TO_NODE_TYPE` map already supports `lab_result → LabResult` and `vital_sign → VitalSign` — nothing upstream ever produces those fact types. Observed live: the seeded Dev workspace has LDL, HbA1c, blood pressure, and Vitamin D nodes all typed `Other`, so the coverage-first Signals engine (which counts only `LabResult`/`VitalSign` for Cardiovascular/Metabolic/Vitals/Inflammation) reports "no current data" despite the data existing.

Guessing wrong is expensive because typing is the contract the entire graph and every downstream filter relies on; mis-typing silently suppresses real signals, and re-typing historical nodes after the fact is a migration.

## Research provided

<!-- Filled when the user provides research. -->

_Research received: YYYY-MM-DD_

## Approaches considered

<!-- Written by agent after receiving research. -->

## Decision

<!-- Proposed/approved decision — one concrete statement. -->

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. Likely touches:
     - backend/packages/c4_processing/src/wellbe_c4_processing/extractor.py
     - backend/apps/processing-worker/src/wellbe_processing_worker/tasks.py (dispatch + FACT_TYPE_TO_NODE_TYPE)
     - the capture→raw_text serialization that currently discards capture_type -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
