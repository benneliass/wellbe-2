# Benchmark Expected-Results Prediction Report

> **⚠️ THIS IS A FORWARD PREDICTION, NOT MEASURED OUTPUT.**
>
> Every number and statement in this document is *predicted from first principles* using only
> (a) the raw benchmark fixture data under `tests/fixtures/benchmark/` and
> (b) the system-design docs under `docs/system-design/` plus the current rule-based implementation
> in `backend/`.
>
> **Nothing here was produced by running the WellBe platform.** No Postgres query, no service call,
> no `seed.sh`, no `kubectl`. This artifact exists so a human can later diff *predicted* vs *actual*
> platform output. Where a prediction is an estimate rather than a deterministic derivation, it is
> labelled as such with an explicit range and reasoning.
>
> Two prediction tracks are kept distinct throughout:
> - **Current-implementation-expected** — what the *code as it exists today* will produce. These are
>   largely **deterministic** because the extractor is a fixed keyword matcher; they were re-derived
>   by an offline script that mirrors the extractor/dedup logic exactly.
> - **Design-expected** — what the *system-design docs intend* the mature pipeline to produce. These
>   are **estimates / ranges**, because the intended LLM/NER extractor, auto-linker, intelligence
>   engines, and Health Thread state machine are **not implemented** in the path that processes this
>   corpus.

---

## 0. Executive summary

The benchmark corpus is **5 de-identified longitudinal cases (C01–C05)**, each provided in two modes
(`blind_pre_diagnosis` and `full_results_no_final_label`). No `answer_key/` is present; no final
labels are asserted, and this report deliberately asserts **no diagnoses** (consistent with the
do-not-diagnose safety posture).

The single most important finding for prediction accuracy:

- **The seed harness (`seed.sh`) rewrites every event's `source_type` to `manual_text`.** Per the
  C4 dispatcher (`dispatcher.py`), `manual_text` routes to the lightweight **Dramatiq text path**,
  i.e. the rule-based `TextFactExtractor`. So **100% of events** — labs, imaging, pathology,
  genetics, everything — are processed by a **10-symptom / 4-medication keyword matcher**, not by
  any structured clinical extractor.
- The text the extractor sees is `raw_payload.original.event` when present (only the `timeline_*`
  events have it) and otherwise `json.dumps(raw_payload)` (all `obs_*` events). So for `obs_*`
  events the keyword match runs over the **serialized JSON** (field names + values).
- Consequently, in the **current implementation**, almost every event collapses to a single
  `OTHER` fact (fallback), node types are limited to **`Symptom` / `Medication` / `Other`**, and
  **zero graph edges and zero intelligence-engine / Health-Thread outputs are produced** — the
  auto-linker (`insert_edge`), the five intelligence engines, and the state machine are **not wired
  into this path**.

Headline current-implementation totals (deterministic, both modes summed):

| Metric | Total across all 5 cases, both modes |
|---|---|
| Raw events (= C2 vault rows) | **452** |
| C4 facts extracted | **459** |
| C5 evidence links (PRIMARY) | **459** |
| C6 nodes after dedup | **427** |
| C6 edges | **0** |

---

## 1. Pipeline model used for prediction

### 1.1 C2 — Raw Context Vault
Append-only, 1 vault row per ingested raw event. **Vault rows = raw event count** (no dedup at C2).

### 1.2 C3 → C4 routing (`dispatcher.decide_route`)
```
fhir                              -> TEMPORAL_FHIR
mime in {jpeg,png,tiff,pdf}       -> TEMPORAL_OCR
source_type in {manual_text,sms,device} -> DRAMATIQ_TEXT   <-- rule-based extractor
everything else                   -> TEMPORAL_DOCUMENT
```
Because `seed.sh` forces `source_type='manual_text'` for **every** event, all events take
`DRAMATIQ_TEXT`. (If native source types — `lab_result`, `manual_input`, `imaging`, … — were used
instead, most events would fall through to `TEMPORAL_DOCUMENT`, which has no implemented worker in
this path, and would yield **0 facts**. The seed harness is what makes the text extractor fire at
all.)

### 1.3 C4 — `TextFactExtractor` (rule-based; `extractor.py`)
- **Symptom keywords (10):** `headache, nausea, fatigue, dizziness, pain, fever, cough,
  chest pain, shortness of breath, insomnia`. Each is matched with `str.find` → **first occurrence
  only**, so at most **one fact per keyword per event** regardless of repeats. `pain` is a substring
  and also matches inside `chest pain`, so an event containing "chest pain" yields **both** a `pain`
  and a `chest_pain` symptom fact.
- **Medication keywords (4):** `ibuprofen, paracetamol, aspirin, metformin`.
- **Fallback:** if no keyword matches, **exactly one** `OTHER` fact is emitted with
  `normalized_key = sha256(text)[:16]` (i.e. unique per distinct text).
- Negation (`is_negated`) is flagged but **does not suppress** the fact.
- `quality_flag`: symptom conf 0.90 / medication 0.92 → `CLEAN`; OTHER conf 0.50 → `REQUIRES_REVIEW`.

So per event: facts = (#distinct symptom keywords present) + (#distinct medication keywords present),
or **1** if that sum is 0.

### 1.4 C5 — Evidence (`tasks.py` → `EvidenceService.link_fact`)
Exactly **one `PRIMARY` evidence link per fact** (`confidence_basis = EXTRACTION_MODEL`). This
satisfies the "no orphan claims" rule (every fact has ≥1 evidence link). **C5 links = C4 facts.**

### 1.5 C6 — Graph nodes (`tasks.FACT_TYPE_TO_NODE_TYPE`, `repository.upsert_node`)
`upsert_node` dedups on **(patient_id, normalized_key)**. Fact→node map actually reachable from the
extractor:

| fact_type emitted | node_type |
|---|---|
| `symptom` | `Symptom` |
| `medication` | `Medication` |
| `other` | `Other` |

(The map also defines `ConditionHypothesis, LabResult, Procedure, VitalSign, …`, but the extractor
never emits those fact types, so **those node types never appear** in current implementation.)
Dedup behaviour:
- `Symptom` / `Medication`: many facts collapse to one node per normalized key (e.g. all `fever`
  mentions → 1 node).
- `Other`: `normalized_key` is a hash of the full text → effectively **unique**, so OTHER facts
  do **not** dedup unless two events have byte-identical text. (In this corpus, OTHER distinct =
  OTHER facts in every case — no collisions.)
- **nodes < facts** purely because the handful of symptom/medication keywords repeat.

### 1.6 C6 — Edges
`insert_edge` exists in `repository.py` but **has no caller anywhere in `backend/`**. The only
edge-touching task, `score_graph_edges_task`, merely *rescore* edges returned by
`get_edges_needing_rescore` — of which there are none. **Current-implementation edges = 0.**
The design (`knowledge_graph.md`) intends an auto-linking worker creating `co_occurs_with`,
`temporally_precedes`, `may_explain`, `contradicts`, etc.; that worker is unbuilt.

### 1.7 Intelligence engines & Health Thread
No pattern/temporal/confounder/contradiction/missing-data engine and no Health Thread state machine
were found in the processing path (`grep` across `backend/**/*.py` returns nothing). Sections F and G
are therefore **design-expected only**; current-implementation produces none of these objects.

---

## 2. Methodology & assumptions (read this to audit the numbers)

1. **Event counts** are ground truth: taken from `manifest.yaml` and confirmed by counting files in
   each `raw_events/` directory. Event-type breakdowns are from the filename suffix
   (`NNNNN_<event_type>.json`).
2. **Current-implementation facts/nodes are deterministic** and were computed by an offline script
   that reproduces, line-for-line, (a) `seed.sh` text selection (`original.event` else
   `json.dumps(raw_payload)`), (b) the `TextFactExtractor` keyword logic, and (c) `upsert_node`
   dedup. They are not estimates. The script was a transient analysis aid and is not committed.
3. **C5 = C4** by construction (one PRIMARY link per fact).
4. **Current-implementation edges = 0** and **engine/thread outputs = 0**, by code inspection
   (no caller for `insert_edge`; no engine/state-machine modules).
5. **Design-expected numbers are estimates**, presented as ranges with reasoning. Assumptions:
   - Design extractor emits **≥1 structured fact per event**; multi-finding events (lab panels,
     multi-symptom notes, exams) emit **>1**. Assumed mean **1.2–1.6 facts/event**.
   - Design dedup is by clinical entity identity. Labs are the biggest dedup lever: the same analyte
     measured repeatedly over time → one `lab_result` node tracked over time (or one node per
     analyte). Assumed design node yield **≈ 45–70% of design facts**, lower in lab-heavy cases.
   - Design edges cannot be point-predicted; an order-of-magnitude estimate is given from node count
     and narrative density.
6. **Safety invariant asserted as a prediction, not a measurement:** no `diagnoses`/diagnosis edge
   type and no final-diagnosis assertion may be produced, in either track. `may_explain` is the
   strongest permitted causal edge (`knowledge_graph.md` §Safety constraints).
7. **No `answer_key/`** was read (absent by design); the clinical narratives below are summarized
   from the `timeline_*` event text only and are **not** diagnostic conclusions.

---

## 3. Benchmark event-type → design node-type reference

Used for the design-expected breakdowns in the per-case sections.

| Benchmark event-type suffix(es) | Design fact_type | Design node_type |
|---|---|---|
| `obs_laboratory`, `timeline_test`, `obs_serology`, `obs_microbiology*`, `obs_infectious_testing`, `obs_csf`, `obs_immunology`, `obs_stool_test`, `obs_classification_data` | lab_result | `lab_result` |
| `obs_imaging`, `timeline_imaging`, `obs_imaging_endoscopy`, `obs_cardiac_mri`, `obs_echocardiography`, `obs_nuclear_medicine`, `obs_ecg`, `obs_laboratory_imaging` | finding | `imaging_result` |
| `obs_symptom`, `timeline_symptom` | symptom | `symptom` |
| `obs_treatment`, `obs_medications`, `obs_medication_change`, `timeline_treatment*`, `obs_treatment_response` | medication / finding | `medication` (+ treatment-response finding) |
| `obs_pathology`, `obs_procedure_pathology`, `obs_immunohistochemistry` | finding | `lab_result` / `procedure` (pathology) |
| `obs_procedure`, `obs_procedure_imaging` | procedure | `procedure` |
| `obs_genetic`, `obs_genetic_panel`, `obs_genetic_family` | finding / family_history | `lab_result` / `family_history` |
| `obs_exam`, `obs_neurologic_exam`, `obs_vitals_exam`, `obs_clinical_assessment`, `obs_workup_summary`, `obs_clinical_course`, `timeline_diagnostic_framework` | finding / vital_sign | `hypothesis` / `vital_sign` / `document` |
| `obs_history`, `timeline_history`, `obs_negative_history` | finding | `condition` / `document` |
| `obs_care_visit`, `timeline_care_visit`, `obs_care_plan` | — | `visit` / `pending_item` |
| `obs_outcome`, `timeline_outcome` | finding | `observation` |
| `obs_demographics`, `obs_anthropometric` | social_history / vital_sign | `social_factor` / `vital_sign` |

---

## 4. Per-case predictions

For every case, **A–E numbers in the "current implementation" tables are deterministic**;
**design-expected numbers are flagged estimates**. F–G are design-expected qualitative only.

---

### CASE C01 — chronic multi-year systemic inflammatory/GI course

**Narrative (from `timeline_*` text, no diagnosis asserted):** childhood-onset loose stools →
recurrent fever + migratory asymmetric joint symptoms driving repeated evaluation → inflammation &
fever persisting *despite* prednisone + methotrexate and further immunomodulators → marked
deterioration (edema, explosive diarrhea, >45 kg unintentional weight loss) → extensive
labs/imaging/pathology → symptoms resolved after **targeted antimicrobial therapy**. Lab-dominated
(20 lab events/mode).

**A. Event inventory**

| event_type | blind (51) | full (56) |
|---|---|---|
| obs_laboratory | 20 | 20 |
| obs_symptom | 10 | 10 |
| obs_treatment | 7 | 8 |
| timeline_symptom | 2 | 2 |
| timeline_treatment_response | 2 | 2 |
| obs_imaging | 2 | 2 |
| obs_exam | 2 | 2 |
| timeline_history | 1 | 1 |
| timeline_care_visit | 1 | 1 |
| obs_procedure | 1 | 1 |
| obs_pathology | 1 | 1 |
| obs_laboratory_imaging | 1 | 1 |
| obs_demographics | 1 | 1 |
| timeline_test / timeline_outcome / obs_procedure_pathology / obs_outcome | — | 1 each |

C2 vault rows = 51 (blind) / 56 (full).

**B–E. Current-implementation (deterministic)**

| Mode | C4 facts | fact_types | C5 links | C6 nodes | node_types | edges | dedup ratio (nodes/facts) |
|---|---|---|---|---|---|---|---|
| blind | 51 | other 45, symptom 6 | 51 | 47 | Other 45, Symptom 2 | 0 | 0.92 |
| full  | 56 | other 50, symptom 6 | 56 | 52 | Other 50, Symptom 2 | 0 | 0.93 |

Symptom nodes = {`fever`, `pain`} both modes (keyword hits inside JSON dumps / timeline text; `fever`
hit 4×, `pain` 2× → dedup to 2 nodes). No medication keyword (prednisone/methotrexate aren't in the
4-medication list). 0 multi-fact events.

**Design-expected (estimates):**
- C4 facts ≈ **65–90** (blind) / **72–100** (full) — lab panels and multi-symptom timeline notes
  expand >1 fact/event.
- C6 nodes ≈ **35–50** — heavy lab dedup (ESR/CRP etc. measured repeatedly → one node per analyte);
  node types: `lab_result` (largest), `symptom`, `medication` (prednisone, methotrexate, antimicrobial),
  `imaging_result`, `procedure`, `condition`/`hypothesis`, `visit`.
- C6 edges ≈ **40–80**: `co_occurs_with` (fever↔joint symptoms↔inflammatory labs),
  `temporally_precedes` (symptom onset → labs), `may_explain` (antimicrobial response → symptom
  resolution), `resolves` (treatment → outcome). **No diagnosis edge.**

**F. Intelligence engines (design-expected):**
- *Pattern:* recurrent fever + migratory joint symptoms co-clustering with elevated inflammatory
  markers; GI symptoms persisting across years.
- *Temporal:* symptom flares preceding/parallel to inflammatory-marker rises; non-response to
  immunosuppression then **response after antimicrobial** (strong temporal "treatment → resolution").
- *Confounder:* steroid/immunomodulator therapy as a confounder of marker trends.
- *Contradiction:* "persisted despite immunosuppression" vs "resolved on antimicrobial" — preserved,
  not resolved.
- *Missing-data:* in `blind` mode the decisive `timeline_test`/`timeline_outcome`/`procedure_pathology`
  events are absent — the engine would flag exactly the gap that `full` mode fills (+5 events).

**G. Health Thread (design-expected):** ~**2–3** threads — (1) chronic diarrhea/GI + weight-loss
thread, (2) recurrent fever + inflammatory/joint thread, possibly (3) systemic deterioration thread.
Likely states: `chronic_monitoring` / `active_unresolved` through most of the timeline, moving to
`explained`→`closed` only in `full` mode where an outcome event exists. Per the state machine, a
single normal test could **not** close these.

---

### CASE C02 — multi-system (cardiac → neuro-cognitive → renal/hematologic) decline, late metabolic response

**Narrative:** isolated acute pericarditis → diastolic hypertension → confusion, insomnia, visual
hallucinations, visual impairment, reasoning difficulty → severe cognitive/motor/language/gait
decline → TMA-like syndrome **without improvement on complement-directed therapy** → multi-domain
improvement after **targeted vitamin/cofactor therapy**; genetic panel performed. Very lab-heavy
(18–23 lab events).

**A. Event inventory (top types)**

| event_type | blind (47) | full (59) |
|---|---|---|
| obs_laboratory | 18 | 23 |
| obs_pathology | 4 | 4 |
| obs_symptom | 3 | 3 |
| obs_imaging | 3 | 3 |
| obs_treatment | 2 | 4 |
| timeline_test | 2 | 3 |
| obs_neurologic_exam | 2 | 2 |
| obs_history / timeline_history / obs_exam | 2 each | 2 each |
| timeline_symptom | 2 | 2 |
| obs_genetic_panel | 1 | 1 |
| (full adds) obs_genetic, obs_clinical_course, timeline_outcome, obs_outcome | — | 1 each |

C2 vault rows = 47 / 59.

**B–E. Current-implementation (deterministic)**

| Mode | C4 facts | fact_types | C5 links | C6 nodes | node_types | edges | dedup ratio |
|---|---|---|---|---|---|---|---|
| blind | 47 | other 45, symptom 2 | 47 | 46 | Other 45, Symptom 1 | 0 | 0.98 |
| full  | 59 | other 57, symptom 2 | 59 | 58 | Other 57, Symptom 1 | 0 | 0.98 |

Only symptom node = {`insomnia`} (2 hits → 1 node). Highest dedup ratio in the corpus (≈0.98):
almost everything is a unique OTHER fallback; the keyword matcher captures essentially none of this
case's neuro/renal/hematologic vocabulary.

**Design-expected (estimates):**
- C4 facts ≈ **60–85** (blind) / **75–105** (full).
- C6 nodes ≈ **38–55** — strong lab dedup; node types `lab_result`, `symptom` (confusion,
  hallucination, gait decline, insomnia), `imaging_result`, `medication` (complement-directed,
  vitamin/cofactor), `condition`/`hypothesis` (pericarditis, hypertension), `family_history`/`finding`
  (genetic panel).
- C6 edges ≈ **45–85**: `co_occurs_with` across cardiac/neuro/renal clusters, `temporally_precedes`
  (pericarditis → hypertension → neuro decline), `may_explain` (metabolic/cofactor → multi-system
  improvement), `contradicts` (no improvement on complement therapy vs improvement on cofactor).

**F. Intelligence engines (design-expected):**
- *Pattern:* multi-system co-occurrence (cardiac + neuro + renal + hematologic).
- *Temporal:* clear staged precedence pericarditis → hypertension → cognitive/motor decline; sharp
  treatment-response inflection at cofactor therapy.
- *Confounder:* genetic/metabolic substrate as a common confounder explaining several "patterns".
- *Contradiction:* therapy non-response vs response — preserved.
- *Missing-data:* `blind` mode lacks `obs_genetic`/`clinical_course`/`outcome` (+12 events in `full`);
  engine flags the genetic/outcome gap as the highest-value missing context.

**G. Health Thread (design-expected):** ~**3–4** threads (cardiac, neuro-cognitive, renal/hematologic
TMA-like, metabolic). States span `active_unresolved` → `waiting_for_result` (genetic panel) →
`escalated` (severe decline) → `explained`/`chronic_monitoring`. `closed` only plausible in `full`
mode with the outcome event.

---

### CASE C03 — acute febrile inflammatory syndrome, steroid-responsive

**Narrative:** high-grade evening fevers + diffuse arthralgia + fatigue + sore throat → fevers and
inflammatory markers **persist despite broad-spectrum antibiotics** → a named clinical classification
framework reviewed with multiple criteria met → **rapid improvement (fever, ferritin, liver enzymes)
after systemic corticosteroids**. Smallest blind case (36 events).

**A. Event inventory (top types)**

| event_type | blind (36) | full (49) |
|---|---|---|
| obs_laboratory | 17 | 20 |
| obs_exam | 3 | 3 |
| obs_symptom | 2 | 2 |
| obs_serology | 2 | 2 |
| timeline_test | 2 | 2 |
| obs_treatment | 1 | 3 |
| obs_outcome | — | 2 |
| obs_classification_data | — | 4 |
| (singletons) infectious_testing, microbiology, imaging, negative_history, treatment_response, demographics, timeline_* | 1 each | 1 each |

C2 vault rows = 36 / 49.

**B–E. Current-implementation (deterministic)**

| Mode | C4 facts | fact_types | C5 links | C6 nodes | node_types | edges | dedup ratio |
|---|---|---|---|---|---|---|---|
| blind | 37 | other 30, symptom 7 | 37 | 33 | Other 30, Symptom 3 | 0 | 0.89 |
| full  | 50 | other 40, symptom 10 | 50 | 43 | Other 40, Symptom 3 | 0 | 0.86 |

Symptom nodes = {`fatigue`, `fever`, `cough`} (fever hit 4× blind / 7× full → still 1 node). This
case has the corpus's **lowest dedup ratio** (≈0.86 full) because `fever` recurs most — the strongest
keyword-dedup signal in the corpus. 1 multi-fact event per mode (an event containing two distinct
symptom keywords).

**Design-expected (estimates):**
- C4 facts ≈ **48–65** (blind) / **62–85** (full).
- C6 nodes ≈ **28–42** — lab dedup; node types `lab_result` (incl. ferritin, liver enzymes,
  serology), `symptom` (fever, arthralgia, sore throat, fatigue), `medication` (antibiotics,
  corticosteroids), `hypothesis`/`document` (classification framework).
- C6 edges ≈ **35–65**: `co_occurs_with` (fever↔arthralgia↔inflammatory markers),
  `temporally_precedes` (antibiotic non-response → steroid response), `resolves` (steroids → marker
  normalization), `may_explain`.

**F. Intelligence engines (design-expected):**
- *Pattern:* tight co-occurrence cluster of evening fever + arthralgia + elevated ferritin/inflammatory
  markers.
- *Temporal:* antibiotic-refractory phase → rapid steroid-responsive inflection.
- *Confounder:* antibiotic exposure as confounder of marker trends.
- *Contradiction:* "persisted despite antibiotics" vs "rapid improvement on steroids".
- *Missing-data:* `blind` lacks the `classification_data` (×4) and `outcome` (×2) events — the
  engine flags the classification/outcome gap that `full` mode supplies (+13 events).

**G. Health Thread (design-expected):** likely **1 dominant** febrile-inflammatory thread
(fever-of-unknown-origin style), possibly a second arthralgia thread. States: `active_unresolved` →
`waiting_for_result` → `explained` (criteria met + steroid response) in `full` mode.

---

### CASE C04 — post-exposure neuro/myelopathy with bowel-bladder involvement, steroid-responsive

**Narrative:** insect bite → bullseye-like rash → constipation + urinary difficulty → sudden
resolving chest pain then **progressive right lower limb weakness** → MRI → **IV methylprednisolone →
improved exam + interval MRI resolution** → rehabilitation recovery (walking, bowel/bladder). Most
neuro-exam-heavy case (7 `obs_neurologic_exam`).

**A. Event inventory (top types)**

| event_type | blind (36) | full (46) |
|---|---|---|
| obs_laboratory | 10 | 10 |
| obs_neurologic_exam | 7 | 7 |
| obs_imaging | 4 | 5 |
| obs_symptom | 3 | 3 |
| obs_treatment | 2 | 3 |
| timeline_symptom | 2 | 2 |
| obs_outcome | — | 3 |
| (singletons) infectious_testing, vitals_exam, history, demographics, timeline_test/history/neurologic_progression/treatment_response | 1 each | 1 each (+full: microbiology_immunology, immunology, csf) |

C2 vault rows = 36 / 46.

**B–E. Current-implementation (deterministic)**

| Mode | C4 facts | fact_types | C5 links | C6 nodes | node_types | edges | dedup ratio |
|---|---|---|---|---|---|---|---|
| blind | 39 | other 32, symptom 6, medication 1 | 39 | 35 | Other 32, Symptom 2, Medication 1 | 0 | 0.90 |
| full  | 49 | other 42, symptom 6, medication 1 | 49 | 45 | Other 42, Symptom 2, Medication 1 | 0 | 0.92 |

Symptom nodes = {`pain`, `chest_pain`} (each hit 3× → "chest pain" text triggers both keywords →
this is the source of the corpus's multi-fact events: **3 multi-fact events/mode**). Medication node =
{`aspirin`} (1 hit — likely inside a JSON dump value, **not** the actual therapy methylprednisolone,
which isn't a keyword). This is a good example of a **false-ish positive**: `aspirin` is captured but
the clinically central drug is missed.

**Design-expected (estimates):**
- C4 facts ≈ **45–62** (blind) / **55–78** (full).
- C6 nodes ≈ **30–45** — node types `imaging_result` (MRI series — dedup across repeat MRIs),
  `symptom` (limb weakness, bowel/bladder, chest pain, rash), `lab_result`, `medication`
  (methylprednisolone), `procedure`/`finding` (CSF, serology in full), `condition`/`hypothesis`.
- C6 edges ≈ **35–60**: `temporally_precedes` (bite/rash → neuro symptoms → MRI finding →
  steroid → resolution), `co_occurs_with` (limb weakness ↔ bowel/bladder ↔ MRI lesion),
  `resolves` (steroid → exam/MRI improvement), `may_explain` (exposure → neuro syndrome). **No
  diagnosis edge.**

**F. Intelligence engines (design-expected):**
- *Pattern:* exposure → dermatologic → neurologic progression cluster.
- *Temporal:* strong ordered chain (bite → rash → autonomic/limb symptoms → imaging lesion →
  treatment → recovery) — the clearest `temporally_precedes` case.
- *Confounder:* steroid effect confounding MRI-resolution interpretation.
- *Contradiction:* "sudden resolving chest pain" vs "progressive weakness" (transient vs progressive).
- *Missing-data:* `blind` lacks `csf`/`immunology`/`microbiology_immunology`/`outcome` (+10 events);
  engine flags the CSF/serology + outcome gap.

**G. Health Thread (design-expected):** ~**2–3** threads — (1) myelopathy/limb-weakness thread
(primary), (2) bowel/bladder dysfunction thread, (3) exposure/rash thread. States: `active_unresolved`
→ `escalated` (progressive weakness) → `waiting_for_result` (MRI/CSF) → `explained`→`closed`/
`chronic_monitoring` after rehab in `full` mode.

---

### CASE C05 — chronic GI (diarrhea/weight-loss) workup with cardiac involvement in full mode

**Narrative:** abdominal pain + diarrhea + significant weight loss begin a prolonged workup →
severe diarrhea (>10×/day), orthostatic presyncope, fatigue, reduced exercise tolerance → extensive
workup; in `full` mode a **cardiac workup appears** (echocardiography ×4, cardiac MRI ×2, nuclear
medicine, ECG) alongside stool tests, pathology, and genetics. Smallest blind case (27 events); the
two modes diverge most here (27 → 45, +18 events, +67%).

**A. Event inventory (top types)**

| event_type | blind (27) | full (45) |
|---|---|---|
| timeline_test | 3 | 5 |
| obs_symptom | 3 | 3 |
| timeline_symptom | 2 | 2 |
| obs_stool_test | 2 | 2 |
| obs_care_visit | 2 | 2 |
| obs_echocardiography | 0 | 4 |
| obs_pathology | 1 | 3 |
| obs_cardiac_mri | 0 | 2 |
| (full-only singletons) obs_nuclear_medicine, obs_ecg, obs_immunohistochemistry, obs_genetic, obs_genetic_family, obs_laboratory, obs_treatment, timeline_treatment_family | 0 | 1 each |
| (shared singletons) workup_summary, procedure_imaging, procedure, medications, medication_change, imaging_endoscopy, imaging, history, demographics, clinical_assessment, care_plan, anthropometric, timeline_imaging, timeline_care_visit | 1 each | 1 each |

C2 vault rows = 27 / 45.

**B–E. Current-implementation (deterministic)**

| Mode | C4 facts | fact_types | C5 links | C6 nodes | node_types | edges | dedup ratio |
|---|---|---|---|---|---|---|---|
| blind | 27 | other 22, symptom 4, medication 1 | 27 | 25 | Other 22, Symptom 2, Medication 1 | 0 | 0.93 |
| full  | 45 | other 40, symptom 4, medication 1 | 45 | 43 | Other 40, Symptom 2, Medication 1 | 0 | 0.96 |

Symptom nodes = {`pain`, `fatigue`} (each 2×); medication node = {`aspirin`}. 0 multi-fact events.

**Design-expected (estimates):**
- C4 facts ≈ **33–48** (blind) / **55–78** (full).
- C6 nodes ≈ **24–38** (blind) / **35–52** (full) — node types `lab_result`/`finding` (stool tests,
  pathology, IHC, genetics), `imaging_result` (endoscopy, echo, cardiac MRI, nuclear), `symptom`
  (diarrhea, abdominal pain, presyncope, fatigue), `vital_sign` (anthropometric, orthostatics),
  `visit`/`pending_item` (care visits, care plan), `family_history` (genetic_family).
- C6 edges ≈ **30–60** (full): `co_occurs_with` (GI cluster; cardiac cluster), `temporally_precedes`
  (GI symptoms → workup → cardiac findings), `may_explain` (systemic process linking GI + cardiac),
  `part_of`. **No diagnosis edge.**

**F. Intelligence engines (design-expected):**
- *Pattern:* GI symptom cluster (diarrhea/pain/weight-loss) + (full mode) cardiac cluster — a
  two-organ-system pattern is the headline.
- *Temporal:* prolonged GI workup preceding cardiac findings; orthostatic presyncope correlating with
  volume loss from diarrhea.
- *Confounder:* dehydration/volume depletion as confounder for presyncope and some cardiac measures.
- *Contradiction:* potential GI-vs-cardiac primary-driver ambiguity — preserved, not resolved.
- *Missing-data:* **the most striking case** — `blind` mode entirely lacks the cardiac workup
  (echo/cardiac-MRI/nuclear/ECG) and genetics present in `full`. The missing-data engine in `blind`
  mode would flag "no cardiac evaluation despite presyncope/exercise intolerance" — and `full` mode
  is essentially the answer to that gap (+18 events).

**G. Health Thread (design-expected):** ~**2–3** threads — (1) chronic GI/diarrhea + weight-loss
thread, (2) cardiac thread (full mode), (3) constitutional/autonomic (presyncope, exercise
intolerance) thread. States: `active_unresolved` → `waiting_for_result` (extensive pending workup,
care-plan/care-visit events imply `pending_item`s) → `chronic_monitoring`.

---

## 5. Consolidated cross-case tables

### 5.1 Current-implementation-expected (DETERMINISTIC)

| Case / mode | Events (C2) | C4 facts | C5 links | C6 nodes | Symptom | Medication | Other | C6 edges |
|---|---|---|---|---|---|---|---|---|
| C01 / blind | 51 | 51 | 51 | 47 | 2 | 0 | 45 | 0 |
| C01 / full  | 56 | 56 | 56 | 52 | 2 | 0 | 50 | 0 |
| C02 / blind | 47 | 47 | 47 | 46 | 1 | 0 | 45 | 0 |
| C02 / full  | 59 | 59 | 59 | 58 | 1 | 0 | 57 | 0 |
| C03 / blind | 36 | 37 | 37 | 33 | 3 | 0 | 30 | 0 |
| C03 / full  | 49 | 50 | 50 | 43 | 3 | 0 | 40 | 0 |
| C04 / blind | 36 | 39 | 39 | 35 | 2 | 1 | 32 | 0 |
| C04 / full  | 46 | 49 | 49 | 45 | 2 | 1 | 42 | 0 |
| C05 / blind | 27 | 27 | 27 | 25 | 2 | 1 | 22 | 0 |
| C05 / full  | 45 | 45 | 45 | 43 | 2 | 1 | 40 | 0 |
| **TOTAL** | **452** | **459** | **459** | **427** | **20** | **6** | **403** | **0** |

Notes: facts ≥ events only in C03/C04 (multi-symptom-keyword events). `Symptom`/`Medication` columns
are **distinct node counts** (post-dedup). The 6 medication nodes are all `aspirin` (likely incidental
JSON-string matches), not the cases' actual therapies — a known limitation of the keyword extractor.

### 5.2 Design-expected (ESTIMATES — ranges, midpoint in parentheses)

| Case / mode | Events | Design facts | Design nodes | Design edges | Dominant design node types |
|---|---|---|---|---|---|
| C01 / blind | 51 | 65–90 (77) | 35–50 (42) | 40–80 (55) | lab_result, symptom, medication, imaging_result |
| C01 / full  | 56 | 72–100 (86) | 38–54 (46) | 45–85 (62) | + outcome, pathology procedure |
| C02 / blind | 47 | 60–85 (72) | 38–55 (46) | 45–85 (62) | lab_result, symptom, imaging_result, hypothesis |
| C02 / full  | 59 | 75–105 (90) | 42–60 (50) | 50–95 (70) | + genetic finding, outcome |
| C03 / blind | 36 | 48–65 (56) | 28–42 (34) | 35–65 (48) | lab_result, symptom, medication |
| C03 / full  | 49 | 62–85 (73) | 32–46 (38) | 40–75 (55) | + classification document, outcome |
| C04 / blind | 36 | 45–62 (53) | 30–45 (37) | 35–60 (45) | imaging_result, symptom, lab_result |
| C04 / full  | 46 | 55–78 (66) | 34–50 (41) | 40–70 (52) | + CSF/serology finding, outcome |
| C05 / blind | 27 | 33–48 (40) | 24–38 (30) | 25–50 (37) | lab_result, symptom, visit/pending_item |
| C05 / full  | 45 | 55–78 (66) | 35–52 (43) | 30–60 (45) | + imaging (echo/cardiac MRI), genetic |
| **TOTAL** | **452** | **580–796 (~679)** | **336–492 (~407)** | **385–725 (~531)** | — |

### 5.3 Divergence summary (design vs current implementation)

| Dimension | Current implementation | Design intent | Why they diverge |
|---|---|---|---|
| Extractor | 10 symptom + 4 medication keywords + OTHER fallback | LLM/NER clinical extractor | Placeholder MVP extractor |
| Facts/event | ~1.0 (mostly OTHER) | 1.2–1.6 (structured) | Keyword matcher can't parse structured labs/imaging |
| Node types | only Symptom / Medication / Other | 25+ clinical/care/context types | Extractor never emits non-symptom/med fact types |
| Routing | 100% text path (seed forces `manual_text`) | FHIR/OCR/document/text by source | Seed harness override |
| Edges | **0** (no auto-linker caller) | co_occurs_with / temporally_precedes / may_explain / … | Auto-linker not built |
| Intelligence engines | none | 5 engines | Not implemented |
| Health Threads | none | per-concern threads + state machine | Not implemented |
| Safety: no diagnosis edge | satisfied (no edges at all) | satisfied (`may_explain` is the ceiling) | Invariant holds in both |

---

## 6. Biggest prediction uncertainties

1. **Exact text fed to the extractor.** `tasks.py` reads `data["_raw_text"]` or
   `data["source_metadata"]["text"]`, but `seed.sh` sends the text under `metadata.text` (and a
   base64 `raw_data`). If the ingestion worker does **not** surface that text as `_raw_text` /
   `source_metadata.text`, the extractor would see an **empty string** → every event becomes a single
   OTHER fact with `normalized_key = sha256("")` (one shared key) → **all OTHER facts in a
   case/user would collapse to a single node**. That would drop C6 node counts dramatically (to
   ≈ distinct-symptom + 1). My deterministic numbers assume the event text *does* reach the
   extractor (faithful to `seed.sh`'s intent). **This is the single largest swing factor.**
2. **Per-patient vs per-mode dedup.** Each case has one `synthetic_user_id`, but both modes share it.
   If both modes are seeded into the same user, symptom/medication/OTHER nodes would dedup **across
   modes**, not within — changing totals. I reported per-mode figures; cross-mode merging would
   reduce the all-cases node total below 427.
3. **Design-track facts/nodes/edges are genuine estimates.** The ranges assume a competent structured
   extractor and a built auto-linker; both are unbuilt. Edge counts especially are order-of-magnitude.
4. **`aspirin`/`pain` matches are partly incidental.** Several keyword hits come from JSON-dump field
   values rather than the clinical event proper; the 6 `aspirin` medication nodes likely do not
   correspond to aspirin therapy. Treat current-impl symptom/medication node identities as
   approximate even though their counts are deterministic.
5. **Mode divergence is informative, not noise.** `full_results_no_final_label` consistently adds
   test/outcome/pathology/genetic events that `blind_pre_diagnosis` omits. This is precisely the
   surface the design's **Missing-Data engine** is meant to flag — a good qualitative validation
   target once the engine exists.

---

*End of prediction report. This document is an auditable forward prediction; compare against measured
platform output separately.*
