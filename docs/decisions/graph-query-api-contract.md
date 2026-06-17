# Decision: Thread-scoped graph read/query API contract

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-165  
**Blocks:** WEL-156 [Graph query/read API endpoint for thread-scoped graph view]

---

## Question

For the `graph` pill ("Open the graph"), what is the thread-scoped graph read/query API contract over the existing C6 schema?
1. **Query shape** — thread-scoped node/edge selection, traversal depth, edge-type filters.
2. **Response contract** (C13) — the shape a viz client consumes.
3. **Viz scoping** — what subset renders (Cytoscape thread view per WEL-78), and how unscoped data is kept out.

The C6 schema itself is already decided (WEL-98, WEL-135, Done); this spike is about the **read/query contract**, not a schema change.

## Context

Touches C6 (Knowledge Graph, read consumer) and needs a C13 endpoint — see `docs/architecture/component-map.md` and `docs/system-design/knowledge_graph.md`. A wrong query contract either leaks unscoped data (privacy) or forces a breaking API change later.

## Research provided

_Research received: YYYY-MM-DD_

<!-- Agent-run research (model, date) recorded verbatim here per research-protocol Section I. -->

## Approaches considered

<!-- Written by agent after research, grounded only in the recorded research. -->

## Decision

<!-- Proposed by agent, approved by user. -->

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
