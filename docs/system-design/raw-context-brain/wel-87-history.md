# WEL-87 history

## Authority

**Status:** Historical repository snapshot.

**Canonical issue:** [WEL-87](https://belias.atlassian.net/browse/WEL-87).

**Captured:** Jira description and all five comments through comment `10137`.

**Does not override:** The [current design](README.md), the live Jira issue, or the [proposed decision record](../../decisions/raw-context-brain-theory-lab.md).

**Issue state at capture:** In Progress, unresolved, Low priority, under WEL-2 Data factory.

**Relationships:** Blocks WEL-58. Relates to WEL-44, WEL-59, and WEL-69.

---

## Investigation

Can one network-inspired Raw Context Brain graph support AI-assisted raw linking, bounded `more(route_handle)` navigation, and Cosmos visualization without copying Vault data or sending the complete graph to a model?

The spike asked for a disposable synthetic lab before production integration.

The raw association layer sits after immutable Vault capture and before ordinary semantic processing.

## Founder intent recorded by the spike

- Store every accepted input in the immutable Vault first.
- Use Nodes that reference Vault ids without duplicating source content.
- Let a model propose associations while preserving `no_link` and `uncertain`.
- Record contextual association, never diagnosis, cause, severity, or medical truth.
- Use one persistent topology for human visualization and bounded system navigation.
- Keep visited Nodes, depth, frontier, and budgets as temporary overlay state.
- Keep each person's graph and routing fully isolated.

## Architecture hypothesis

### Evidence plane

Immutable synthetic source events and stable ids.

### OSPF and Intermediate System to Intermediate System (IS-IS)-inspired topology plane

Open Shortest Path First (OSPF) and IS-IS contribute topology-state lessons only.

Versioned link advertisements with provenance, sequence, digest, supersession, and explicit withdrawal.

A Link-State Database (LSDB)-like projection contains the accepted-current topology for one pinned snapshot.

Topology does not itself authorize disclosure of endpoint text.

### Border Gateway Protocol (BGP)-inspired policy pipeline

BGP contributes route-policy and alternative-selection lessons only.

**Candidate Context Routing Information Base (RIB):** Eligible candidate paths before final selection.

**Selected Context RIB:** Deterministic routes selected for the purpose and snapshot.

**Consumer Export RIB:** Minimum redacted route data permitted for the model or visual consumer.

Default-deny import and export policy runs before relevance ranking.

### Hierarchical Navigable Small World (HNSW) and bounded-beam discovery

HNSW search provides approximate candidates.

Approximate retrieval seeds candidates.

Exact person, provenance, authorization, and policy checks run afterward.

The frontier remains bounded and should preserve diversity across source families, facets, times, and route reasons.

Generic hubs and near-duplicate routes are penalized.

Approximate exhaustion is not proof that no related context exists.

### Named Data Networking (NDN) and Content-Centric Networking (CCN)-inspired interaction

NDN and CCN contribute request-for-content and bounded-response lessons.

`SemanticInterest` describes a request for relevant context.

`SemanticData` is a bounded response with freshness, snapshot identity, returned evidence, legal continuations, and an optional route handle.

`more(route_handle)` atomically continues a saved frontier.

It does not rerun the query with a larger limit or silently move to a newer topology.

The spike mapped:

- Interest → `SemanticInterest`
- Data → `SemanticData`
- Forwarding Information Base (FIB) → category and semantic route resolvers
- Pending Interest Table (PIT) → scoped in-flight request and coalescing state
- Content Store → person-, policy-, snapshot-, and derivation-scoped caches
- Nonce → duplicate and replay detection
- InterestLifetime → step deadline
- HopLimit → maximum semantic expansion depth
- MustBeFresh → snapshot and freshness constraint
- FinalBlockId → exact end of a stable result sequence

### Local router

The local router—not the model—owns:

- identity and person scope,
- authorization,
- candidate generation,
- result count,
- topology snapshot,
- visited Nodes and Links,
- saved frontier,
- depth and fan-out,
- deadlines and budgets,
- model token and cost limits,
- and legal next routes.

The model receives only locally prepared evidence and controller-issued handles.

## Required failure behavior

**False-link reinforcement:** Derived links do not strengthen one another without a new independent raw source, person correction, or recorded recalculation.

**Cycles and mixed versions:** One exploration uses one topology snapshot and authorization epoch. Exact visited sets prevent repeated traversal.

**Hub domination:** Degree normalization, source-family caps, and diversity prevent generic hubs from hiding alternatives.

**Typed stopping:** `supported_leaf`, `approximate_frontier_exhausted`, `budget_exhausted`, `policy_blocked`, `authorization_changed`, `stale_snapshot`, `dependency_unavailable`, or `insufficient_independent_evidence`.

**Churn:** Equivalent updates coalesce. Nearly equal routes may use hysteresis. Person corrections and consent changes are never damped.

**Hostile content:** Evidence text cannot mint controls, select scope, issue routes, or change budgets.

## Protocol concepts explicitly rejected

- Literal protocol daemons or flooding
- Shortest path as best evidence
- One scalar route metric as medical significance
- Random load balancing
- Route controls derived from untrusted content
- BGP-style damping of person corrections
- Fixed infinity or hold-down behavior
- Stale serving after authorization changes
- Authenticated origin as proof of truth
- Source-dropping summaries
- Silent default routes into broader context

## Lab boundary

- Isolated package only
- Synthetic or explicitly de-identified fixtures
- No production Vault, C4, C6, consent, or workspace integration
- No production migration or runtime dependency
- Deterministic replay without live model calls
- No bible-file change
- No claim of medical meaning

## Research areas left open

1. Link semantics and confidence
2. Candidate and route ranking
3. Advertisement and snapshot contract
4. Continuation-capability security
5. Navigation taxonomy
6. Model prompt and evaluation contract
7. Summary policy
8. Persistence choice
9. Visualization comprehension
10. Provider and privacy readiness

---

## Comment history

### 10095 — 2026-10-11 — Spike created

Created under WEL-2 with `layer:core`, `component:data-factory`, `impact:cross-cutting`, `phase:post-mvp`, and Low priority.

The spike blocked WEL-58 and related to WEL-44, WEL-59, and WEL-69.

### 10102 — 2026-10-11 — Networking guidance expanded

Added OSPF/IS-IS, BGP, NDN/CCN, HNSW, bounded-beam, and Kademlia-derived lessons.

Added failure experiments, rejected mechanisms, ten research areas, and the four-state research-gap classification.

### 10103 — 2026-10-11 — Initial lab built

The isolated lab contained a Vault, pointer graph, advertisement log, bounded router, heuristic judge, optional OpenAI judge, Cosmos view, and scorecard.

One in-memory graph served both visualization and route continuation.

The model received a bounded page.

Handles were pinned to one snapshot and authorization epoch.

The initial run reported 66.7% precision on 12 synthetic notes, both no-link traps falsely linked, no live model call, and eight research areas still open.

The recommendation remained revise.

### 10104 — 2026-10-11 — Five lab revisions

Model `no_link` and `uncertain` judgments stopped deleting accepted edges.

Candidates became the union of exact token matches, accepted neighbors, and the per-person approximate index.

Continuation with the same request id returned the saved page; a new id advanced within the expansion budget.

Unknown source independence stopped increasing confidence.

Approximate-index recall against exact token-and-neighbor candidates was low, while vector-neighbor recall remained high.

### 10137 — 2026-10-20 — Snapshot at `66aa328`

This comment describes the lab at commit `66aa328`, not the current lab.

At that point the router owned ingestion, advertisements, accepted edges, per-person indexing, and `explore` / `more(route_handle)`.

The Cosmos view still managed its click trail separately and did not call `explore`.

Later code connected explorer continuation, changed ranking behavior, and replaced counter-based route ids with random 128-bit handles.

The comment recorded the graph's undirected links, record-kind colors, degree-based size, accepted-neighbor trail, note keywords, opened-note panel, and the distinction between persistent topology and temporary traversal state.

## Later implementation evidence

Read current code and tests under [`labs/raw-context-brain`](../../../labs/raw-context-brain/README.md).

Read the generated measurements in [`REPORT.md`](../../../labs/raw-context-brain/REPORT.md).

Read the current implementation comparison in [Lab implementation gaps](lab-implementation-gaps.md).
