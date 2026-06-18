# WellBe Graph View — Full System Design

**Status:** **Approved — Approach C (progressive whole-person graph).** Decision record `docs/decisions/whole-person-graph-model-scoping.md` approved 2026-06-18; research spike **WEL-187** resolved/closed. The whole-person model supersedes the prior thread-scoped default; the user-facing default is a *progressive, budgeted, explainable* graph (see Part XV).
**Date:** 2026-06-18 (rev. 2026-06-18 — adopted WEL-187 research)
**Primary Jira:** WEL-78 · relates to WEL-60, WEL-156, WEL-16 (E5 Knowledge Graph)
**Related docs:** design spec `docs/superpowers/specs/2026-06-18-second-brain-graph-design.md` · current/live build spec `docs/implementation/ui/graph-visualization-spec.md` · data model `docs/system-design/knowledge_graph.md` · live API `docs/decisions/graph-query-api-contract.md`

> **How to read this document.** It is self-contained. Part I sets the platform context. Part II explains what the graph view is and why it exists. Parts III–V are the full design (core model, improvements, expansion roadmap) with rationale and nuance. Parts VI–XIV cover safety, data model, interaction states, visual language, current state, spike answers, and governance. **Part XV is the operative refinement layer** adopted from the WEL-187 research — where it conflicts with an earlier part, Part XV (and the edited core sections) win. Where this design diverges from previously approved decisions, it is flagged explicitly.

## Part I — Platform context

### I.1 What WellBe is
WellBe is a **patient-centered Health Investigation OS** built on a sovereign personal core. The individual managing their own health (patient or caregiver) is **always the data controller** and the audience every feature must serve first. Clinicians, care teams, institutions, and researchers may use role-specific workspaces, but only under the individual's explicit, scoped, revocable grant — never by default, never as controller. Businesses (hospitals, employers) may *distribute* WellBe, but distribution never confers data access or control.

WellBe does **not diagnose**. It captures, connects, and surfaces patterns from data the user has submitted, always traceable to its source. Its purpose is singular: **one person understanding their own health better than they could without it.**

### I.2 The problem it addresses
Health information for a single person is fragmented across time, devices, documents, clinicians, and memory. Symptoms recur, results go un-chased, referrals stall, and the connective tissue between episodes is lost. The research that informed WellBe studied systemic clinical failures — missed diagnoses, handoff gaps, referral voids — but WellBe's answer is to **empower the individual within the system**, not to replace or become the clinical system.

### I.3 The operating loop
Everything in WellBe moves through one loop:

**Capture → Connect → Clarify → Close → Correct.**

- **Capture** — the user submits anything (a message, a photo of a lab, a document, a wearable export).
- **Connect** — WellBe extracts entities, links them to evidence, and relates them across time and source.
- **Clarify** — intelligence surfaces patterns, open questions, and what's worth attention.
- **Close** — pending results, referrals, and follow-ups are tracked to resolution.
- **Correct** — the user can correct anything; corrections layer over source data without destroying it.

### I.4 The moat — the comparison engine
WellBe's mechanism and differentiator is **cross-device, cross-time, cross-source, cross-domain synthesis**. Comparison is the *how*, not the *what*: the end is the user's understanding; comparison is the engine underneath. The graph view is the most direct visual expression of this engine.

### I.5 Core object — the Health Thread
The central product object is the **Health Thread**: one ongoing health concern (e.g. "Recurring headaches since February"), with a lifecycle state (`active_unresolved → explained → waiting_for_result → resolved → closed`). Threads organize the user's concerns; the graph view visualizes the entities and relationships within and across them.

### I.6 The component map (the parts the graph touches)
WellBe is built from numbered core components (C1–C17). The graph view primarily touches:

- **C6 Knowledge Graph** — per-patient typed nodes/edges with evidence-weighted scores; the substrate the graph view renders.
- **C13 API & Contract Layer** — the single external boundary; serves the graph read API and enforces access/provenance/non-diagnosis/audit.
- **C5 Evidence & Provenance** — every node/edge traces to a raw source ("no orphan claims").
- **C7 Health Thread Engine** — owns concerns/threads (the cluster identity in the graph).
- **C1 Trust & Consent / C17 Workspaces & Grants** — scope who may see which slice; govern sharing.
- **C9 Continuity & Closure**, **C11 Correction**, **C14 Investigation**, **C15 Theory**, **Intelligence Engines** — power expansion features (ghost nodes, user-authored edges, investigation lens, etc.).

## Part II — What the graph view is

### II.1 The feature, in one sentence
A single, unified, per-person **knowledge map that aggregates everything the user has captured** into a neuron-like web of concepts and their relationships — an **"AI second brain" for one's own health** — where any element can be expanded into everything related to it, and every connection is explainable and traceable to its source.

### II.2 The "second brain" thesis
The mental model is Obsidian's graph, adapted for health: pieces of information link into a map; you navigate by association; the structure itself reveals relationships you would not otherwise notice. But unlike a notes vault, this graph carries clinical-grade obligations — non-diagnosis, provenance, calm — that shape every design choice.

### II.3 The job to be done
The graph is **not** a screensaver. Its job is to let the user:
1. **See the whole picture** of their health at once — every concern and how they relate.
2. **Discover connections** across concerns and time (e.g. headaches relate to sleep and dizziness).
3. **Drill from any concept to its evidence** — the raw captures behind it.
4. **Act** from any node inside the operating loop (ask, correct, mark resolved, add capture, prepare a visit packet).

If the graph cannot drive an action or an understanding, it does not belong in the view.

### II.4 How it expresses the platform idea
The graph is the visible form of **Connect** — the comparison-engine moat made tangible. It is personal-first (one person's own data), source-linked (every node/edge traces to a submission), non-diagnostic (relationship language only), and user-controlled (the individual can correct, hide, author links, and scope sharing). It turns "WellBe remembers and relates everything for me" from a claim into something the user can *see and touch*.

### II.5 Why a graph at all (and the honest counter-argument)
Graphs are powerful for revealing structure, but the industry lesson is stark: **graph views are often admired and rarely used** (Obsidian's graph is the most-screenshotted, least-used view). WellBe accepts this risk deliberately and answers it by (a) tying every node to an action, (b) leading with relevance so the view is *useful*, not just complete, and (c) offering plain-language narration ("explain my graph"). A graph that only explores will be opened once; a graph that *does the loop* will be used.

### II.6 What it is NOT
- Not a diagnosis or risk engine. No node says "you have X"; no edge says "A causes B".
- Not a clinician EHR view or a population dashboard.
- Not a thread-scoped silo (this is the deliberate change from the prior design — see III.1).
- Not a force-directed toy that re-shuffles on every load (positions are stable — see III.4).

## Part III — The core design (with rationale & nuance)

### III.1 Unified whole-person map (the central change)
**Decision:** the graph is one unified map of the whole person — not a per-thread subgraph.
**Why:** the user's goal is to see "the overall cases of the person and their relations" and to discover that concerns connect (headache ↔ dizziness). A thread-scoped view structurally hides exactly the cross-concern relationships that are most valuable.
**What this changes:** the previously approved design (`research-brief-c6-graph-visualization.md`, `graph-query-api-contract.md`) made the graph **thread-scoped** and stated *"the full patient graph is never shown as a single network."* This design overrides that — which is why it is gated behind spike WEL-187.
**Nuance:** "unified" does not mean "undifferentiated." Structure is preserved through concern clusters (III.3) and relevance weighting (III.6), and safety is preserved through confidence-first rendering (IV.1). The aggregation is real but legible.

### III.2 Nodes = concepts (deduplicated)
**Decision:** the resting map shows **concept nodes** — deduplicated entities. "Headache" is one node even if mentioned 50 times; the 50 raw mentions live *behind* it as evidence.
**Why:** a literal "every piece of info is a node" map (true Obsidian vault) becomes an unreadable cloud at 50–300+ nodes/year, and in health it makes coincidental co-mentions look meaningful.
**Nuance (the hybrid):** clicking a concept can expand into its underlying captures (III.5), so total aggregation is preserved — every raw piece is *reachable*, just layered. Concepts are the resting granularity; pieces are one expansion away.

### III.3 Concerns = tinted cluster regions; shared concepts bridge them
**Decision:** Health Threads / concerns render as soft **tinted halo regions** grouping their concepts. A concept that belongs to two concerns (e.g. "Dizziness") sits between them and **bridges** the clusters.
**Why:** this is the answer to "but if threads are connected?" There is **no thread→thread edge** in the model; threads connect through **shared entities** (a node whose `thread_ids` contains both) and through candidate "may relate" links (WEL-141/142). Rendering concerns as regions keeps the map oriented; rendering the shared node as a bridge makes the connection visible and honest.
**Nuance:** clusters are a *visual* grouping computed at render time from C6 (`thread_ids` / entity resolution), not a new stored object. A node can belong to several clusters; it is drawn once, at the bridge.

### III.4 Layout = organic but frozen
**Decision:** a force-directed, organic neuron/constellation layout is computed **once**, then node positions are **locked**. Re-layout happens only on explicit user request ("tidy up").
**Why:** the neuron aesthetic is what the user wants; but live physics where nodes drift between visits reads as unstable/anxious in a health context and destroys spatial memory ("where was that thing?").
**Nuance:** "frozen" must be reconciled with ever-growing data — see IV.5 (incremental layout). New nodes dock near their cluster without disturbing existing positions.

### III.5 Click a node = expand the full neighborhood
**Decision (revised per WEL-187):** clicking a concept reveals a **budgeted neighborhood** — the top **5–12** related concepts above the confidence floor, with captures held **behind an evidence drawer** (not auto-shown). A **"show more"** control reveals weaker/older links in batches, and the view **always shows hidden counts** ("Showing 8 of 31 related items"). Prior expansions persist with one-tap per-branch collapse.
**Why:** the user wants to reach everything related — but the research [S2] shows "everything at once" explodes into a hairball, makes performance unpredictable, and inflates false meaning. Budgeting preserves reachability (nothing is hidden, only deferred) while keeping each step legible and safe.
**Nuance:** the budget is enforced server-side (`node_budget`, `edge_budget`, `min_score_level`, `sort_by`, `cursor` — see Part XV.6). "Complete evidence mode" is available for users who want full audit. This is where the original "show everything" instinct is most deliberately constrained.

### III.6 Entry = progressive whole-person overview (revised per WEL-187)
**Decision (revised):** the user lands on a **progressive cluster overview** — concern clusters, their counts, open loops, and a small set of **high-confidence bridge concepts** — *not* a full node-link constellation. Relevance still orders the view (active concerns prominent, resolved dimmed). The **full galaxy is preserved as an explicit "Explore all connections" / audit mode**, never the primary operating surface.
**Why (changed from the original "land on the full constellation"):** the research is unambiguous — a whole-network default is both a usability hazard (hairball above ~50–100 nodes [S2]) and a *safety* hazard (users infer cause/severity from density, centrality, and lines [S3]). The principle is **"whole-person model, not whole-network dump."** Overview-first → zoom/filter → details-on-demand [S1].
**Nuance:** relevance weighting derives only from neutral signals (recency, thread status, open loops, upcoming visit, user pin) and must **not** imply severity or diagnosis. A persistent legend states: *"This map shows activity and evidence in your records, not medical severity."* See Part XV.2 (split encodings) and XV.5 (relevance signals).

## Part IV — Core improvements (now part of the design)

These were brainstormed as enhancements and all approved into the core design.

### IV.1 Confidence-first edges (split scoring per WEL-187)
Edge *evidence strength* drives visual weight: strong/evidenced relationships render as solid, brighter, thicker lines; weak/candidate relationships render faint, thin, dashed. A **confidence floor** (adjustable) hides the weakest links by default (defaults in Part XV.5).
**Important (revised):** evidence strength must **not** be conflated into a single composite that users can read as medical risk. Scoring is **split into three independent concepts** — *evidence strength* (how well-supported in the user's sources), *recency/activity*, and *user priority* — each mapped to a *different* visual channel (XV.2). The underlying C6 `PotentialScore`/`score_level` informs evidence strength only.
**Why it matters most in health:** this is the single most important anti-harm mechanism. It prevents a coincidental co-mention from *looking* like a meaningful causal link [S3]. The visual weight of an edge must track the strength of its evidence, never exceed it — and never imply severity.

### IV.2 "Why are these connected?" + relationship vocabulary policy
Every edge is inspectable. Tapping an edge opens a panel with: a **plain-language relationship label** (never the raw edge-type name), the contributing signals, the **source captures** on both ends, any contradicting evidence, and a standard safety line ("This connection means these items were related in your records in the way shown above. It does not prove that one caused the other."). No connection is a black box.
**Relationship vocabulary policy (per WEL-187):** raw edge types (`may_explain`, `aggravates`, …) are **never shown** in the graph. They map to user-facing families: *Recorded together · Around the same time · Part of the same care step · You linked these · A source you uploaded says · System candidate (hidden by default) · Investigation-only hypothesis.* See Part XV.3.
**Tie to platform:** direct expression of C5 provenance — "no orphan claims" extended to relationships.

### IV.3 Semantic zoom / level-of-detail (LOD)
- **Zoomed out:** clusters collapse into labeled "concern blobs" with counts.
- **Mid zoom:** concept nodes appear.
- **Zoomed in:** captures, dates, and evidence chips appear.
This keeps the whole-person map legible at every scale and is the structural answer to overwhelm.

### IV.4 Action-radial menus (graph drives the loop)
Long-press / right-click a node opens a radial menu of loop actions: **Ask about this · Add a capture · Mark resolved · Correct this · Add to visit packet · Hide.** This is what turns the graph from a viewer into an operating surface, and it is the primary defense against the "admired but unused" failure mode.

### IV.5 Incremental layout (reconciles "frozen" with "growing")
New nodes from new captures **dock near their cluster** using a local force pass; existing node positions are preserved. The map grows like an accreting organism rather than re-shuffling. Spatial memory is protected; full re-layout is opt-in only.

### IV.6 User-authored edges (C11 correction)
The user can **assert a connection** the system missed ("these two are related") and **dispute** one it inferred. User-authored edges are visually distinct and are first-class corrections layered over source data — never destroying inferred edges, always traceable.
**Important (revised per WEL-187):** user-authored edges are a **separate evidence class** and must **not** auto-raise medical confidence. "You linked these" is kept distinct from "records show these often appeared together." They influence **personalization and retrieval**, not clinical interpretation, and only strengthen when later supported by source evidence or repeated patterns. This prevents the graph from reinforcing confirmation bias or health anxiety.
**Tie to platform:** this is **Correct** in the operating loop, applied to the graph.

## Part V — Expansion roadmap (phased, post-core)

All six were approved as desired direction. They are sequenced *after* the core ships and each may carry its own spike where it touches a core component.

| # | Idea | What it does | Primary component | Notes / guardrails |
|---|------|--------------|-------------------|--------------------|
| 1 | **Time scrubber** | A timeline slider replays how the graph grew — nodes/edges appear as captured. Reveals temporal sequence (what came before what). | C6 + intelligence | Sequence ≠ causation. Must label as chronology, never as cause. |
| 2 | **Missing-data ghost nodes** | Dotted "expected but absent" nodes — an ordered lab with no result, a referral with no follow-up. Surfaces open loops. | C9 Continuity & Closure | Framed as "still open / worth chasing," never as alarm. Drives Close. |
| 3 | **Investigation / Theory lens** | Overlay the active Investigation or Theory: highlight evidence-for / evidence-against a working theory across the map. | C14 Investigation, C15 Theory | Theory carries safety level; non-diagnostic framing enforced by C10. |
| 4 | **Comparison overlays** | The moat made visual: "people with a similar pattern often also tracked X." Opt-in, consent-gated, aggregate-only. | Moat + C1/C17 | **Default off.** Cross-patient is always explicit user opt-in. Never institution-enabled. |
| 5 | **"Explain my graph"** | Ask narrates the map in plain language: "Your headaches connect to sleep and dizziness; here's why." | Ask / intelligence + C10 | Non-diagnostic, source-cited narration. Lowers the graph-literacy barrier. |
| 6 | **Shareable subgraph → visit packet** | Select a cluster and export a clean, source-linked subgraph into a doctor/visit packet. | Visit packets + C17 grants | User-controlled share; the "bring this to my doctor" payoff. |

**Sequencing rationale:** 1, 2, 5 deepen the *personal* understanding loop and should come first; 3 builds on Investigation/Theory maturity; 6 connects to the existing visit-packet feature; 4 (comparison) is the highest-value but highest-governance item and ships last, fully consent-gated.

## Part VI — Safety, ethics & non-negotiables

These constraints are fixed regardless of design. The design must honor every one.

### VI.1 No diagnosis, no asserted causality
- No node asserts a condition the user does not have ("you have X").
- **No edge says "A causes B."** Causal-adjacent relationships use hedged language only (`may_explain`, "may relate to," "often noted around the same time").
- Severity, risk scores, and prognosis are never rendered.
- Enforced by **C10 Safety & Governance Gate** on every payload that reaches the view.

### VI.2 Traceability ("no orphan claims")
Every node and every edge must trace to a raw source the user submitted. If it can't be sourced, it isn't shown. "Why connected?" (IV.2) operationalizes this.

### VI.3 The false-causality risk is the core ethical risk
A graph's visual language *implies* causation by adjacency and lines. In health this can create false beliefs and anxiety. The design's answers: confidence-first edges (IV.1), hedged relationship vocabulary (VI.1), explicit "why connected" provenance (IV.2), and the confidence floor that hides the weakest links.

### VI.4 Calm, non-alarming presentation
Color, motion, and copy must reduce anxiety, not amplify it. No red "danger" coding of health states; no aggressive pulsing; ghost/open-loop nodes are framed as "worth a follow-up," never as alarms. Resolved concerns dim gently — never disappear or feel "deleted."

### VI.5 Personal-first & privacy
One person's own data by default. No cross-patient or aggregate layer without that individual's explicit, scoped opt-in (V.4). Sharing a subgraph (V.6) is a user-initiated, grant-scoped action governed by C1/C17. An institution distributing WellBe gains no access to the graph.

### VI.6 Accessibility
The graph must not be the *only* path to any information — a list/timeline equivalent always exists. Color is never the sole carrier of meaning (pair with shape/label/weight). Keyboard navigation, screen-reader summaries, and "explain my graph" (V.5) are accessibility features as much as features.

## Part VII — Risks & mitigations

| Risk | Severity | Mitigation in this design |
|------|----------|---------------------------|
| **False causality** — lines/adjacency imply cause | High | Confidence-first edges (IV.1); hedged vocabulary (VI.1); "why connected" provenance (IV.2); confidence floor |
| **Overwhelm / hairball** at scale | High | Progressive cluster-overview default (III.6, XV.1); budgeted expansion with hidden counts (III.5); concept-level resting view (III.2); semantic zoom (IV.3) |
| **Anxiety** from seeing everything at once | High | Calm visual language (VI.4); dim-not-delete; ghost nodes framed as follow-ups; no severity coding |
| **"Admired but unused"** (Obsidian lesson) | High | Action-radial menus tie every node to the loop (IV.4); "explain my graph" (V.5); relevance-led usefulness |
| **Spatial instability** between visits | Medium | Frozen layout (III.4) + incremental docking (IV.5) |
| **Performance** at 300+ nodes / mobile | Medium | LOD/cluster collapse (IV.3); server-side scoping; resolve in spike (canvas/WebGL renderer choice) |
| **Scope/governance** — overrides approved thread-scoped design | Resolved | WEL-187 spike resolved; decision record approved 2026-06-18 (Approach C) |
| **Cross-patient privacy** (comparison overlay) | High | Default off; explicit opt-in; aggregate-only; never institution-enabled (V.4, VI.5); **out of MVP** (XV.9) |
| **Misread relevance as severity** | High | Split visual encodings (XV.2); persistent "not medical severity" legend (XV.8) |
| **Privacy inference-leakage** via bridge edges / cluster shape | High | Scope-filter **before** graph assembly; recompute edges/clusters on the scoped graph; no hidden counts outside grant (XV.7) |
| **False-inference (unmeasured)** | High | Mandatory comprehension/anxiety testing gate before launch; ≥85–90% correct edge interpretation (XV.10) |
| **Regulatory boundary creep** | High | Governance gates for theory/comparison; per-market legal review — FDA CDS, FTC, HIPAA, EU AI Act, IL PPL Am.13 (XV.11) |

**Risks explicitly accepted (pending mitigation in the spike):** higher rendering complexity than a thread-scoped view; the unified map raises the false-causality bar; relevance weighting needs a defensible, non-diagnostic signal definition.

## Part VIII — Data model reference (C6)

Canonical source: `docs/system-design/knowledge_graph.md`. The graph view renders this model; it does not invent node/edge types.

### VIII.1 Node types
The personal graph is per-patient and typed:

- **Clinical:** `symptom`, `condition`, `medication`, `lab_result`, `imaging_result`, `procedure`, `diagnosis`, `hypothesis`
- **Care pathway:** `visit`, `referral`, `referral_appointment`, `pending_item`, `practitioner`, `care_setting`
- **Personal context:** `body_region`, `mood_state`, `baseline_deviation`, `wearable_metric`, `document`
- **External context:** `environmental_event`, `public_health_signal`
- **Investigation:** `investigation`, `theory`
- **Meta:** `health_thread`, `story_memory_entry`, `patient_correction`

Each node carries: `privacy_class`, `confidence`, `evidence_level`, `source_context_ids[]`, `created_at`, `last_updated_at`.

### VIII.2 Edge types
`co_occurs_with`, `temporally_precedes`, `may_explain`, `contradicts`, `confirms`, `aggravates`, `resolves`, `part_of`, `derived_from`, `belongs_to_thread`, `evidence_for`, `evidence_against`, `investigates`, `relevance_link`.

Each edge carries: `PotentialScore` (0–100), `score_level` (7 levels), `source_context_ids[]`, `confidence`, `is_user_corrected`.

### VIII.3 Mapping the model to the design
- **Concept node (III.2)** = a resolved entity node; its `source_context_ids[]` are the underlying captures revealed on expansion (III.5).
- **Concern cluster (III.3)** = nodes sharing a `belongs_to_thread` edge to the same `health_thread`; a bridge node has `belongs_to_thread` edges to two threads.
- **Edge weight (IV.1)** = `PotentialScore` / `score_level`; the confidence floor filters on it.
- **"Why connected" (IV.2)** = edge type + `source_context_ids[]` + `confidence`.
- **User-authored / disputed edges (IV.6)** = `is_user_corrected` / `patient_correction` nodes.
- **Ghost nodes (V.2)** = `pending_item` / `referral_appointment` with no resolving fact.
- **Investigation/Theory lens (V.3)** = `investigation`/`theory` nodes with `investigates` / `evidence_for` / `evidence_against` edges.

### VIII.4 Hard model constraints
- **`may_explain` is the strongest causal language.** No edge type asserts diagnosis or definite cause.
- **`contradicts` edges are preserved, not resolved** — the graph shows conflict honestly rather than hiding it.
- The **External Evidence Graph is a separate graph** and is never blended into the personal graph; it connects only via `relevance_link` as context.
- All scoring/auto-linking changes to C6 are core-component touches and require their own research spike.

## Part IX — Interaction model & states

### IX.1 Entry
Land on the relevance-weighted full constellation (III.6): active concerns bright/central, resolved dimmed/peripheral. A "zoom out" reveals the full galaxy; "tidy up" triggers opt-in re-layout.

### IX.2 Core interactions
- **Tap node** → select; show a side drawer (label, type, dates, evidence count, thread membership).
- **Tap node again / expand affordance** → reveal full neighborhood: related concepts + their captures (III.5), respecting the confidence floor.
- **Tap edge** → "why connected?" panel (IV.2).
- **Long-press / right-click node** → action-radial (IV.4): Ask · Add capture · Mark resolved · Correct · Add to visit packet · Hide.
- **Pinch / scroll** → semantic zoom across cluster → concept → capture LOD (IV.3).
- **Collapse control** → per-branch collapse to manage density.
- **Confidence-floor slider** → reveal/hide weaker edges.

### IX.3 States
- **Cold start (no data):** not an empty hairball — a calm prompt to capture, with one example concept. The graph earns its first nodes through Capture.
- **Sparse (a few concepts):** show all; no relevance dimming needed; encourage more capture.
- **Healthy (tens–low hundreds):** relevance weighting + clustering carry legibility.
- **Dense (300+):** LOD/cluster collapse default; expansion is local; full re-layout discouraged.
- **Mobile:** clusters-first; tap-to-expand; radial menu adapts to a bottom sheet; the list/timeline equivalent is one tap away (VI.6).

### IX.4 Always-available non-graph equivalent
Per VI.6, every node/edge is also reachable via list/timeline views. The graph is a lens, never a gate.

## Part X — Visual language

Aligned to WellBe's calm, personal-first aesthetic (see `docs/implementation/ui_vision.md`).

- **Layout:** organic neuron/constellation; frozen positions; soft tinted halos for concern clusters.
- **Nodes:** **never size-alone for mixed signals** (large reads as "serious"). Split channels: activity → brightness/opacity; evidence volume → ring count / chip; user priority → pin/star; open loop → small task badge. Shape/icon encodes node type so color is never the sole signal.
- **Edges:** weight/opacity/dash encode **evidence strength** only (not severity/activity); user-authored edges visually distinct; no red "danger" edges.
- **Color:** per-concern tints for clusters; relevance via brightness/saturation (active bright, resolved dim). No clinical red/green risk coding.
- **Motion:** gentle docking of new nodes (IV.5); no aggressive pulsing; transitions are slow and calm.
- **Typography & chrome:** consistent with the workspace shell (`TopBar`, `PageBody`); evidence chips and date labels appear only at deep zoom.

## Part XI — Current state vs target

- **Backend / API:** a thread-scoped read endpoint exists and is live — `GET /v2/graph/threads/{thread_id}` (see `docs/decisions/graph-query-api-contract.md`), returning neutral node-link JSON, access/provenance/non-diagnosis scoped at C13.
- **Frontend:** the web route `apps/web/app/(workspace)/graph/page.tsx` is a `ComingSoon` placeholder — no renderer is built yet.
- **Gap to this design (Approach C):**
  1. **API:** thread-scoped contract must extend to the budgeted, scope-filtered, summary-bearing endpoint set in XV.6 (`/v2/graph/person/overview`, `/nodes/{id}/neighborhood`, `/edges/{id}/explanation`, `/nodes/{id}/evidence`, corrections/user-edges, layout endpoints).
  2. **Renderer:** run the Sigma.js+Graphology vs Cytoscape.js bakeoff (XV.12) at 30/120/300/800 nodes; build frozen + local-docking layout.
  3. **Features:** progressive cluster overview, budgeted expansion with hidden counts, "why connected" + relationship vocabulary, split-channel encodings, confidence floor, action-radial, separate-class user-authored edges, list/timeline equivalent.
  4. **Safety/eval:** relationship-copy keys + legend served by API; comprehension/anxiety testing gate before launch.
- **Jira reality check:** several graph backend stories are implemented but their Jira status lags (Epics still "To Do" while child stories are "Done"). Status reconciliation is tracked separately from this design.

## Part XII — Spike (WEL-187) questions — answered

The spike is **resolved**. The six open questions were answered by the user-provided research (`wellbe_graph_research_review.md`) and adopted in the decision record. Summary of answers (detail in Part XV):

1. **Cross-concern query & scoping** → budgeted, scope-filtered, cursor-based views; authorize *before* assembly; server returns summaries + safety-copy keys; never an unbounded full graph (XV.6).
2. **Relevance weighting** → neutral signals only (recency, active-thread, open loop, upcoming visit, user pin, new evidence, pending correction); never severity/risk/prognosis (XV.5).
3. **Cluster computation** → hybrid precompute (from `belongs_to_thread` + entity resolution) + render-time overlap; bridge nodes drawn once with cluster chips; no thread→thread edges (XV.4).
4. **Confidence floor & edge exposure** → hide score levels 1–2 by default; overview shows 5–7; neighborhoods 3–7; budgeted expansion + "show more" (XV.5).
5. **Layout & performance** → Sigma.js+Graphology vs Cytoscape.js bakeoff at 30/120/300/800 nodes; frozen + local docking (XV.12).
6. **User-authored edges** → separate evidence class; influences personalization/retrieval, not medical confidence; strengthens only with later source support (IV.6, XV.3).

## Part XIII — Governance & status

- **This design supersedes** the thread-scoped framing in `docs/decisions/research-brief-c6-graph-visualization.md` and `docs/decisions/graph-query-api-contract.md` — specifically the rule that "the full patient graph is never shown as a single network." **This override is now in effect** (decision approved 2026-06-18).
- **Decision record (Approved):** `docs/decisions/whole-person-graph-model-scoping.md` (Approach C).
- **Spike:** **WEL-187 — resolved/closed**; WEL-78 unblocked, `re-eval:clean`.
- **Bible-file note:** this document does not modify any bible file. Adopting Approach C did not require a bible change; if future implementation implies changes to `system_design.md` or safety docs, the doc-governance re-eval protocol runs first.
- **Implementation status:** **unblocked.** Build proceeds against Approach C — starting with Phase 0 (prototype + renderer bakeoff + comprehension testing) then the Phase 1 MVP scope (XV.9). New stories flow into the E5 Knowledge Graph epic via triage.

## Part XIV — References

- Design spec (brainstorm output): `docs/superpowers/specs/2026-06-18-second-brain-graph-design.md`
- Decision record (Open): `docs/decisions/whole-person-graph-model-scoping.md`
- Prior approved (superseded by Approach C): `docs/decisions/research-brief-c6-graph-visualization.md`, `docs/decisions/graph-query-api-contract.md`
- Research input (user-provided, WEL-187): `wellbe_graph_research_review.md` (refs [S1]–[S30])
- Live API contract: `docs/decisions/graph-query-api-contract.md`
- Data model: `docs/system-design/knowledge_graph.md`
- Intelligence engines: `docs/system-design/intelligence_engines.md`
- UI vision: `docs/implementation/ui_vision.md`
- Current build spec: `docs/implementation/ui/graph-visualization-spec.md`
- Component map: `docs/architecture/component-map.md`
- Jira: WEL-78 (graph view), WEL-187 (spike), E5 Knowledge Graph epic

## Part XV — Research-driven refinements (WEL-187, adopted 2026-06-18)

This part records the concrete decisions adopted from the user-provided research review. It is the operative spec where it conflicts with earlier parts. **Guiding principle: whole-person model, not whole-network dump — progressive, budgeted, explainable, source-linked, scope-filtered, non-diagnostic, and comprehension-tested before launch.**

### XV.1 Progressive disclosure levels
- **Overview (default):** concern clusters, counts, open loops, high-confidence bridge concepts only.
- **Cluster detail:** concept nodes within a selected cluster.
- **Detail:** captures, dates, evidence chips, source previews.
- **Explore/audit:** full galaxy — explicit, labeled "Explore all connections," never the default.

### XV.2 Split visual encodings (no signal conflation)
Activity → brightness/opacity · evidence volume → ring/chip · user priority → pin/star · open loop → task badge. **Never node size alone** for mixed signals. Edge thickness = evidence strength only.

### XV.3 Relationship vocabulary policy
User-facing families, mapped from C6 edge types, shown instead of raw type names:
1. **Recorded together** — same capture/document/visit (`co_occurs_with`).
2. **Around the same time** — temporally close, no causal claim (`temporally_precedes` shown neutrally).
3. **Part of the same care step** — lab/referral/result/visit/follow-up (`part_of`, care-pathway links).
4. **You linked these** — user-authored (separate class).
5. **A source you uploaded says** — source-linked clinical statement (`confirms`/`may_explain` only when a source states it).
6. **System candidate** — weak/system-inferred, hidden by default.
7. **Investigation-only hypothesis** — visible only in the theory/investigation lens.

`contradicts` surfaces as "conflicting information" (preserved, not resolved). `may_explain` never renders as "causes."

### XV.4 Cluster computation
Hybrid: precompute membership/anchors (daily or post-ingestion) from `belongs_to_thread` + entity resolution; resolve overlap and current filters at render time. A node may belong to several clusters; bridge nodes are drawn **once** with small cluster chips. **No thread→thread edges.** Clusters are product groupings around Health Threads — **never** clinical conclusions (no "root cause group" labels).

### XV.5 Split scoring + confidence floor
Three independent scores, never one medical-risk composite:
- **Evidence strength** (drives edge weight): source count, source diversity, explicitness, temporal recurrence, extraction confidence; penalties for contradiction and staleness. Ranking/filtering only — copy says "more evidence in your records," not "more likely."
- **Recency/activity.**
- **User priority** (pin/dispute).

**Relevance** (for ordering, neutral): active-thread, recency, open loop, upcoming visit, user pin, new evidence, pending correction. Never severity/risk/prognosis. User-facing label "active in your records" / "worth reviewing now."

**Default confidence floor:** hide `score_level` 1–2; neighborhoods show 3–7; overview shows 5–7 only unless the user lowers the slider. Slider labels: "Only strongest source-backed links" / "More links" / "Exploratory links" (avoid "low confidence" as the only label). User-authored edges always shown when requested, visually separate.

### XV.6 API contract direction (C13)
Principles: never return an unbounded full patient graph; **authorize/scope-filter before assembly**; budgeted + cursor-based; server provides summaries and **safety-copy keys** (client does not invent wording). Endpoints:
- `GET /v2/graph/person/overview?node_budget&edge_budget&min_score_level&include_resolved=dimmed` → clusters, top bridges, open loops, high-confidence edges, summary cards, layout anchors, provenance counts.
- `GET /v2/graph/nodes/{id}/neighborhood?radius=1&node_budget&edge_budget&min_score_level&include_captures=false&cursor` → related concepts, edge explanations, hidden counts.
- `GET /v2/graph/edges/{id}/explanation` → plain label, contributing signals, source captures, contradicting evidence, copy guardrails.
- `GET /v2/graph/nodes/{id}/evidence?source_type&cursor` → captures behind a concept.
- `POST /v2/graph/corrections` · `POST /v2/graph/user-edges` · `POST /v2/graph/edges/{id}/dispute`.
- `GET/PUT /v2/graph/layouts/current` · `POST /v2/graph/layouts/tidy`.

Response carries `scope`, `budgets` (incl. `hidden_node_count`/`hidden_edge_count` — only for data the viewer may know exists), `legend`, `clusters`, `nodes`, `edges`, `open_loops`, `layout`.

### XV.7 Privacy: scope-filter before assembly (C1/C13/C17)
Authorization runs **before** graph assembly. A hidden node can still leak via a bridge edge or cluster shape (e.g. "oncology visit → hair loss"); therefore scope-filter nodes first, then **recompute edges/clusters on the scoped graph**, and never render hidden counts for data outside the viewer's grant. Maps to FHIR Consent.

### XV.8 Layered graph model
Toggleable layers: observation · concept · thread · continuity · correction · investigation · external. **Default visible:** observation/concept/thread/continuity only. The external evidence graph stays separate and connects only via explicit `relevance_link` context.

### XV.9 MVP scope (Phase 1) and exclusions
**Include:** cluster overview · deduplicated concept nodes · concern clusters (soft halos) · high-confidence bridge nodes · edge confidence styling + floor · "why connected?" with sources · node drawer · budgeted local expansion · actions (Ask, Add capture, Correct, Add to visit packet, Hide/mute) · list/timeline equivalent · layout stability · basic user-authored links (separate class) · accessibility basics.
**Exclude from MVP:** cross-patient comparison overlays · disease-risk/severity overlays · full raw capture network on entry · unbudgeted expansion · theory lens (until C14/C15 governance mature) · external-evidence blending · AI medical interpretation beyond source-cited hedged summaries.

### XV.10 Mandatory comprehension/anxiety testing gate (pre-launch)
Before launch: comprehension test (show edges, ask "what does this mean?"; track false-causality / false-severity / false-diagnosis rates; require **≥85–90%** correct edge interpretation after legend+panel; re-test low health/graph-literacy users) and an anxiety/calmness test (pre/post self-rated anxiety, perceived control, clinician-discussion confidence). Success metrics span understanding, product utility (% sessions ending in a loop action, visit-packet/closure rates, repeat use), safety (anxiety change, C10 copy-violation catches, edges-without-provenance blocked), and technical (render time, mobile FPS, response size, layout stability).

### XV.11 Regulatory watchpoints (per-market legal review)
FDA CDS / device-software boundary (no diagnosis, treatment, risk prediction, severity, med-change instructions); FTC Health Breach Notification Rule; HIPAA access rights; EU AI Act (if EU); Israel PPL Amendment 13 (if IL users). Theory and comparison phases carry the most regulatory weight.

### XV.12 Renderer bakeoff (Phase 0)
Prototype **Sigma.js + Graphology** (read-heavy, WebGL, large graphs; more custom work for compound nodes/overlays/accessibility) vs **Cytoscape.js** (rich interactions, compound nodes, graph algorithms; validate dense-mobile performance) at 30/50, 120/250, 300/800, 800/2,500 node/edge scales on mid-range mobile, low-end laptop, and desktop. Measure render time, pan/zoom FPS, label legibility, edge hit accuracy, memory, accessibility-workaround complexity, and ease of freeze/incremental layout. Favor Sigma if read-heavy/large dominates; Cytoscape if compound nodes/rich interaction dominate.

### XV.13 Safety copy
**Use:** "Recorded together," "Appeared around the same time," "Part of the same care step," "You linked these," "A source you uploaded says…," "WellBe noticed this pattern in your records," "Worth asking about." **Avoid:** "causes," "proves," "diagnoses," "risk," "danger," "high severity," "this means," "AI found the cause." Persistent legend: *"This map shows how items appear in your records. Brighter items are more active or recent, not more medically serious. Lines show recorded relationships or patterns, not proof of cause."* System-inferred edges are framed as "WellBe noticed these appeared together in your records," never "AI discovered."

