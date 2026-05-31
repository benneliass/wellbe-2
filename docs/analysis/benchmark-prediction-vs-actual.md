# Benchmark Prediction vs. Actual — Cross-Reference Report

> **Purpose.** This document diffs the *forward prediction* in
> [`benchmark-expected-results.md`](./benchmark-expected-results.md) against the **measured live
> state** of the WellBe local Kind cluster (namespace `wellbe`, Postgres `postgres-0`, db `wellbe`).
>
> All actual numbers were obtained by **read-only SQL** (`SELECT` / `COUNT` / `GROUP BY`) executed via
> `kubectl exec -n wellbe postgres-0 -- psql -U wellbe -d wellbe`. No data was mutated, no re-seed, no
> pod restart. The exact queries and raw outputs are in the [Appendix](#appendix--raw-sql--outputs).
>
> Date measured: 2026-05-31.

---

## 0. Headline verdict

- **The deterministic, current-implementation prediction was essentially perfect** for the data that
  is actually present. Every per-case **event**, **fact** (by type), **node** (by type *and* identity),
  and **edge** count matches the prediction's `blind_pre_diagnosis` figures **exactly**.
- **Only `blind_pre_diagnosis` mode is seeded.** The prediction's headline totals (452 events / 459
  facts / 427 nodes) summed *both* modes. The cluster contains only the blind half, so the right
  comparison is against the prediction's per-case **blind** rows — and those match to the unit.
- **The text-path / "empty-text collapse" hypothesis (prediction uncertainty #1) is REFUTED.** The
  seeded text *does* reach the extractor. OTHER nodes have **174 distinct `normalized_key`s out of
  174** (all unique) and **zero** nodes carry the empty-string hash. Node `display_label`s contain
  real clinical prose.
- **One divergence of substance:** C5 evidence-link *rows* are **~2× the fact count** (not 1:1 as
  predicted) because the 197 benchmark events were **processed twice** by the C4 worker. Facts and
  nodes are idempotent and stayed at 1×; evidence links are not, leaving **201 orphan links** (links
  whose source fact no longer exists). The *invariant* the prediction asserted (every fact has exactly
  one PRIMARY link) still holds — `valid_links = 204 = fact_count`.
- **One expected extra:** a **stray manual-test patient** (`7e47287f…`, 1 event: *"persistent fever
  and severe joint pain … taking ibuprofen 400mg"*) → 3 facts / 3 nodes (`fever`, `pain`, `ibuprofen`).

---

## A. Per-case predicted (current-impl, **blind**) vs actual

Each benchmark case maps to one `synthetic_user_id` (= `patient_id`):

| Case | patient_id | mode present |
|---|---|---|
| C01 | `61b3a25e-867f-50f2-9e6f-0483ec54e245` | blind only |
| C02 | `00697626-0025-5d87-9576-20367e50c0e1` | blind only |
| C03 | `cd2e1041-bc5b-5c4e-adae-1786c640079e` | blind only |
| C04 | `23b1d00e-65db-530a-9d4b-5bde4dc39a3f` | blind only |
| C05 | `8e2138f0-a50a-5f54-a42e-719254a5fafd` | blind only |
| (stray) | `7e47287f-7325-4477-8bae-8040ddf21e46` | manual test |

### A.1 C2 vault events

| Case | Predicted (blind) | Actual | Δ | Match |
|---|---|---|---|---|
| C01 | 51 | 51 | 0 | ✅ |
| C02 | 47 | 47 | 0 | ✅ |
| C03 | 36 | 36 | 0 | ✅ |
| C04 | 36 | 36 | 0 | ✅ |
| C05 | 27 | 27 | 0 | ✅ |
| **5-case total** | **197** | **197** | **0** | ✅ |
| stray | — | 1 | +1 | (extra) |
| **grand total** | — | **198** | — | — |

### A.2 C4 extracted facts

| Case | Predicted (blind) | Actual | Δ | Match |
|---|---|---|---|---|
| C01 | 51 | 51 | 0 | ✅ |
| C02 | 47 | 47 | 0 | ✅ |
| C03 | 37 | 37 | 0 | ✅ |
| C04 | 39 | 39 | 0 | ✅ |
| C05 | 27 | 27 | 0 | ✅ |
| **5-case total** | **201** | **201** | **0** | ✅ |
| stray | — | 3 | +3 | (extra) |
| **grand total** | — | **204** | — | — |

### A.3 C5 evidence links

| Case | Predicted (blind, =facts) | Actual (rows) | Actual valid (1/fact) | Δ rows | Match |
|---|---|---|---|---|---|
| C01 | 51 | 102 | 51 | +51 | ⚠️ rows 2×; invariant ✅ |
| C02 | 47 | 94 | 47 | +47 | ⚠️ rows 2×; invariant ✅ |
| C03 | 37 | 74 | 37 | +37 | ⚠️ rows 2×; invariant ✅ |
| C04 | 39 | 78 | 39 | +39 | ⚠️ rows 2×; invariant ✅ |
| C05 | 27 | 54 | 27 | +27 | ⚠️ rows 2×; invariant ✅ |
| **5-case total** | **201** | **402** | **201** | **+201** | ⚠️ |
| stray | — | 3 | 3 | +3 | (extra, 1× — processed once) |
| **grand total** | — | **405** | **204** | — | — |

> The prediction's "C5 = C4, one PRIMARY link per fact" is correct **as an invariant** —
> `valid_links (204) == fact_count (204)` — but the **table holds ~2× rows** for the benchmark cases
> because of duplicate C4 processing (see §D).

### A.4 C6 nodes

| Case | Predicted (blind) | Actual | Δ | Match |
|---|---|---|---|---|
| C01 | 47 | 47 | 0 | ✅ |
| C02 | 46 | 46 | 0 | ✅ |
| C03 | 33 | 33 | 0 | ✅ |
| C04 | 35 | 35 | 0 | ✅ |
| C05 | 25 | 25 | 0 | ✅ |
| **5-case total** | **186** | **186** | **0** | ✅ |
| stray | — | 3 | +3 | (extra) |
| **grand total** | — | **189** | — | — |

### A.5 C6 edges

| Case | Predicted | Actual | Δ | Match |
|---|---|---|---|---|
| all cases + stray | 0 | 0 | 0 | ✅ |

The auto-linker has no caller; `graph.kg_edges` is empty. Prediction confirmed exactly.

---

## B. `fact_type` and `node_type` distribution — predicted vs actual

### B.1 `fact_type` (C4)

| fact_type | Predicted (blind 5-case) | Actual (5-case, stray excluded) | Actual (incl. stray) | Match |
|---|---|---|---|---|
| other | 174 | 174 | 174 | ✅ |
| symptom | 25 | 25 | 27 | ✅ |
| medication | 2 | 2 | 3 | ✅ |
| **total** | **201** | **201** | **204** | ✅ |

Stray adds 2 symptom (`fever`, `pain`) + 1 medication (`ibuprofen`), 0 other.

### B.2 `node_type` (C6)

| node_type | Predicted (blind 5-case) | Actual (5-case, stray excluded) | Actual (incl. stray) | Match |
|---|---|---|---|---|
| Other | 174 | 174 | 174 | ✅ |
| Symptom | 10 | 10 | 12 | ✅ |
| Medication | 2 | 2 | 3 | ✅ |
| **total** | **186** | **186** | **189** | ✅ |

Only three node types ever appear — `Other`, `Symptom`, `Medication` — exactly as predicted. None of
the `LabResult / ConditionHypothesis / Procedure / …` types defined in `FACT_TYPE_TO_NODE_TYPE` appear,
because the keyword extractor never emits those fact types.

### B.3 Symptom / Medication node *identities* — predicted vs actual

| Case | Predicted symptom nodes | Actual symptom nodes | Predicted med | Actual med | Match |
|---|---|---|---|---|---|
| C01 | fever, pain | fever, pain | — | — | ✅ |
| C02 | insomnia | insomnia | — | — | ✅ |
| C03 | fatigue, fever, cough | cough, fatigue, fever | — | — | ✅ |
| C04 | pain, chest_pain | chest_pain, pain | aspirin | aspirin | ✅ |
| C05 | pain, fatigue | fatigue, pain | aspirin | aspirin | ✅ |
| stray | (not predicted) | fever, pain | (not predicted) | ibuprofen | extra |

Every predicted identity is present; no unpredicted identities in the 5 cases. The prediction's caveat
that the `aspirin` nodes are **incidental keyword hits** (not the cases' real therapies, which the
4-drug matcher misses) stands.

---

## C. Verdict on each listed prediction uncertainty

The prediction listed 5 uncertainties (§6 of the prediction report). Verdicts:

### C.1 — Text fed to the extractor / "empty-text collapse" (the #1 swing factor) → **REFUTED. Text reaches the extractor.**

The prediction worried that `tasks.py` reads `data["_raw_text"]` / `source_metadata.text` while
`seed.sh` sends text under `metadata.text`; if the text never surfaced, every event would collapse to
a single OTHER node with `normalized_key = sha256("")` per user.

**Evidence it did NOT collapse:**
- OTHER nodes: **174 distinct `normalized_key` out of 174 total** — every OTHER node is unique.
- **Zero** nodes carry the empty-string hash `e3b0c44298fc1c14` (= `sha256("")[:16]`).
- OTHER node `display_label`s are **real text**: e.g. *"Loose stools for many years, described as
  beginning in childhood."*, *"Rheumatology workup showed high inflammatory markers…"* (from
  `timeline_*` prose) and `{"kind": "observation", "benchmark": …}` (from `json.dumps(raw_payload)`
  on `obs_*` events) — exactly the two text sources the prediction modelled.
- `source_metadata->>'text'` is populated on every event with the same prose.

**Path actually used:** vault rows have `blob_ref` set (text also persisted to the blob store), so the
`event.blob_ref is None` branch is false and the `source_metadata.text` fallback is not what fires;
the ingestion worker surfaces the text to the processing worker as `_raw_text`, which the extractor
reads directly. Net effect: the prediction's **deterministic assumption (text reaches the extractor)
was correct**, and the catastrophic-collapse scenario it flagged as the largest swing factor **did not
occur**. This is why facts/nodes match to the unit.

### C.2 — Per-patient vs per-mode dedup → **Not exercised (only blind seeded); no cross-mode merge occurred.**

The concern was that seeding both modes into one `synthetic_user_id` would dedup symptom/medication/
OTHER nodes *across* modes and pull totals below the per-mode sum. Since **only `blind_pre_diagnosis`
is present**, no cross-mode merging happened, and the per-mode (blind) figures match exactly. The
hypothesis is plausible but **untestable on the current data**.

### C.3 — Design-track facts/nodes/edges are estimates → **Confirmed not realised (design pipeline unbuilt).**

Actual output is pure current-implementation: 3 node types only, **0 edges**, no intelligence-engine or
Health-Thread objects. The design-expected ranges (≈679 facts / ≈407 nodes / ≈531 edges) describe an
unbuilt pipeline and are **not** reflected in the cluster, as the prediction itself stated.

### C.4 — `aspirin` / `pain` matches partly incidental → **Confirmed.**

`aspirin` appears as a Medication node in C04 and C05 only; the clinically central drugs
(methylprednisolone, prednisone, methotrexate, complement-directed / cofactor therapy) are absent
because they are not among the 4 keyword drugs. `pain` is matched both standalone and inside
`chest pain` (C04 has both `pain` and `chest_pain` nodes). These are keyword artifacts, as predicted.

### C.5 — Mode divergence is informative (Missing-Data engine target) → **N/A — full mode not seeded.**

`full_results_no_final_label` events are absent, so the blind/full divergence cannot be observed in the
cluster. The qualitative point stands for a future full-mode seed.

---

## D. Root-cause notes for divergences

### D.1 Only blind mode is present (largest "headline" gap vs the prediction's combined totals)

The prediction's executive totals (452 / 459 / 459 / 427) sum **both** modes. The cluster holds only
`blind_pre_diagnosis` (per-case C2 counts equal the prediction's blind column exactly: 51/47/36/36/27).
The benchmark seed subagent reported seeding blind mode only — confirmed. When compared against the
correct (blind) prediction rows, there is **no gap**.

### D.2 C5 evidence links are ~2× facts — duplicate C4 processing, non-idempotent linking

Mechanism, established from the data:

- Per-event shape: **193 events → 1 fact / 2 links**, **4 events → 2 facts / 4 links** (the C04
  multi-keyword `chest pain` events), **1 event (stray) → 3 facts / 3 links**.
- `evidence_links` rows: **405 total**, of which **204 valid** (source fact exists) and **201 orphan**
  (source `fact_id` not in `processing.extracted_facts`). Every link has a distinct `source_id`
  (405 distinct), i.e. 405 distinct `fact_id`s were generated but only 204 fact rows persist.

Interpretation: each of the 197 benchmark events was **processed twice** by the C4 Dramatiq worker
(at-least-once delivery). On each pass `_extract_facts` mints fresh `fact_id`s and calls both
`insert_fact` and `link_fact` (neither has an `ON CONFLICT`/dedup clause in code). The **facts** from
the second pass did not survive (the table shows the single-pass count per event), but the second
pass's **links were inserted** referencing those now-absent `fact_id`s → 201 orphan links. The stray
patient was processed **once** (3 facts / 3 links, no orphans), which is why its links are 1×.

Consequences:
- The prediction's **invariant** ("one PRIMARY link per fact") holds: `valid_links (204) == facts
  (204)`, and no fact is orphaned (every fact still has its link).
- But the table also contains **orphan links** (links without a fact). The DB trigger
  `enforce_no_orphan_claims` only checks that the *raw event* exists, not the *fact*, so these orphan
  links are not blocked. This is a real, measurable artifact the prediction did not anticipate
  (it assumed exactly-once processing).
- Nodes were unaffected because `upsert_node` dedups on `(patient_id, normalized_key)` and is
  idempotent — hence node counts match the prediction exactly despite double processing.

### D.3 The stray manual-test patient

`7e47287f-7325-4477-8bae-8040ddf21e46` has 1 `manual_text` event:
*"Patient reports persistent fever and severe joint pain for 3 weeks, taking ibuprofen 400mg…"* →
keyword hits `fever`, `pain`, `ibuprofen` → 3 facts / 3 nodes (2 Symptom, 1 Medication), 3 links.
This is a hand-entered smoke-test event, not part of the benchmark corpus, and accounts for the entire
difference between the 5-case totals and the grand totals.

### D.4 No vault-level dedup

`duplicate_of_event_id IS NOT NULL` on **0** events — C2 did not collapse any rows; all 198 events are
distinct vault rows (one per seed POST). The doubling is purely a C4-processing-layer phenomenon.

---

## E. Accuracy assessment

**Where the prediction was right (and why):**
- **Events, facts (totals + by `fact_type`), nodes (totals + by `node_type` + identities), edges** —
  all match the blind prediction **to the unit**. This is expected: the prediction was re-derived by an
  offline script mirroring `seed.sh` text selection, the `TextFactExtractor` keyword logic, and
  `upsert_node` dedup. Because the seeded text genuinely reaches the extractor, that deterministic
  model reproduced reality exactly.
- The **structural** predictions are all confirmed: only 3 node types ever appear; OTHER dominates
  (174/186 nodes); OTHER keys are unique (no collisions); `aspirin` is the only medication captured in
  the corpus and is incidental; edges = 0; no engines/threads.
- The prediction's **#1 risk call** (empty-text collapse) was correctly *flagged as the biggest swing
  factor* and the prediction correctly *chose* the "text reaches extractor" branch — which is what
  happened.

**Where the prediction was wrong / incomplete (and why):**
1. **C5 link cardinality.** Predicted 1 link per fact (row count = fact count). Actual row count is
   ~2× due to duplicate processing leaving orphan links. The *invariant* was right; the *row count*
   was not, because the prediction assumed exactly-once processing.
2. **Mode coverage.** The combined-mode headline totals don't describe the cluster, which has blind
   only. (The per-case blind rows, which are the auditable unit, are correct.)
3. **The stray manual-test patient** was not in the prediction (the prediction was derived purely from
   the fixture corpus). It contributes +1 event / +3 facts / +3 nodes / +3 links.

**Overall:** For the slice of reality that exists (blind mode, current implementation), the
deterministic prediction is **accurate to the unit** on every count except evidence-link **row** count,
where an operational artifact (double processing) inflated rows 2× without violating the one-link-per-
fact invariant. The single largest stated uncertainty — whether seeded text reaches the extractor —
resolved in the favorable (predicted) direction.

---

## Appendix — raw SQL & outputs

All queries run via `kubectl exec -n wellbe postgres-0 -- psql -U wellbe -d wellbe -c "<SQL>"`.

### Cluster reachability
```
$ kubectl get pods -n wellbe
postgres-0 ... 1/1 Running ; processing-worker / ingestion-worker / vault-writer / minio / redis / zitadel all Running
```

### Q1 — total counts per stage
```sql
SELECT 'C2_events' AS metric, count(*) FROM vault.raw_context_events
UNION ALL SELECT 'C4_facts', count(*) FROM processing.extracted_facts
UNION ALL SELECT 'C5_links', count(*) FROM evidence.evidence_links
UNION ALL SELECT 'C6_nodes', count(*) FROM graph.kg_nodes
UNION ALL SELECT 'C6_edges', count(*) FROM graph.kg_edges;
```
```
 C2_events | 198
 C4_facts  | 204
 C5_links  | 405
 C6_nodes  | 189
 C6_edges  |   0
```

### Q2 — per-patient C2 events
```sql
SELECT patient_id, count(*) FROM vault.raw_context_events GROUP BY patient_id ORDER BY patient_id;
```
```
 00697626-0025-5d87-9576-20367e50c0e1 | 47
 23b1d00e-65db-530a-9d4b-5bde4dc39a3f | 36
 61b3a25e-867f-50f2-9e6f-0483ec54e245 | 51
 7e47287f-7325-4477-8bae-8040ddf21e46 |  1
 8e2138f0-a50a-5f54-a42e-719254a5fafd | 27
 cd2e1041-bc5b-5c4e-adae-1786c640079e | 36
```

### Q3 — per-patient facts / nodes / links
```sql
SELECT patient_id, count(*) FROM processing.extracted_facts GROUP BY patient_id ORDER BY patient_id;
SELECT patient_id, count(*) FROM graph.kg_nodes GROUP BY patient_id ORDER BY patient_id;
SELECT patient_id, count(*) FROM evidence.evidence_links GROUP BY patient_id ORDER BY patient_id;
```
```
facts:  00697..=47  23b1..=39  61b3..=51  7e47..=3   8e21..=27  cd2e..=37
nodes:  00697..=46  23b1..=35  61b3..=47  7e47..=3   8e21..=25  cd2e..=33
links:  00697..=94  23b1..=78  61b3..=102 7e47..=3   8e21..=54  cd2e..=74
```

### Q4 — fact_type / node_type distributions
```sql
SELECT fact_type, count(*) FROM processing.extracted_facts GROUP BY fact_type ORDER BY count(*) DESC;
SELECT node_type, count(*) FROM graph.kg_nodes GROUP BY node_type ORDER BY count(*) DESC;
```
```
fact_type:  other 174 | symptom 27 | medication 3
node_type:  Other 174 | Symptom 12 | Medication 3
```

### Q5 — OTHER-node collapse test (uncertainty #1)
```sql
SELECT count(DISTINCT normalized_key) AS distinct_keys, count(*) AS total_nodes
  FROM graph.kg_nodes WHERE node_type='Other';
SELECT normalized_key, count(*) FROM graph.kg_nodes WHERE node_type='Other'
  GROUP BY normalized_key HAVING count(*)>1 ORDER BY count(*) DESC LIMIT 10;
SELECT count(*) AS empty_string_hash_nodes FROM graph.kg_nodes WHERE normalized_key='e3b0c44298fc1c14';
```
```
distinct_keys = 174 | total_nodes = 174
(0 rows with count > 1)
empty_string_hash_nodes = 0
```

### Q6 — evidence-link cardinality & orphans
```sql
SELECT link_type, count(*) FROM evidence.evidence_links GROUP BY link_type;          -- primary | 405
SELECT count(DISTINCT source_id), count(*) FROM evidence.evidence_links;             -- 405 | 405
SELECT cnt AS links_per_fact, count(*) FROM
  (SELECT source_id, count(*) cnt FROM evidence.evidence_links GROUP BY source_id) s
  GROUP BY cnt ORDER BY cnt;                                                         -- 1 | 405
SELECT count(*) FROM evidence.evidence_links l
  WHERE NOT EXISTS (SELECT 1 FROM processing.extracted_facts f WHERE f.id=l.source_id); -- orphan = 201
SELECT count(*) FROM evidence.evidence_links l
  WHERE EXISTS (SELECT 1 FROM processing.extracted_facts f WHERE f.id=l.source_id);     -- valid  = 204
```

### Q7 — facts-vs-links per raw event
```sql
SELECT f_cnt AS facts_per_event, l_cnt AS links_per_event, count(*) AS num_events FROM (
  SELECT e.id,
    (SELECT count(*) FROM processing.extracted_facts f WHERE f.raw_context_event_id=e.id) f_cnt,
    (SELECT count(*) FROM evidence.evidence_links  l WHERE l.raw_context_event_id=e.id) l_cnt
  FROM vault.raw_context_events e) s
GROUP BY f_cnt, l_cnt ORDER BY num_events DESC;
```
```
 facts_per_event | links_per_event | num_events
        1        |        2        |    193
        2        |        4        |      4
        3        |        3        |      1   (stray, processed once)
```

### Q8 — Symptom / Medication node identities
```sql
SELECT patient_id, node_type, normalized_key FROM graph.kg_nodes
  WHERE node_type IN ('Symptom','Medication') ORDER BY patient_id, node_type, normalized_key;
```
```
 00697..  Symptom    insomnia
 23b1..   Medication aspirin
 23b1..   Symptom    chest_pain
 23b1..   Symptom    pain
 61b3..   Symptom    fever
 61b3..   Symptom    pain
 7e47..   Medication ibuprofen     (stray)
 7e47..   Symptom    fever         (stray)
 7e47..   Symptom    pain          (stray)
 8e21..   Medication aspirin
 8e21..   Symptom    fatigue
 8e21..   Symptom    pain
 cd2e..   Symptom    cough
 cd2e..   Symptom    fatigue
 cd2e..   Symptom    fever
```

### Q9 — proof text reached the extractor (sample OTHER labels + stray content)
```sql
SELECT left(display_label,55), left(normalized_key,16) FROM graph.kg_nodes
  WHERE node_type='Other' AND patient_id='61b3a25e-867f-50f2-9e6f-0483ec54e245' LIMIT 6;
SELECT patient_id, source_type, blob_ref IS NULL, left(source_metadata->>'text',90)
  FROM vault.raw_context_events WHERE patient_id='7e47287f-7325-4477-8bae-8040ddf21e46';
SELECT count(*) FROM vault.raw_context_events WHERE duplicate_of_event_id IS NOT NULL;  -- 0
```
```
OTHER labels (C01): "Loose stools for many years, described as beginnin…" / "Rheumatology workup
  showed high inflammatory marke…" / "Marked deterioration with edema, explosive diarrhe…" /
  '{"kind": "observation", "benchmark": {"case_id": "…'   (timeline prose + obs_* json.dumps)
stray event text: "Patient reports persistent fever and severe joint pain for 3 weeks, taking
  ibuprofen 400mg"   (source_type=manual_text, blob_ref NOT null)
duplicate_of_event_id set on 0 events
```

### Code paths confirmed (read-only)
- `backend/.../processing-worker/.../tasks.py` `_extract_facts`: reads `data["_raw_text"]`, falling
  back to `source_metadata.text` only when `blob_ref is None`; one `insert_fact` + one `link_fact` per
  result; nodes upserted (idempotent) via `_create_graph_node`. No `ON CONFLICT` on facts or links.
- `backend/.../c4_processing/.../extractor.py` `TextFactExtractor`: 10 symptom + 4 medication keywords,
  OTHER fallback with `normalized_key = sha256(text)[:16]`.
- `tests/fixtures/benchmark/seed.sh`: sends `source_type='manual_text'`, text under both `metadata.text`
  and base64 `raw_data`; text = `raw_payload.original.event` else `json.dumps(raw_payload)`.

*End of cross-reference report.*
