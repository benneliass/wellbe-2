# Decision: How C4 extraction types structured lab/vital captures

**Status:** Approved  
**Date opened:** 2026-06-18  
**Date approved:** 2026-06-18  
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

_Research received: 2026-06-18_

Source: user-supplied findings file `WEL-186-structured-capture-extraction-typing-research-findings.md` (faithful summary below; the full file is the authoritative record). Findings are grounded in cited external sources — primarily HL7 FHIR (the **Observation** resource [S1/S2], the **Vital Signs** profile [S3], the **Observation Category** value set with `laboratory`/`vital-signs` [S4], US Core **lab** [S5] and **vital** [S6] profiles, **profiling/StructureDefinition** [S7], **Provenance** [S8], **ConceptMap** [S9], **Resource Identity** [S21], **ObservationInterpretation** [S22]), terminology standards (**LOINC** [S10], **UCUM** [S11/S12]), the **OMOP** Measurement domain [S13], clinical NLP work (**cTAKES** [S14], **NLP2FHIR** [S15]), and distributed-systems patterns (**idempotent consumer** [S18], **AWS retry/idempotency** [S17], **event sourcing** [S19], **projections** [S20], **schema registry** [S16]).

Key findings:

- **Mature health-data models type labs/vitals structurally, not via NLP.** FHIR and OMOP model labs and vitals as structured observations/measurements with explicit category, code, subject, time, value, and unit — they do not need free-text NLP to recognize that a structured LDL or blood-pressure value is an observation. [S1][S3][S5][S6][S13] Clinical NLP (cTAKES, NLP2FHIR) is for *unstructured narrative*; NLP2FHIR explicitly separates an NLP engine for notes from structured-data integration via mappings/templates. [S14][S15]
- **`capture_type` is sufficient for routing but not for final type.** Because WellBe has no dedicated `vital` capture type (vitals arrive as `lab`), `capture_type=lab` should route to a structured observation extractor; inside it, the fact is `vital_sign` only when the payload matches a governed vital-sign concept (by code/category/normalized test name/unit/value shape), else `lab_result`. FHIR's vital category + minimum vital concepts + componentized blood pressure support this content-based distinction. [S3][S4][S6]
- **Contract should be a versioned, testable registry**, not scattered code — mapping `capture_type` + payload predicate → `fact_type`, required/optional fields, normalized identity, emitted fields, provenance, and migration behavior; governed like FHIR profiles / ConceptMap and schema-registry compatibility. Additive vital aliases/units are backward-compatible; reclassifying an existing normalized key needs a new contract version + backfill. [S7][S9][S16]
- **Correct typing must not wait for full terminology normalization.** Emit `LabResult`/`VitalSign` with raw source fields, a normalized display/key, best-effort parsed value/unit/reference where unambiguous, **nullable** LOINC/UCUM code fields, a normalization status (`raw_only`/`unit_normalized`/`coded`), and provenance. FHIR/OMOP separate observation structure from optional coding, so a typed fact can exist before coding. [S1][S2][S13]
- **No clinical interpretation in this step.** FHIR keeps interpretation separate from code/value; HL7 ObservationInterpretation (normal/abnormal/high/low) is a qualitative assessment. WellBe (non-diagnostic, never-alarm) must not compute normality/abnormality/alarm; source-provided flags may be stored only as source metadata with provenance, never as a WellBe judgment. [S2][S22][S8]
- **Idempotency at two levels.** Fact ID derived from immutable source identity (`raw_event_id` + payload path/ordinal + extractor family/contract major version), so redelivery or later unit-normalization doesn't create duplicates. The graph-node key should additionally include occurrence/effective time (with source identity as tie-breaker) so distinct readings over time stay distinct while the same raw event stays idempotent. Blood pressure → one `vital_sign` fact with systolic/diastolic components, not one lab or two unrelated facts. [S8][S17][S18][S21][S2][S3]
- **Fix history by reprocess-from-raw, not by mutating raw captures.** Replay/backfill `capture_type=lab` raw events through the new extractor in a controlled migration mode (dry-run diff, deterministic ids, gated downstream side effects, provenance + job metadata), and **supersede/deprecate** old `Other` nodes rather than deleting evidence; favor rebuild-from-raw over in-place graph mutation. [S19][S20][S8]

The findings evaluated four end-to-end approaches and recommended **Approach 1 (deterministic structured extractor with a governed vital exception), carrying the future-proofing discipline of Approach 4 (structural typing now, optional terminology enrichment later)**.

## Approaches considered

All four are taken from the provided research (§ "Approaches considered").

- **Approach 1 — Deterministic structured extractor with governed vital exception.** Route by `capture_type`; send `lab` to a structured observation extractor that emits `vital_sign` when a versioned vital registry matches, else `lab_result`; keep `symptom`/`note` on the existing text path. *Pro:* high precision, deterministic/testable, preserves idempotency via stable source-derived ids, directly fixes the `Other` defect, no interpretation. *Con:* must maintain a vital registry + normalization rules; relies on local aliases where no standard code exists; unusual home/device vitals may misclassify until the registry expands. *Fit (§5):* **best fit.**
- **Approach 2 — Full FHIR/terminology normalization before graph ingestion.** Convert every structured capture into a profile-conformant FHIR Observation (LOINC, UCUM, components, Provenance) and derive type from the profile. *Pro:* strong interoperability/export foundation; rich fields. *Con:* too heavy for the immediate defect if it *blocks* typing on complete normalization; LOINC/UCUM mapping can be incomplete; profile-conformance governance overhead before WellBe needs interchange. *Fit:* good future direction, not the best first step.
- **Approach 3 — Universal NLP/LLM/inferred extractor for all captures.** Flatten everything (incl. structured labs/vitals) to text and infer type with a model. *Pro:* unified path; good for messy narrative. *Con:* discards reliable schema info, adds drift/eval burden, makes idempotency harder, risks regressing the free-text path, and doesn't solve the vital exception without a governed registry (at which point it's a less-deterministic Approach 1). *Fit:* weak for structured typing.
- **Approach 4 — Two-stage: structured typing now, optional terminology enrichment later.** Approach 1 first; then async/separate enrichment (LOINC/UCUM/FHIR shaping) that is *additive* and never downgrades a typed fact back to `Other`, with governed migration only when a reclassification is approved. *Pro:* fixes the defect quickly, keeps a standards-compatible path, preserves idempotency by treating enrichment as additive metadata. *Con:* two related contracts (typing vs enrichment); must prevent enrichment failures from downgrading facts and decide when enrichment is strong enough to change keys/trigger migration. *Fit:* very strong if scoped carefully (Approach 1 + explicit future-proofing).

## Decision

**Adopt Approach 1 as the immediate design, with Approach 4's future-proofing discipline.** Concretely:

1. **Dispatch by `capture_type`** before extraction: `symptom` and `note` → existing `TextFactExtractor` (unchanged); `lab` → a new deterministic **structured observation extractor**; `document` → existing document/OCR path (out of scope).
2. **Inside the `lab` route:** if the payload matches a **versioned `VitalConceptRegistry`** (by source code/category, normalized test name, unit, or value shape) → `fact_type = vital_sign`; otherwise → `fact_type = lab_result`. Node type follows the existing `FACT_TYPE_TO_NODE_TYPE` map (`LabResult`/`VitalSign`). Blood pressure is one `vital_sign` fact with systolic/diastolic components.
3. **Typing is not blocked on terminology.** Emit the typed fact with: raw `test_name`/`value`/`unit`/`reference_range`, source/capture time, `raw_event_id` + payload path, extractor + contract version; a normalized observation key/display; best-effort parsed value/unit/components only when unambiguous; **nullable** `code_system`/`code`/`code_display` and a `normalization_status` (`raw_only`/`unit_normalized`/`coded`). LOINC/UCUM coding and FHIR shaping are deferred, additive enrichment.
4. **No clinical interpretation.** Never compute normality/abnormality/concern/diagnosis/alarm. Any source-provided abnormal flag is stored only as source-provided metadata with provenance.
5. **Idempotency at two levels.** Fact ID from immutable source identity (`raw_event_id` + payload path/ordinal + extractor-family/contract-major-version). Graph-node key includes patient + node type + normalized observation identity + occurrence/effective time, with source identity as tie-breaker when time is missing/coarse.
6. **Contract is a governed, versioned, testable artifact** (table/registry) with golden fixtures for LDL, HbA1c, blood pressure, Vitamin D, plus symptom/note negative cases; additive changes are backward-compatible, reclassifications require a new version + backfill plan.
7. **Historical correction by reprocess-from-raw.** Replay `capture_type=lab` raw events through the new extractor in a controlled backfill (dry-run diff, deterministic ids/upserts, gated downstream side effects, provenance + migration-job metadata); **supersede/deprecate** old `Other` nodes rather than mutating raw captures.

## Trade-offs accepted

- WellBe maintains a small but explicit, versioned vital-sign registry (and must expand it for new vitals/devices).
- Some facts will initially be `raw_only`/uncoded while still correctly typed; full LOINC/UCUM normalization, FHIR export shape, and improved free-text NLP are **deferred**.
- Historical `Other` nodes require a backfill/migration step (not a free side effect).
- We accept two related contracts (structural typing vs later enrichment) and the discipline to prevent enrichment failures from downgrading typed facts.
- These are preferred over leaving structured data invisible to type-filtered features, or making correctness depend on a broad NLP/LLM inference path.

## Implementation notes

Touches (per the live code reviewed for this Spike):
- `backend/packages/c4_processing/src/wellbe_c4_processing/extractor.py` — add a structured observation extractor producing `FactType.LAB_RESULT` / `FactType.VITAL_SIGN`; leave `TextFactExtractor` unchanged.
- `backend/apps/processing-worker/src/wellbe_processing_worker/tasks.py` — dispatch on `capture_type` before extraction; reuse `FACT_TYPE_TO_NODE_TYPE` (already maps `lab_result`/`vital_sign`); keep `_deterministic_fact_id` semantics and extend the normalized key with occurrence time for structured facts.
- The capture→`_raw_text`/`source_metadata` serialization (capture path / ingestion) currently discards `capture_type` for the structured payload — preserve the structured payload + declared type so the structured extractor can consume it.
- New artifacts: a versioned `VitalConceptRegistry` (registry + golden fixtures) and a backfill/migration job for `capture_type=lab` `Other` nodes.
- Out of scope here: LOINC/UCUM mapping, FHIR conformance, document/OCR path, free-text NLP quality, signals/coverage presentation. See the findings file's "Open risks / unknowns" (vital scope, node granularity/occurrence time, timestamp rules, terminology governance, reference-range representation, malformed captures, migration mechanics, backfill side effects, source-provided-flag safety) — these inform WEL-185 implementation sub-decisions.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
