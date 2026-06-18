# Research Brief — Typing Structured Captures in the Processing Pipeline (C4)

**For:** External researcher / analyst (no prior knowledge of this codebase assumed)
**Spike:** WEL-186 · **Blocks:** WEL-185 (C4: type-aware extraction for structured lab/vital captures)
**Decision record to be filled from this research:** `docs/decisions/structured-capture-extraction-typing.md`
**Status:** Awaiting research · **Brief written:** 2026-06-18

---

## 0. How to use this brief (read first)

You are an **external observer**. Assume you have **no access to the source code, the running system, or the team**. Everything you need is in this document. Your job is **not** to write code — it is to research how comparable systems (clinical data pipelines, health-data interoperability standards, NLP/IE systems, and event-driven processing platforms) solve the questions in §6, and to return a findings document we can turn into a design decision.

> **Do not** propose a solution that depends on details not in this brief. If something is missing, state the assumption explicitly in your findings.

### What to deliver — return your research as a downloaded file

Produce a **single self-contained file** and **download/export it** (do not paste only into a chat). We will ingest that file directly.

- **Filename:** `WEL-186-structured-capture-extraction-typing-research-findings.md` (Markdown preferred; PDF acceptable).
- **Where to put it:** export/download it to your machine and hand the file back (the same way prior briefs' findings were delivered as `~/Downloads/WEL-XXX-...-research-findings.md`).
- **Structure (use these exact headings):**
  1. `## Summary` — 5–10 line executive answer.
  2. `## Sources reviewed` — every source with title, author/org, year, URL, and a one-line note on credibility.
  3. `## Findings by question` — one subsection per question Q1–Q5 in §6.
  4. `## Approaches considered` — 2–4 distinct end-to-end approaches to typing structured captures, each as: *Approach N — what it does | Pros | Cons | Fit with our constraints (§5)*.
  5. `## Recommendation` — one concrete recommended approach and the trade-offs accepted.
  6. `## Open risks / unknowns` — anything still needing a product, clinical, or data-modeling decision.
- **Citations:** every non-obvious claim cites a source from "Sources reviewed".
- **Grounding rule:** base findings on the sources you cite. Label any reliance on your own prior knowledge as such.

---

## 1. What WellBe is (context for an outsider)

WellBe is a **patient-centered health investigation operating system**. Its core is a **personal, user-controlled health memory**: an individual collects their own health context (symptoms, lab results, vitals, notes, documents, device data) and the system links it into **Health Threads** (containers for one unresolved/ongoing health concern) and helps carry each concern forward until it is resolved, explained, monitored, or safely handed off.

**The individual is always the data controller.** WellBe is **non-diagnostic**: it never asserts a diagnosis or a clinical verdict. It organizes, links, and surfaces *what the user's own records contain*, with strict "never alarm" framing and a safety review layer over any composed output. Every derived fact must trace back to its raw source ("no orphan claims").

This brief is about an internal data-processing problem — **how raw captures become correctly-typed structured knowledge** — which sits underneath nearly every user-facing feature. Getting the typing right is what lets the rest of the system reason over a person's data without silently dropping or mislabeling it.

## 2. The problem we are solving

When a user (or an import) records a piece of health context, it enters WellBe as a **capture** with a declared **type** — for example:

- `symptom` — free text, e.g. *"Dry cough most mornings for three weeks, unusual afternoon tiredness."*
- `lab` — **structured** fields, e.g. `{ test_name: "LDL cholesterol", value: "165", unit: "mg/dL", reference_range: "<130" }`
- `note` — free text.
- (and others, including vital signs such as blood pressure.)

A downstream **Processing Pipeline** turns each capture into one or more **facts** (typed atomic assertions), and each fact becomes a **node** in a personal knowledge graph. Nodes carry a **node type** (e.g. `Symptom`, `LabResult`, `VitalSign`, `Medication`, `Other`). Many features filter strictly by node type — for instance, a "coverage" view of health areas (cardiovascular, metabolic, etc.) only counts `LabResult` and `VitalSign` nodes.

**The defect:** structured `lab` and vital-sign captures are currently **flattened to plain text** and run through a lightweight, keyword-based text extractor that only recognizes a fixed list of symptom and medication words. Anything it doesn't recognize falls back to the catch-all type `Other`. As a result, real lab results (LDL, HbA1c, blood pressure, Vitamin D) all become `Other` nodes — and every feature that filters on `LabResult`/`VitalSign` treats the workspace as if it has **no current data**, even though the data is present and correctly stored at the raw level.

The product question: **how should the pipeline derive a capture's fact type (and therefore its node type) when the capture's structured type and fields are already known — and what is the contract for that mapping — without regressing the existing free-text path or the pipeline's reliability guarantees?**

## 3. How the pipeline works today (factual — for grounding)

You do not need to write code, but this scopes realistic recommendations.

- **Capture → raw store.** A capture is persisted immutably as a raw event with its declared type and payload, plus provenance.
- **Raw event → facts (extraction).** A worker reads the raw event and runs an **extractor**. The only live extractor is a **rule-based, keyword-matching text extractor**: it scans text for a small fixed vocabulary of symptoms and medications; if nothing matches, it emits a single fallback fact of type `OTHER`. It does **not** parse lab values, units, reference ranges, or recognize that the capture was declared `lab`/vital.
- **Facts → graph nodes.** Each fact is upserted into the knowledge graph. A **fact-type → node-type map already exists** and already includes correct targets such as `lab_result → LabResult` and `vital_sign → VitalSign`. The gap is purely **upstream**: no extractor ever produces those fact types, so those map entries are never exercised.
- **Reliability guarantees (must be preserved).** The pipeline is **event-driven and at-least-once**: the same raw event can be redelivered. Today this is made safe by **deterministic fact IDs** (a re-processed event yields the same fact id, and inserts are idempotent), idempotent graph-node upserts (keyed on patient + node type + a normalized key), and "process each fact's downstream work only if it was newly inserted." Any new extraction path must keep these properties.
- **Safety.** Composed, user-facing outputs pass a safety/governance gate (non-diagnostic, never-alarm). Typing a node is **not** a clinical claim — it is structural classification — but the research should be mindful that WellBe must never turn "we recognized this as a lab" into "this lab is normal/abnormal/concerning."

### Concrete illustration (real, from a seeded test profile)

Captured: LDL cholesterol 165 mg/dL (ref <130), HbA1c 5.4% (ref 4.0–5.6), Blood pressure 128/82 mmHg, Vitamin D 22 ng/mL (ref 30–100), plus several symptom and note captures.

Result in the graph: the four lab/vital items were stored as **node type `Other`** (not `LabResult`/`VitalSign`). The symptom captures became `Symptom` nodes. Because the coverage feature counts only `LabResult`/`VitalSign`, it reported **"no current data across all areas"** despite the labs being present.

## 4. What exists vs. what does not (factual)

**Exists:**
- A declared `capture_type` on every capture, and structured payloads for `lab` (and the ability to express vitals).
- An immutable raw store with provenance.
- A fact model with a `fact_type` field and a defined enum of fact types (including `lab_result`, `vital_sign`, `symptom`, `medication`, `finding`, `allergy`, `procedure`, `immunization`, `family_history`, `social_history`, `other`).
- A correct `fact_type → node_type` map (already supports `LabResult`, `VitalSign`, etc.).
- Idempotency/redelivery safety mechanics (deterministic fact ids, idempotent upserts).

**Does NOT exist:**
- Any extraction path that uses the **declared capture type** (or parses structured lab/vital fields) to emit `lab_result` / `vital_sign` facts.
- Any parsing of lab **value / unit / reference range** into structured fields on the fact, or any **coding** (e.g. mapping a test name to a standard code system).
- A defined **contract** for "given `capture_type` + payload, what `fact_type` (and what normalized identity / optional code) results."

**The gap this research closes:** the design of a typed-extraction approach for structured captures and its contract, so labs/vitals reliably become `LabResult`/`VitalSign` nodes — chosen against real options used in clinical-data and IE systems, and compatible with our reliability and safety constraints.

## 5. Constraints your recommendation must satisfy

1. **Correct typing for known-structured captures.** A `lab` capture must become a `LabResult`; a vital-sign capture (e.g. blood pressure) must become a `VitalSign`.
2. **No regression of the free-text path.** Symptom/medication/free-text extraction must keep working unchanged.
3. **Idempotency / at-least-once safety preserved.** Re-processing the same capture must not create duplicates or double-fire downstream work (deterministic identity must still hold for the new fact types).
4. **No orphan claims.** Every produced fact must remain traceable to its raw source.
5. **Non-diagnostic & never-alarm.** Typing is structural only. The approach must not introduce any clinical interpretation, reference-range verdict, or alarm.
6. **Extensible & future-proof.** The mapping/contract should accommodate additional structured capture types over time (e.g. wearables, immunizations) without a redesign, and should not paint us into a corner if richer extraction (NLP/LLM/NER) is added later.
7. **Migration awareness.** Node typing is a contract the whole graph depends on; the research should consider how existing mis-typed (`Other`) nodes would be corrected, since re-typing historical data is effectively a data migration.

## 6. The research questions (answer each in your deliverable)

- **Q1 — Where should type come from for structured captures?** When a capture's *type is already declared* and its payload is structured (vs. free narrative), what do comparable systems do to derive the canonical entity/fact type? Options seen in the wild include: trusting the declared type via a deterministic mapping; a dedicated structured parser per type; routing by content/MIME at a dispatcher; or running everything through an NLP/IE model. What are the trade-offs (precision, maintainability, drift) of **declared-type mapping vs. inferred/NLP typing** for *structured* inputs specifically?
- **Q2 — What is a good `capture_type` + payload → fact_type/node_type contract?** How should such a mapping be specified so it is unambiguous, testable, and extensible (e.g. table-driven mapping, a typed schema/registry per capture type, validation rules)? How do mature health/data pipelines version and govern such a mapping so changes are safe?
- **Q3 — How much structured parsing belongs in typing, and how do standards model labs/vitals?** Should the fact also carry parsed **value/unit/reference range** and a **code** (e.g. LOINC for labs, standard vitals representations, UCUM units)? What do interoperability standards (e.g. HL7 FHIR Observation for labs/vitals, LOINC, UCUM, SNOMED) recommend, and what is a pragmatic *minimum* that achieves correct typing now while leaving room for richer normalization later — without overreaching into clinical interpretation?
- **Q4 — Preserving idempotency for typed structured facts.** How should the **deterministic identity / normalized key** of a structured lab/vital fact be derived (e.g. from test name + value + unit + timestamp, or a code) so that at-least-once redelivery stays idempotent and the same logical result doesn't create duplicate nodes — while still distinguishing genuinely different results over time? What patterns do event-driven clinical pipelines use here?
- **Q5 — Coexistence, routing, and migration.** How should a structured-typing path **coexist** with the free-text extractor (dispatch/routing by capture type or content), so each input takes the right path and neither regresses the other? And what are sound strategies to **re-type or backfill** already-ingested data that was mis-typed as `Other`, given an immutable raw store and an idempotent graph (reprocess-from-raw vs. targeted migration), including how to do so safely and reversibly?

## 7. Out of scope for this brief

- Implementation/code design — derived after a decision is approved.
- Full clinical NLP of free-text narratives (the existing free-text extractor's *quality* is a separate concern); this brief is about **structured** captures whose type is already known.
- Reference-range evaluation, normality judgments, or any diagnostic interpretation — explicitly excluded by WellBe's non-diagnostic posture.
- The user-facing presentation of signals/coverage — a separate, already-decided concern; here we only ensure the underlying nodes are typed correctly.

## 8. Glossary

- **Capture** — a single recorded piece of health context, with a declared `capture_type` (e.g. `symptom`, `lab`, `note`) and a payload.
- **Raw event** — the immutable, provenance-bearing stored form of a capture.
- **Fact** — a typed atomic assertion derived from a raw event (has a `fact_type` and a normalized key).
- **Extractor** — the component that turns raw event text/payload into facts. Today: a keyword-based text extractor only.
- **Node / node type** — an entity in the personal knowledge graph; its type (e.g. `LabResult`, `VitalSign`, `Symptom`, `Other`) is what downstream features filter on.
- **Idempotency / at-least-once** — the same event may be processed more than once; the system must produce the same result without duplicates.
- **No orphan claims** — every derived fact must link back to its raw source.
- **Non-diagnostic / never-alarm** — WellBe never asserts diagnoses or alarms; it organizes the user's own data.

---

_When your findings file is ready, return it to the team. It will be recorded verbatim under "Research provided" in `docs/decisions/structured-capture-extraction-typing.md`, after which approaches and a proposed decision are written and sent for approval. No implementation happens until that decision is approved._
