# Decision: Raw Context Brain stays a lab

**Status:** Proposed  
**Date opened:** 2026-10-11  
**Date approved:**  
**Approved by:**  
**Jira Spike:** WEL-87  
**Blocks:** WEL-58 Auto-linking across the personal graph

---

## Question

Can one pointer graph support Cosmos visualization and bounded route continuation without copying vault text or sending the whole graph to a model, and is that graph ready to become production architecture?

## Context

This touches the Raw Context Vault (C2), the processing pipeline boundary (C4), and Knowledge Graph auto-linking (C6). WEL-87 asked for a disposable synthetic lab before any production story. Guessing a production graph, a ranking formula, or a model contract from the lab would be expensive to unwind because links, snapshots, and route handles would become stored behavior.

## Research provided

Lab measurements from the WEL-87 scorecard run on 2026-10-11. These are synthetic-lab results, not a founder-reviewed gold set and not a live model run.

Heuristic judge on 12 synthetic notes:

- True links among gold link pairs: 4 / 4
- Candidate recall of gold links: 100.0%
- Precision of predicted links: 66.7%
- False links on gold no-link pairs: 2 (100.0%)
- Abstention quality: 33.3%
- Injection notes accepted as links: 0
- Approximate neighbour recall @5 in top 10: 100.0%

Sparse-map exploration, one bounded page:

- 100 nodes: 23 ms, 1265 bytes, 4 items
- 1,000 nodes: 317 ms, 1266 bytes, 4 items
- 10,000 nodes: 11614 ms, 1267 bytes, 4 items

Cross-person candidates in these runs: 0.

26 automated tests passed, covering confidence caps, withdrawal, foreign handles, cross-person exclusion, continuation, cycles, stale snapshots, authorization changes, and rebuilding.

The same run labeled eight of the ten spike research areas `still_open`, advertisement/snapshot behavior `measured_in_lab`, and summary policy `not_needed_for_minimum_production_boundary`.

_Research received: 2026-10-11_

## Approaches considered

Approach 1: Proceed into production with this topology — the page stayed about 1.3 KB at 10,000 nodes and cross-person candidates stayed at zero. | Pro: routing and isolation held on synthetic data. | Con: predicted-link precision was 66.7%, both gold no-link trap pairs were false links, and eight research areas are still open.

Approach 2: Revise by keeping the lab and leaving production blocked — preserve the measured pointer graph, local router, bounded page, and snapshot-pinned continuation. | Pro: those mechanisms held in tests without copying vault text into the graph. | Con: there is still no approved production boundary for ranking, handles, or the model contract.

Approach 3: Stop the single-graph idea — treat the 100% false-link rate on the two trap pairs as a failed hypothesis. | Pro: the heuristic did assert links the gold set rejected. | Con: that rate is two token-overlap traps, while candidate recall of the four gold links was 100% and the routing tests passed.

## Decision

Revise. Keep the Raw Context Brain as an isolated synthetic lab. Do not copy it into the vault, the processing pipeline, or the knowledge graph, and do not unblock WEL-58, until the still-open research areas are decided from evidence supplied or explicitly approved by the user.

## Trade-offs accepted

The lab does not become a shippable auto-linker. Link quality of a hosted model is unknown. Route-handle signing, a healthcare facet list, persistence, and whether people can read the picture without treating a link as cause are still open. The in-memory advertisement log is evidence about behavior, not a storage choice.

## Implementation notes

The lab lives at `labs/raw-context-brain/` and is outside the production npm workspaces. `REPORT.md` in that directory holds the scorecard. A passing lab run does not change `docs/current/capability-index.md`.

**Current design:** [`docs/system-design/raw-context-brain/README.md`](../system-design/raw-context-brain/README.md)

**WEL-87 history:** [`docs/system-design/raw-context-brain/wel-87-history.md`](../system-design/raw-context-brain/wel-87-history.md)

**Lab implementation gaps:** [`docs/system-design/raw-context-brain/lab-implementation-gaps.md`](../system-design/raw-context-brain/lab-implementation-gaps.md)

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
