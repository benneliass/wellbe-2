import { writeFileSync } from "node:fs";
import { evaluateGold } from "./gold.js";
import { generateTopology } from "./generate.js";
import { HnswIndex } from "./hnsw.js";
import { mulberry32 } from "./text.js";

async function recall(): Promise<number> {
  const index = new HnswIndex(12, 16);
  const random = mulberry32(12);
  const vectors: Float64Array[] = [];
  for (let cluster = 0; cluster < 8; cluster += 1) {
    const center = Float64Array.from({ length: 16 }, () => random() * 2 - 1);
    for (let member = 0; member < 25; member += 1) {
      const vector = Float64Array.from(center, (value) => value + (random() - 0.5) * 0.05);
      let norm = 0;
      for (const value of vector) norm += value * value;
      norm = Math.sqrt(norm);
      for (let dim = 0; dim < vector.length; dim += 1) vector[dim] /= norm || 1;
      index.add(`c${cluster}-${member}`, vector);
      vectors.push(vector);
    }
  }
  let hits = 0;
  let total = 0;
  for (let query = 0; query < 20; query += 1) {
    const cluster = query % 8;
    const member = query % 25;
    const id = `c${cluster}-${member}`;
    const vector = vectors[cluster * 25 + member];
    if (!vector) continue;
    const exact = index.bruteForce(vector, 5, id).map((item) => item.id);
    const approx = new Set(index.search(vector, 10).map((item) => item.id));
    for (const neighbor of exact) {
      total += 1;
      if (approx.has(neighbor)) hits += 1;
    }
  }
  return total === 0 ? 0 : hits / total;
}

function scaleRow(count: number): { count: number; milliseconds: number; bytes: number; items: number } {
  const started = Date.now();
  const lab = generateTopology({ count, kind: "sparse", seed: 9, pageSize: 5, hopLimit: 4 });
  const response = lab.explore({ personId: "synthetic-1", purpose: "nav", anchorId: "n1" });
  return {
    count,
    milliseconds: Date.now() - started,
    bytes: new TextEncoder().encode(JSON.stringify(response)).length,
    items: response.items.length,
  };
}

function candidateRecall(count: number): number {
  const lab = generateTopology({ count, kind: "sparse", seed: 9, pageSize: 5, hopLimit: 4 });
  let hits = 0;
  let total = 0;
  for (let query = 0; query < 20; query += 1) {
    const id = `n${(query * 17) % count}`;
    const event = lab.vault.get(id);
    if (!event) continue;
    const split = lab.candidateSplit("synthetic-1", event.text, id);
    const approx = new Set(split.hnsw);
    for (const candidate of split.exact) {
      total += 1;
      if (approx.has(candidate)) hits += 1;
    }
  }
  return total === 0 ? 0 : hits / total;
}

const gold = await evaluateGold();
const approximateRecall = await recall();
const exactRecall100 = candidateRecall(100);
const exactRecall1000 = candidateRecall(1_000);
const scales = [100, 1_000, 10_000].map(scaleRow);
const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

const report = `# WEL-87 Raw Context Brain lab report

Date: 2026-10-11

This is a disposable synthetic-data lab. It is not a production architecture decision.

## Recommendation

**revise**

One pointer topology can serve a Cosmos view and a bounded local route in this lab. Link judgments, continuation security, and persistence are not ready to leave the lab. Do not promote this into the Vault, the processing pipeline, or the knowledge graph.

Smallest next boundary: keep the lab. Production stories, including WEL-58, stay blocked.

## Measurements

Heuristic judge on the 12-note synthetic gold set (not founder-reviewed):

| Measure | Result |
|---|---|
| True links among gold link pairs | ${gold.trueLinks} / ${gold.goldLinks} |
| Candidate recall of gold links | ${percent(gold.candidateRecall)} |
| Precision of predicted links | ${percent(gold.precision)} |
| False links on gold no-link pairs | ${gold.falseLinks} (${percent(gold.falseLinkRate)}) |
| Abstention quality | ${percent(gold.abstentionQuality)} |
| Injection notes accepted as links | ${gold.injectionAcceptedLinks} |
| Approximate neighbour recall @5 in top 10 | ${percent(approximateRecall)} |
| HNSW top 16 recall against exact token and neighbor candidates, 100 nodes | ${percent(exactRecall100)} |
| HNSW top 16 recall against exact token and neighbor candidates, 1,000 nodes | ${percent(exactRecall1000)} |

Sparse-map exploration payload. The model-facing response stays a page, not the map:

| Nodes | Build + one exploration | Response bytes | Items returned |
|---|---|---|---|
${scales
  .map((row) => `| ${row.count} | ${row.milliseconds} ms | ${row.bytes} | ${row.items} |`)
  .join("\n")}

Cross-person candidates observed in these runs: 0.

Live OpenAI was not called. No API key was read and no prompt was logged.

## Failure log

Automated tests provoke the cases below. See \`npm test\` for the latest pass/fail.

- A model \`no_link\` or \`uncertain\` stays in the log and leaves an accepted edge in place. Withdrawal and a user correction can remove it.
- The same continuation request id returns the saved page. A new id advances, until the expansion budget stops the walk.
- Derived confidence does not rise from an unknown source or from repeated agreement on the same lineages.
- User corrections apply immediately, including a higher or lower confidence.
- Withdrawal keeps the vault event and drops the accepted edge.
- A foreign handle or a clinical reason code is not stored as a link.
- Another person's note is absent from the judge request.
- \`no-model\` notes are omitted and \`summary-only\` notes export type and time.
- Document members hang off one hub.
- Full advertisement replay matches the incremental projection digest.
- A rebuilding projection refuses new routes.
- Judge timeouts retry twice, then return \`dependency_unavailable\` with the vault event kept.
- \`more\` continues the saved frontier and does not rerun candidate search.
- Cycles stop. Stale snapshots, authorization changes, expiry, and use limits stop continuation.
- An isolated node is an exact leaf. The detail text does not say that no related context exists.
- Hub degree is normalized below a specific note with the same overlap.

## Research-gap matrix

| Focus | Label | Lab note |
|---|---|---|
| Link semantics and confidence | still_open | The lab enforces a confidence cap and abstention. Permitted reason types are not settled. |
| Candidate and route ranking | still_open | The lab uses one recorded lexicographic order with degree normalization. That order is not approved. |
| Advertisement and snapshot contract | measured_in_lab | Sequence, digest, tombstone, and incremental-versus-full digest match on the synthetic log. |
| Continuation capability security | still_open | Handles are opaque and server-side, with expiry, use limits, and snapshot and authorization invalidation. Signing and encryption were not chosen. |
| Healthcare navigation taxonomy | still_open | Routes use source type and time only. |
| OpenAI prompt and evaluation contract | still_open | No founder-reviewed gold set and no live model run. |
| Summary policy | not_needed_for_minimum_production_boundary | The lab keeps source membership and does not summarize as a default. |
| Persistence choice | still_open | The lab is in memory. No second database was introduced. |
| Visualization comprehension | still_open | The default drawing is the route neighborhood. The larger map is a separate control. No person has been asked whether the picture is understood. |
| Provider and privacy readiness | still_open | Synthetic fixtures only. |

## Practical limits

- A 10,000-node sparse map builds and returns one bounded page in the time shown above.
- The exploration response stays under 16 KB in the scale test.
- The generator repeats common tokens, so HNSW recall against the exact token-and-neighbor set is lower than vector-neighbor recall. That gap is reported as approximate.
- The heuristic judge false-links the breakfast/glucose trap. That is a measured limit of token overlap, not evidence about a hosted model.
`;

writeFileSync(new URL("../REPORT.md", import.meta.url), report);
console.log(report);
