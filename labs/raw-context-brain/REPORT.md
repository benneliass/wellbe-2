# WEL-87 Raw Context Brain lab report

Date: 2026-10-21

This is a disposable synthetic-data lab. It is not a production architecture decision.

## Recommendation

**revise**

One pointer topology can serve a Cosmos view and a bounded local route in this lab. Link judgments, continuation security, and persistence are not ready to leave the lab. Do not promote this into the Vault, the processing pipeline, or the knowledge graph.

Smallest next boundary: keep the lab. Production stories, including WEL-58, stay blocked.

## Measurements

Heuristic judge on the 12-note synthetic gold set (not founder-reviewed):

| Measure | Result |
|---|---|
| True links among gold link pairs | 4 / 4 |
| Candidate recall of gold links | 100.0% |
| Precision of predicted links, heuristic column | 66.7% |
| False links on gold no-link pairs | 2 (100.0%) |
| Abstention quality | 33.3% |
| Injection notes accepted as links | 0 |
| Approximate neighbour recall @5 in top 10 | 100.0% |
| HNSW top 16 recall against exact token and neighbor candidates, 100 nodes | 15.2% |
| HNSW top 16 recall against exact token and neighbor candidates, 1,000 nodes | 1.5% |

Sparse-map exploration payload. The model-facing response stays a page, not the map:

| Nodes | Build + one exploration | Response bytes | Items returned |
|---|---|---|---|
| 100 | 21 ms | 1217 | 4 |
| 1000 | 425 ms | 1218 | 4 |
| 10000 | 19856 ms | 1219 | 4 |

Cross-person candidates observed in these runs: 0.

Live model column: not run. No API key was read and no prompt was logged. The heuristic percentage stays in the heuristic column.

## Failure log

Automated tests provoke the cases below. See `npm test` for the latest pass/fail.

- A model `no_link` or `uncertain` stays in the log and leaves an accepted edge in place. Withdrawal and a user correction can remove it.
- The same continuation request id returns the saved page. A new id advances, until the expansion budget stops the walk.
- Derived confidence does not rise from an unknown source or from repeated agreement on the same lineages.
- User corrections apply immediately, including a higher or lower confidence.
- Withdrawal keeps the vault event and drops the accepted edge.
- A foreign handle or a clinical reason code is not stored as a link.
- Another person's note is absent from the judge request.
- `no-model` notes are omitted and `summary-only` notes export type and time.
- Document members hang off one hub.
- Full advertisement replay matches the incremental projection digest.
- A rebuilding projection refuses new routes.
- Judge timeouts retry twice, then return `dependency_unavailable` with the vault event kept.
- `more` continues the saved frontier and does not rerun candidate search.
- Cycles stop. Stale snapshots, authorization changes, expiry, and use limits stop continuation.
- A continuation can focus one advertised note. A note outside that route is refused and the frontier stays.
- Same-lineage neighbors past the cap stop as insufficient independent evidence.
- A copied note does not become a link by itself. When that original sits on the frontier, it is advertised as the original record. A document hub is advertised the same way.
- An isolated node is an exact leaf. The detail text does not say that no related context exists.
- Equal overlap puts a specific note ahead of a hub. A closer match stays ahead of a weaker specific note. Degree is that later tie-break.

## Research-gap matrix

| Focus | Label | Lab note |
|---|---|---|
| Link semantics and confidence | still_open | The lab can say link, no link, or abstain. A later abstain or no link leaves a kept edge in place. Confidence does not rise from repeating the same evidence. Permitted reason types are not settled. |
| Candidate and route ranking | still_open | Relevance is the raw match. Degree is a later tie-break. A previous note is held only when no higher key is worse. That order is not approved. |
| Advertisement and snapshot contract | measured_in_lab | Sequence, digest, tombstone, and incremental-versus-full digest match on the synthetic log. |
| Continuation capability security | still_open | A route id is 128 random bits naming a server record. Expiry, use limits, and snapshot and authorization checks still stop continuation. Signing and encryption were not adopted. |
| Healthcare navigation taxonomy | still_open | Routes name a neighbor, a source type, earlier or later context, the original record when it sits on the frontier, and stop. Diagnosis, cause, and severity are not facets. |
| OpenAI prompt and evaluation contract | still_open | The 12-note score is the heuristic column. No founder-reviewed gold set and no live model column. |
| Summary policy | not_needed_for_minimum_production_boundary | The lab keeps source membership and does not summarize as a default. |
| Persistence choice | still_open | The lab is in memory. No second database was introduced. |
| Visualization comprehension | still_open | Lines have no arrowheads. Color is record kind. Size is the number of links, and the legend says so. No comprehension study has been run. |
| Provider and privacy readiness | still_open | Synthetic fixtures only. |

## Practical limits

- A 10,000-node sparse map builds and returns one bounded page in the time shown above.
- The exploration response stays under 16 KB in the scale test.
- The generator repeats common tokens, so HNSW recall against the exact token-and-neighbor set is lower than vector-neighbor recall. That gap is reported as approximate.
- The heuristic judge false-links the breakfast/glucose trap. That is a measured limit of token overlap, not evidence about a hosted model.
