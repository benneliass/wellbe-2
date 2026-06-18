# Decision: Whole-person ("second brain") graph model, cross-concern traversal, and scoping

**Status:** Approved
**Date opened:** 2026-06-18
**Date approved:** 2026-06-18
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

**Received:** 2026-06-18. **Source:** user-provided document `wellbe_graph_research_review.md` —
"WellBe Graph View — Research Review, Design Critique, and Spike Inputs." Product/design research input
(explicitly not legal/medical/regulatory advice). Faithful summary of its findings below; full reference
list ([S1]–[S30]) is in the source document.

**Executive verdict.** The whole-person, patient-controlled, source-linked graph concept is strategically
strong — especially because it is treated as an *operating surface* (every node/edge leads to evidence,
correction, follow-up, visit prep, or explanation), not a decorative visualization. But the design as
written is not yet robust: the core weakness is the tension between "show the whole person" and the known
limits of node-link comprehension. Network-visualization research finds major difficulty above ~50 nodes
(high density) and ~100 nodes (low density) [S2]; in health this is also a *safety* problem because users
infer cause/severity/urgency from proximity, line thickness, color, and centrality [S3]. **Recommendation:
approve the concept, but do not approve a raw full-patient graph as the primary default. Approve a
budgeted, explainable, task-first whole-person graph.**

**What is strongest (keep):** patient-controlled framing [S10]; concept-node resting granularity;
explicit naming of false causality as the #1 risk [S3]; provenance-first ("no orphan claims") aligned to
FHIR Provenance [S11]; action-radial converting view→workflow; diagnostic-safety-adjacent goals without
diagnosing [S8].

**Main weak points and required changes:**
1. **"Whole graph on entry" is a hazard.** Replace full-constellation default with a *progressive
   whole-person overview*: default = concern clusters + counts + open loops + high-confidence bridge
   concepts; mid = concept nodes in selected clusters; detail = captures/dates/evidence; explore = full
   galaxy as an explicit, non-default "Explore all connections" mode [S1, S2]. Principle: **whole-person
   model, not whole-network dump.**
2. **"Click expands full neighborhood" can explode.** Use *budgeted neighborhood expansion*: default
   top 5–12 related concepts above the confidence floor; captures behind an evidence drawer; "show more"
   in batches; always show hidden counts ("Showing 8 of 31"). API needs `node_budget`, `edge_budget`,
   `min_score_level`, `sort_by`, `cursor`.
3. **Relevance may be misread as severity.** Separate visual encodings — activity=brightness/opacity,
   evidence volume=ring/chip, user priority=pin, open loop=badge; never size alone. Persistent legend:
   "Layout shows activity and evidence in your records, not medical severity."
4. **Edge semantics too broad.** Don't show raw edge-type names (`may_explain`, `aggravates`, …).
   Adopt a *relationship vocabulary policy* with user-facing families: Recorded together · Around the
   same time · Part of the same care step · You linked these · A source you uploaded says · System
   candidate (hidden by default) · Investigation-only hypothesis.
5. **User-authored edges can reinforce false beliefs.** Store as a *separate evidence class*: visually
   distinct; do **not** auto-raise medical confidence; influence personalization/retrieval, not clinical
   interpretation; strengthen only when later supported by source evidence/repeated patterns.
6. **Comparison overlays are high-risk.** Keep out of the core product and early phases; treat as a
   separate governed product (explicit opt-in, cohort definition, minimum cohort size, differential
   privacy/strong aggregation, no clinician/institution default access, no risk language, fairness/bias
   review).
7. **No measurement of false inference.** Add a *mandatory comprehension/safety test before launch* —
   track false-causality / false-severity / false-diagnosis rates; require ≥85–90% correct edge
   interpretation after legend+panel; re-test low health/graph-literacy users.

**Modeling & engineering recommendations.** Layered graph model (observation / concept / thread /
continuity / correction / investigation / external) with toggles; default shows observation/concept/
thread/continuity only [S6]. Normalize clinical concepts internally to standard vocabularies for dedup/
entity resolution (SNOMED CT [S21], LOINC [S22], RxNorm [S23], OMOP [S24]) — not user-facing.
Provenance as first-class data (FHIR Provenance / W3C PROV) [S11, S13]. **Split scoring** into three
separate concepts — evidence strength, recency/activity, user priority — never one composite readable as
medical risk. Default confidence floor: hide score levels 1–2; neighborhoods show 3–7; overview shows
5–7 only; plain slider labels ("Only strongest source-backed links" / "More links" / "Exploratory
links"). Cluster computation: hybrid precompute (from `belongs_to_thread` + entity resolution) + render-
time overlap; bridge nodes drawn once with cluster chips; no thread→thread edges; clusters are product
groupings, not clinical conclusions. Renderer: bakeoff **Sigma.js + Graphology** [S18, S20] (read-heavy,
WebGL, large) vs **Cytoscape.js** [S19] (rich interactions, compound nodes) at 30/120/300/800 nodes on
mobile/low-end/desktop. Frozen layout + local docking for new nodes.

**API recommendations (WEL-187).** Never return an unbounded full patient graph; authorize/scope-filter
*before* graph assembly; budgeted + cursor-based; server provides summaries and safety-copy keys.
Endpoints: `GET /v2/graph/person/overview`, `GET /v2/graph/nodes/{id}/neighborhood`,
`GET /v2/graph/edges/{id}/explanation`, `GET /v2/graph/nodes/{id}/evidence`,
`POST /v2/graph/corrections` · `/user-edges` · `/edges/{id}/dispute`, and layout endpoints
(`GET/PUT /v2/graph/layouts/current`, `POST /v2/graph/layouts/tidy`).

**Privacy / regulatory.** Consent maps to FHIR Consent [S12]. **Inference leakage**: a hidden node can
leak via a bridge edge or cluster shape (e.g. "oncology visit → hair loss"); mitigate by scope-filtering
nodes first, then recomputing edges/clusters on the scoped graph, and never rendering hidden counts
outside the viewer's grant. Watchpoints: FDA CDS / device-software boundary [S14, S15] (avoid diagnosis,
treatment, risk prediction, severity, med-change instructions), FTC Health Breach Notification Rule [S16],
HIPAA access [S17], EU AI Act [S28], Israel PPL Amendment 13 [S29].

**Evaluation & success metrics.** Comprehension / task / anxiety-calmness / renderer / clinician-clarity
tests; metrics across user understanding (correct/false-causality/false-severity rates, evidence-retrieval
success), product utility (% sessions ending in a loop action, visit-packet rate, closure rate, repeat
use), safety (anxiety change, C10 copy-violation catches, edges-without-provenance blocked), and technical
(render time, mobile FPS, response size, layout stability).

## Approaches considered

All three are grounded in the provided review.

- **A. Keep approved thread-scoped model (status quo).** Lowest risk for false causality and privacy
  leakage; structurally hides cross-concern relationships — the exact value the user wants. Rejected: it
  defeats the "second brain / see the whole person" goal.
- **B. Unified full-constellation default (the original spec, III.6 / III.5).** Maximizes "show
  everything." Rejected by the review as a usability *and* safety hazard at scale (hairball; cause/
  severity misread from density/centrality [S2, S3]); unbounded expansion is also a performance risk.
- **C. Progressive, budgeted, explainable whole-person graph (recommended).** Keeps the whole-person,
  cross-concern, source-linked, action-first model, but the *default* is a cluster overview with high-
  confidence bridges; expansion is budgeted with hidden counts; the full galaxy is an explicit explore/
  audit mode. Adds: relationship vocabulary policy, split scoring, layered model, scope-filter-before-
  assembly, comprehension/anxiety testing gate, and regulatory review. Best balance of the user's goal
  with safety, privacy, accessibility, and shippability.

## Decision

**Adopt Approach C in full, with every recommendation in the provided review.** WellBe pursues a
**whole-person ("second brain") graph model**, but the user-facing default is a **progressive, budgeted,
explainable** experience — not an unbounded full-patient node-link network. The full graph remains
available only through an explicit zoom/explore/audit mode. All graph elements must be source-linked,
scope-filtered (authorization *before* assembly), non-diagnostic, and **comprehension-tested for false
causality/severity before launch**.

This supersedes the thread-scoped default in `graph-query-api-contract.md` and the "full patient graph is
never shown / one-click-one-layer" stance in `research-brief-c6-graph-visualization.md`. Specifically
adopted:

1. Progressive whole-person overview as default; full galaxy = explicit explore/audit mode only.
2. Budgeted neighborhood expansion with hidden counts; captures behind an evidence drawer.
3. Separate visual encodings for activity / evidence volume / user priority; never size-alone; persistent
   "not medical severity" legend.
4. Relationship vocabulary policy (plain-language families); raw edge-type names never shown in the graph.
5. User-authored edges as a separate evidence class that never auto-raises medical confidence.
6. Split scoring: evidence strength · recency/activity · user priority (no single medical-risk-readable
   score). Default confidence floor (hide levels 1–2; overview 5–7; neighborhood 3–7).
7. Layered graph model with safe default layers; standard-vocabulary normalization internally.
8. Budgeted, scope-filtered, cursor-based API with server-side summaries and safety-copy keys; the named
   endpoint set is the WEL-187 contract direction.
9. Scope-filter-before-assembly; no hidden counts outside grant (inference-leakage mitigation).
10. Renderer bakeoff (Sigma.js+Graphology vs Cytoscape.js) at 30/120/300/800 nodes; frozen + local docking.
11. Cross-patient comparison overlays out of MVP; separate governed product.
12. Mandatory comprehension/anxiety testing gate + success metrics before launch.

**Non-goals:** no diagnosis; no severity ranking; no causal claims; no raw full graph as default at dense
scale; no cross-patient comparison in MVP; no external medical evidence blended into the personal graph
without explicit context labels.

**Recommended MVP scope (Phase 1):** cluster overview · deduplicated concept nodes · concern clusters with
soft halos · high-confidence bridge nodes · edge confidence styling + floor · "why connected?" panel with
sources · node drawer (evidence count/dates/sources/thread membership) · budgeted local expansion · core
actions (Ask, Add capture, Correct, Add to visit packet, Hide/mute) · list/timeline equivalent · layout
stability · basic user-authored links (separate class) · accessibility basics. **Out of MVP:** cross-
patient overlays; disease-risk/severity overlays; full raw capture network on entry; unbudgeted expansion;
theory lens (until C14/C15 governance mature); external-evidence blending; AI medical interpretation
beyond source-cited hedged summaries.

**Roadmap order:** Phase 0 spike+prototype validation → Phase 1 personal source-linked graph (MVP) →
Phase 2 continuity/closure (ghost nodes, pending, visit packet) → Phase 3 narrative/accessibility
("explain my graph", summaries) → Phase 4 investigation/theory lens (after C14/C15 governance) → Phase 5
aggregate comparison overlays (separate governed, opt-in).

## Trade-offs accepted

- **Less "show everything" on entry** than the user's original instinct, in exchange for legibility,
  lower false-causality/anxiety risk, and shippability. The full galaxy is preserved as an explicit mode.
- **More engineering up front** (budgeted/scoped API, split scoring, vocabulary policy, scope-filter-
  before-assembly, renderer bakeoff) than a naive renderer over the existing thread endpoint.
- **A launch gate** (comprehension/anxiety testing ≥85–90% correct edge interpretation) that adds
  pre-launch work but de-risks the core ethical failure mode.
- **Internal vocabulary normalization** (SNOMED/LOINC/RxNorm/OMOP) adds ingestion/processing work (C4)
  but improves dedup and entity resolution.

## Implementation notes

- Canonical design doc updated to Approach C: `docs/implementation/ui/graph-view-system-design.md`.
- C6/C13 changes (cross-concern traversal, budgeted/scoped API, split scoring, cluster derivation) remain
  core-component work; the *contract direction* is decided here, but concrete schema/scoring changes still
  follow normal review and may warrant focused sub-spikes (e.g. scoring split, vocabulary mapping).
- Privacy: authorization/scope-filter must run before graph assembly (C1/C13/C17); no hidden counts
  outside grant.
- Safety: all payloads pass C10; relationship copy keys + legend served by the API, not invented client-
  side; comprehension/anxiety testing is a launch prerequisite.
- Phasing and MVP scope above flow into Jira (E5 Knowledge Graph epic + WEL-78 and new stories) via a
  triage pass.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
