# Decision: Owner's thread graph includes one-hop neighbours

**Status:** Approved  
**Date opened:** 2026-09-27  
**Date approved:** 2026-09-28  
**Approved by:** User  
**Amends:** [graph-query-api-contract.md](graph-query-api-contract.md), Decision item 3 ("Out-of-thread adjacent nodes are structurally omitted") and the trade-off "Omit out-of-thread adjacency entirely".

---

## Question

The thread graph (`GET /v2/graph/threads/{thread_id}`) showed only the thread's own nodes, so each thread looked isolated: the owner could not see that, say, fatigue in one thread links to a ferritin result in another. Should the thread view show adjacent nodes that live outside the thread?

## Context

The original decision omits out-of-thread adjacency for everyone, so a thread view never discloses that other data exists. That risk is about **other people**: a grantee (clinician, family member) who was shown one thread must not learn that the rest of the record exists. The account owner already has access to their whole record, including the separate full Graph page, so showing them their own neighbouring nodes discloses nothing new.

## Decision

1. **Owner (controller) reads:** the thread graph also returns nodes **one edge away** from the thread's nodes, with the edges that connect them. Each node carries `attributes.in_thread` (`true`/`false`); the web labels outside nodes "elsewhere in your records". The expansion is bounded: at most **50 nodes** in total and **200 boundary edges** scanned (strongest first), and the existing node/edge type filters apply to neighbours. `include_neighbors=false` turns it off.
2. **Grant-based reads (any non-controller principal):** unchanged from the original decision. Out-of-thread adjacent nodes are **structurally omitted**, not summarized or stubbed, so their existence is never disclosed.
3. Neighbours are **connections in the owner's own records, not causes**. Edge vocabulary and the `may_explain` ceiling are unchanged.

## Trade-offs accepted

- **Richer owner view over a single uniform rule:** the endpoint now behaves differently by principal, and that difference must stay covered by tests. The grantee path keeps zero existence leakage.
- **Fixed one-hop bound:** deeper exploration stays on the full Graph page rather than in the thread view.

## Implementation notes

- **C13:** `backend/apps/api/src/wellbe_api/routers/graph_v2.py` expands neighbours only when `principal.is_controller`.
- **C6:** `GraphRepository.edges_touching_nodes` selects the patient's edges with at least one end in the thread's node set.
- **Tests:** `backend/apps/api/tests/test_graph_v2_neighbours.py`, including `test_grantee_never_sees_out_of_thread_adjacency`.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
