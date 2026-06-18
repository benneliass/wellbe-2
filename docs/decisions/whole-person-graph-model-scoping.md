# Decision: Whole-person ("second brain") graph model, cross-concern traversal, and scoping

**Status:** Open
**Date opened:** 2026-06-18
**Date approved:** (fill on approval)
**Approved by:** User
**Jira Spike:** WEL-187 (blocks WEL-78)
**Blocks:** WEL-78 [Build graph visualization]; relates to WEL-60, WEL-156, WEL-16 (E5)

---

## Question

Should WellBe's graph view move from the currently approved **thread‑scoped** model to a **unified
whole‑person ("second brain") map**, and if so: how do we model and serve it without breaking the
non‑diagnosis, privacy, calm, and stability guarantees? Specifically:

1. **Cross‑concern traversal & API (C6/C13):** how to query/return a multi‑concern subgraph (concept
   nodes + concern clusters + bridge nodes) with object/property‑level scoping, given that today's
   `/v2/graph/threads/{id}` is strictly single‑thread and structurally omits out‑of‑thread data. What is
   the new/extended read contract?
2. **Concept de‑dup & cluster derivation:** how concept nodes and concern (cluster) groupings are derived
   from C6 (`thread_ids`, entity resolution), and how shared/bridge nodes are identified.
3. **Relevance‑weighting:** what drives bright‑central vs dim‑edge placement (recency, thread status,
   open loops) without implying severity or diagnosis.
4. **Confidence thresholds & edge provenance:** default visibility floor for edges, what "why connected?"
   returns, and how user‑authored edges (C11) are represented, distinguished, and scored.
5. **Privacy for a unified graph:** authorization across concerns and what a shareable subgraph may
   contain.
6. **Performance/LOD at 200–300+ nodes and the mobile interaction model.**

## Context

This supersedes (on approval) the thread‑scoped stance in `docs/decisions/graph-query-api-contract.md`
(Approved) and the "full patient graph is never shown as one network / one click = one layer" stance in
`docs/decisions/research-brief-c6-graph-visualization.md`. It touches core components **C6 Knowledge
Graph** (node/edge semantics, scoring, clustering, traversal) and **C13 API** (a new/extended graph read
contract), and intersects C1/C17 (scoping/sharing), C9 (missing‑data ghost nodes), C11 (user‑authored
edges), and C14/C15 (investigation/theory lens) for later phases. See
`docs/architecture/component-map.md`.

Guessing wrong is expensive and partly irreversible: a unified graph that leaks across concerns is a
privacy failure; an undifferentiated hairball with statistical edges is a false‑causality / anxiety
hazard that conflicts with `do_not_diagnose_rules.md` and `safety_model.md`. The full proposed design is
in `docs/superpowers/specs/2026-06-18-second-brain-graph-design.md`.

**Research results must be provided by the user. Agents may not self-research.**

## Research provided

_Research received: (pending)_

## Approaches considered

_(to be written from provided research)_

## Decision

_(proposed after research, approved by user)_

## Trade-offs accepted

_(filled on decision)_

## Implementation notes

_(filled after approval)_

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
