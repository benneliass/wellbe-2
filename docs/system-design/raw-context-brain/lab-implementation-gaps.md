# Network-concept implementation gaps

## Purpose

**Question:** Which network-inspired Raw Context Brain concepts exist in the current lab, and which remain partial or absent?

**Scope:** [`labs/raw-context-brain`](../../../labs/raw-context-brain/README.md).

**Authority:** Implementation comparison only.

**Normative design:** [`README.md`](README.md).

**Historical source:** [`wel-87-history.md`](wel-87-history.md).

This file does not promote the lab into production architecture.

The [decision record](../../decisions/raw-context-brain-theory-lab.md) remains Proposed.


## Summary

The lab demonstrates the central hypothesis:

> A model can assess or continue through a small, controller-prepared context without receiving the person's full graph.

The gaps below are closed in the lab, aligned to the finished design.

A route handle stays an opaque `rh_` lookup key. The session record lives in a session store. A graph store holds notes, the ledger, nodes, acknowledgements, and the projection revision. The browser uses `localStorage` through that same store. Reload restores the graph and starts with no exploration session. A second lab given the same stores can resolve a handle that has not been expired.

`same_record_group` is a hub membership. A note-to-note link uses a contextual relation. Rebuild checks the full ledger-row hash and rejects a structural link that is not current hub membership.

What stays open is listed at the end. Those are product parameters, not missing lab behavior.

---

## Implemented

### Link advertisements and accepted topology

**Implemented:** Append-only advertisements with sequence, digest, origin, evidence, supersession, and withdrawal.

**Implemented:** Incremental projection into undirected accepted edges.

**Implemented:** `finishRebuild` checks advertisement digests, then rebuilds the projection.

**Evidence:** `src/types.ts`, `src/store.ts`, `src/router.ts`, `tests/safety.test.ts`, and `tests/persist.test.ts`.

### Bounded model context

**Implemented:** The assessment model receives issued handles and short excerpts, not arbitrary Node ids or the full graph.

**Implemented:** Same-person filtering and control tags run before model exposure.

**Implemented:** Returned handles must have been issued in that request.

**Evidence:** `src/router.ts` and `tests/safety.test.ts`.

### Saved frontier and continuation

**Implemented:** A route handle resolves to frontier state held by the browser's `RawContextLab` instance: visited sequence, budgets, snapshot identity, expiry, and use count.

**Implemented:** Each frontier item records the Node that expanded it (`fromId`).

**Implemented:** A forward step takes the next item whose `fromId` is the current tip.

**Implemented:** Continuation advances saved state without rerunning candidate discovery.

**Implemented:** Repeating the same request id returns the saved result. The same request id with a different purpose is denied.

**Implemented:** A continuation that finds no forward note returns `supported_leaf`, keeps that handle for rewind, and keeps the cycle count.

**Evidence:** `src/router.ts` and `tests/navigation.test.ts`.

### Legal next-route advertisements

**Implemented:** The router advertises bounded forward frontier-item, facet, time, source, and stop actions.

**Implemented:** Route ids remain bound to allowed Node ids in the lab instance.

**Implemented:** A focus outside that binding is rejected.

**Evidence:** `src/router.ts` and `tests/navigation.test.ts`.

### Snapshot, purpose, and authorization checks

**Implemented:** Handles bind purpose, authorization epoch, projection revision, projection digest, expiry, and use limit.

**Implemented:** A purpose mismatch returns `wrong_purpose`.

**Implemented:** An exploration handle rejects `operation: "assess_link"`.

**Implemented:** Authorization or topology changes invalidate continuation instead of serving stale state.

**Evidence:** `src/router.ts` and `tests/navigation.test.ts`.


### Exact and approximate stopping

**Implemented:** Exact and approximate completion are distinguished.

**Implemented:** Terminal reasons include supported leaf, insufficient independent evidence, approximate exhaustion, and budget exhaustion.

**Implemented:** Same-lineage exhaustion can end the session while an earlier sibling is still queued, because that sibling is not a forward step from the current tip.

**Evidence:** `src/types.ts`, `src/router.ts`, and `tests/navigation.test.ts`.

### Approximate candidate discovery

**Implemented:** Hierarchical Navigable Small World (HNSW) search supplies approximate candidates.

**Implemented:** Exact token and accepted-neighbor candidates are unioned with approximate candidates.

**Implemented:** Person, policy, and ranking checks run afterward.

**Evidence:** `src/hnsw.ts`, `src/router.ts`, and `tests/navigation.test.ts`.

---

## Closed

Checked by `npm test` (121 passed) and `npm run typecheck`. The wiring tests are `tests/closed-gaps.test.ts`.

**You save a note.** The lab appends a route-set revision. It keeps candidate ids, selected ids, export handles, prune rows, and a provenance record (discovery, rank, prune reason, export handle). The save result includes the revision and the prune rows. The next save appends another revision.

**You save a note that can be closer to a neighbor.** After a non-link judgment, the controller may judge up to two untried neighbors that share more words than the judged note. That is one round. It does not chain.

**Selection is diversified.** The lab cap of 2 applies to lineage, source type, facet, and route reason, and reserves one earlier and one later note when the new note has a time. The cap is a lab stand-in. It is not the open product parameters X, Y, or the keyword floor.

**You repeat a request id.** The pending-interest table replays the saved page. The same id with another purpose is denied. An equivalent request still in flight joins the first one.

**The judge is slow or full.** The lab stops with `dependency_unavailable` on deadline, in-flight cap, or the third failure. The schedule waits with backoff and deterministic jitter. The caller sleeps. The module does not.

**You click an earlier opened note.** Rewind uses the same handle, cuts the path at that note, and is idempotent when the note is already the tip. An exact leaf stays on that handle so the walk can rewind. Other terminals release the handle.

**You reload the page.** Notes, links, nodes, and acknowledgements come back from the graph store. The exploration session is gone. `expireExploration()` drops the walk and leaves the graph.

**You rebuild.** Every stored ledger field except `id` and the hash itself is covered. A bad hash does not publish edges. A `same_record_group` row must be a hub and a current member, and a hub member needs a policy row.

---

## Intentionally rejected

The missing items below are not gaps:

- literal routing daemons or wire protocols,
- graph flooding between peers,
- shortest path as best evidence,
- a single route score as medical importance,
- random route balancing,
- cross-person candidate retrieval,
- controls minted from untrusted evidence,
- model abstention deleting an accepted Link,
- stale continuation after authorization or topology change,
- and approximate exhaustion reported as proof that nothing related exists.

## Production blockers

The lab still does not resolve:

- final category vocabulary,
- keyword thresholds,
- candidate and route ranking policy,
- confidence calibration,
- production judgment contract,
- handle security,
- navigation taxonomy,
- hosted-model evaluation,
- founder-reviewed acceptance thresholds,
- physical persistence architecture,
- visualization comprehension,
- and provider/privacy readiness.

These remain research and decision questions.
