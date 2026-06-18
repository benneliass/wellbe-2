# Design Spec — WellBe "Second Brain" Graph View

**Date:** 2026-06-18
**Status:** Proposed design (pending research spike + decision record before implementation)
**Owner:** User (brainstorm partner: agent)
**Primary Jira:** WEL-78 (graph visualization), relates to WEL-60, WEL-156, E5/WEL-16
**Supersedes (on approval):** the thread-scoped stance in `docs/decisions/graph-query-api-contract.md` and the "never one network / one-click-one-layer" stance in `docs/decisions/research-brief-c6-graph-visualization.md`
**Companion build spec (current/live behavior):** `docs/implementation/ui/graph-visualization-spec.md`

> ⚠️ This is a deliberate departure from the currently approved, thread-scoped graph design. It changes
> core‑component behavior (C6 Knowledge Graph, C13 API) and therefore must go through a research spike +
> decision record before any code is written. **No implementation until that is approved.**

---

## 1. The job to be done

A single, unified, per‑person **knowledge map that aggregates everything the user has captured** — the
visible form of WellBe's "Connect" layer (the cross‑time / cross‑source comparison engine that is the
product's moat). The model the user is reaching for is an **"AI second brain"** — like Obsidian's graph,
but for one person's health, where pieces of information link into a neuron‑like map and any element can
be expanded into everything related to it.

Crucially, the graph must do a **job**, not just look impressive: every node is a place to *act* inside
the Capture → Connect → Clarify → Close → Correct loop.

---

## 2. Core model (agreed in brainstorm)

1. **One unified map per person.** Not thread‑scoped silos — a single connected brain.
2. **Nodes = concepts (deduplicated entities).** "Headache" is one node even if mentioned 50 times; raw
   captures live *behind* the concept as evidence. The resting map shows concept nodes.
3. **Concerns = tinted cluster regions.** Health Threads / concerns render as soft tinted halos grouping
   their concepts. A concept belonging to two concerns (e.g. "Dizziness") sits between them and
   **bridges** the clusters — this is how connected threads are shown.
4. **Layout = organic but frozen.** Force‑directed neuron/constellation aesthetic computed **once**, then
   positions **locked** for spatial stability. Re‑layout only on explicit request.
5. **Click a node = expand the full neighborhood.** Reveals **both** related concepts **and** their
   captures. Prior expansions persist; each branch has one‑tap collapse; captures are toggleable per node.
6. **Entry = full constellation, relevance‑weighted.** Land on the whole brain; active/recent concerns
   bright and central, resolved/older ones dimmed toward the edges (still reachable, never hidden). A
   "zoom out" control gives the full galaxy.

## 3. Core improvements (all in scope for the core build)

1. **Confidence‑first edges.** Weak/speculative edges **hidden by default** behind one "show possible
   links" toggle. Dashed = system‑suggested, solid = confirmed; default lens = PotentialScore > 0.5.
2. **"Why connected?" on every edge.** Tap an edge → the evidence + score inputs (e.g. "co‑occurred 7×",
   "named together in ER note 3/15"). Connections are explainable — the antidote to false‑causality.
3. **Semantic zoom / level‑of‑detail.** Zoomed out = concern clusters; mid = concept hubs; zoomed in =
   concepts + captures. Not just pan/zoom.
4. **Action‑radial on every node.** Tap → ask · correct · mark resolved · add capture · prepare visit
   packet. This is what makes the graph *used*, not admired; it wires the graph into the operating loop.
5. **Incremental layout.** New concepts dock near their cluster centroid without moving existing nodes;
   a "tidy up" re‑layout is offered, never forced.
6. **User‑authored edges (C11).** The user can assert / confirm / deny a connection. User‑asserted vs
   system‑suggested edges are visually distinct; corrections feed back into C6 scoring.

## 4. Expansion roadmap (phased — post‑core)

1. **Time scrubber** — animate the graph growing over time; "what changed since last visit" lights up new
   nodes/edges. Uses `temporally_precedes`.
2. **Missing‑data ghost nodes (C9 + Missing‑Data engine)** — render *absence*: "result expected, not in",
   "no labs in 14 months", "referral with no follow‑up." Turns the map into a closure tool.
3. **Investigation & Theory lens (C14/C15)** — an Investigation highlights its subgraph; a Theory is a
   hypothesis node with explicit for/against evidence edges. The graph becomes the investigation
   workspace.
4. **Comparison overlays (the moat, consent‑gated)** — "me now vs me 6 months ago"; explicit opt‑in only,
   anonymized cohort patterns. Off by default; governed by the C1 cross‑patient gate.
5. **"Explain my graph" (Ask‑powered narration)** — plain‑language walkthrough of the map and what's open.
6. **Shareable subgraph → visit packet** — select a neighborhood and share it scoped/revocably; answers
   scoped sharing for a unified graph.

## 5. Non‑negotiables (retained from current safety posture)

- **No diagnosis.** Edge labels stay relationship‑language ("co‑occurs with", "may explain") — never
  "causes"/"diagnoses". `ConditionHypothesis` reads as uncertain. (Bible: `do_not_diagnose_rules.md`,
  `safety_model.md`.)
- **Every node/edge traceable to source.** One tap to the raw submission(s).
- **Accessibility.** Confidence/score never communicated by colour alone; ≥44px targets; reduced motion.
- **Calm, never alarmist.** Relevance‑weighting and confidence‑first rendering keep it from becoming an
  anxiety/false‑pattern machine.
- **Personal‑first & grant‑scoped.** The individual controls the map and any sharing; cohort/comparison is
  opt‑in only.

## 6. Risks this design accepts (and how it answers them)

| Risk | Mitigation built into the design |
|---|---|
| Hairball implies false causality / drives anxiety | Confidence‑first (weak edges hidden), "why connected?", relevance‑weighting, relationship‑only labels |
| "Pretty but useless" (Obsidian graph problem) | Action‑radial on nodes ties every node to the operating loop |
| Hard on mobile | Semantic zoom + a focus/ego mode for small screens (mobile treatment is an open question for the spike) |
| Frozen layout vs ever‑growing data | Incremental layout rule (dock new nodes, opt‑in tidy) |
| Statistical edges read as clinical truth | Confidence floor + dashed speculative + "why connected?" evidence |
| Unified graph fights scoped sharing | Shareable‑subgraph expansion (select neighborhood → scoped packet) |
| Distressing for chronically ill users | Relevance‑first, calm aesthetic, no full‑surface alarm states |

## 7. Open questions the research spike MUST answer (before implementation)

These touch core components and cannot be guessed:

1. **Cross‑concern traversal & scoping (C6/C13):** how to query and return a *multi‑concern* subgraph
   without leaking out‑of‑scope data; the new API shape (today's `/v2/graph/threads/{id}` is strictly
   single‑thread and structurally omits everything else, so it cannot serve this).
2. **Concept de‑duplication & cluster derivation:** how concept nodes and concern clusters are computed
   from C6 (`thread_ids`, entity resolution) and how "shared/bridge" nodes are identified.
3. **Relevance‑weighting model:** what drives bright‑central vs dim‑edge (recency, thread status, open
   loops) and how it stays calm/non‑diagnostic.
4. **Confidence thresholds & edge provenance contract:** default floor, what "why connected?" returns, and
   how user‑authored edges (C11) are represented and scored.
5. **Privacy for a unified graph:** object/property‑level authorization across concerns; what a shareable
   subgraph is allowed to contain.
6. **Performance/LOD at 200–300+ nodes** and the **mobile** interaction model.

## 8. Relationship to current state

- **Live today:** C6 store (WEL‑77), thread‑scoped read API `/v2/graph/threads/{id}` (WEL‑156). UI is a
  placeholder (WEL‑78).
- **This design changes:** scope (thread → whole‑person), expansion (one‑layer → full neighborhood),
  rendering (radial‑stable → frozen‑organic), and requires a **new/extended graph read API**.
- **Process:** research spike → decision record (superseding the thread‑scoped decisions) → Jira triage of
  E5/WEL‑78/WEL‑60/WEL‑156 → implementation. `docs/implementation/ui_vision.md` and the companion build
  spec are updated only **after** the decision is approved.

## 9. References

- Brainstorm mockups: `.superpowers/brainstorm/15678-1781811755/content/` (node‑granularity, concern‑
  representation, layout‑style, expansion‑behavior, entry‑navigation, composed‑concept‑v2)
- Current visual spec: `docs/decisions/research-brief-c6-graph-visualization.md`
- Live API contract: `docs/decisions/graph-query-api-contract.md`
- Data model: `docs/system-design/knowledge_graph.md`
- Companion build spec (current behavior): `docs/implementation/ui/graph-visualization-spec.md`
- Decision record (this change): `docs/decisions/whole-person-graph-model-scoping.md`
