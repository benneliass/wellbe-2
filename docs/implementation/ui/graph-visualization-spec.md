# WellBe — Graph Visualization Build Spec (WEL-78)

> **Purpose of this file.** A single, copy‑paste‑ready specification for building the WellBe graph
> visualization. It consolidates the approved visual design, the data model, the live read API,
> the platform context, and the product/safety constraints so a frontend developer or UI/UX
> designer can start work without chasing references.
>
> **Status:** The graph **data + read API are built and live** (WEL‑156, Done). The **visual layer is
> not built** — `apps/web/app/(workspace)/graph/page.tsx` is a "Coming Soon" placeholder. This spec
> describes what replaces that placeholder (Jira **WEL‑78**, To Do).
>
> **Source documents this consolidates:**
> - `docs/decisions/research-brief-c6-graph-visualization.md` (authoritative visual spec)
> - `docs/system-design/knowledge_graph.md` (data model)
> - `docs/decisions/graph-query-api-contract.md` (the live read API contract — Approved)
> - `docs/implementation/ui_vision.md` (platform UI direction)
> - Jira: WEL‑78 (viz), WEL‑60 (timeline + evidence graph), WEL‑156 (read API), WEL‑141/142 (relevance candidates)

---

## 1. Platform context — what WellBe is, and where the graph fits

WellBe is a **patient‑centered Health Investigation OS** built on a sovereign personal core. The
**individual managing their own health is always the data controller**. WellBe does **not diagnose** —
it captures, connects, and surfaces patterns from data the user has submitted, always traceable to its
source.

The product runs an operating loop: **Capture → Connect → Clarify → Close → Correct.** The core object
is the **Health Thread** — one ongoing health concern (e.g. "Recurring headaches since February"), with
a lifecycle state.

**The graph is WellBe's "Connect" surface made visible.** Behind it sits the C6 Knowledge Graph: a
per‑patient network of health entities (symptoms, tests, meds, visits, documents, pending items, etc.)
and the evidence‑weighted relationships between them, all built from this one person's history. The
intelligence engines traverse this graph to surface patterns; the graph view lets the *user* see and
navigate the same connected picture, scoped to one thread at a time, with every node and edge traceable
back to a raw submission.

**Component ownership (who produces what the graph shows):**

```
C4 Processing      extracts entities/facts from raw events
  → C5 Evidence    links every fact back to its C2 raw source (no orphan claims)
  → C7 Thread      decides whether to create/update a Health Thread (the graph root)
  → C6 Graph       stores Thread root node + entity nodes + typed, scored edges
  → C13 API + UI   renders the expandable graph and the evidence drawer (THIS SPEC)
```

**Where it lives in the app:** the graph is reached from a thread (the "Open the graph" / "Explore
connections" action) and from the Deep Dive area. It is **not** the home screen. Home leads with
continuity (what changed, open loops, active threads); the graph is a depth surface you enter from a
thread or investigation. See `ui_vision.md` §"Timeline and Evidence Graph" and §"Progress Over Pages".

---

## 2. Current state & scope of this work

| Piece | Status | Where |
|---|---|---|
| C6 Knowledge Graph store (nodes/edges/scoring) | **Built** (WEL‑77) | `backend/packages/c6_graph` |
| Thread‑scoped graph **read API** | **Built & live** (WEL‑156) | `GET /v2/graph/threads/{thread_id}` |
| Graph **visualization UI** | **Not built** (WEL‑78) | `apps/web/app/(workspace)/graph/page.tsx` is a placeholder |
| Relevance‑candidate model + review UX | To Do (WEL‑141/142) | out of scope here, design‑compatible |

**This spec covers WEL‑78:** replace the placeholder with the real graph view, wired to the live API.

---

## 3. The live read API (what you call)

**Endpoint:** `GET /v2/graph/threads/{thread_id}`
**Auth (local dev):** header‑based. Send `X-Wellbe-Patient-Id` and `X-Wellbe-Actor-Id` (the seeded dev
patient is `de7a0000-0000-4000-8000-000000000001`). In production this is the C1/ZITADEL session.
**Base URLs (local):** API at `http://api.localhost`, web at `http://app.localhost`.

**Query parameters (all server‑enforced bounds):**

| Param | Type | Default | Ceiling | Meaning |
|---|---|---|---|---|
| `max_nodes` | int | 200 | 500 | max nodes returned |
| `max_edges` | int | 400 | 1000 | max edges returned |
| `node_types` | string[] | — | — | filter to these node types (allowlisted) |
| `edge_types` | string[] | — | — | filter to these edge types (allowlisted) |

**Response (`schema_version: c13.graph.subgraph.v2`) — neutral node‑link JSON:**

```json
{
  "schema_version": "c13.graph.subgraph.v2",
  "thread_id": "ba37e6ff-3a15-49ab-a9b8-f87e38548d46",
  "nodes": [
    {
      "id": "uuid",
      "type": "Symptom",
      "label": "Fatigue",
      "status": "active",
      "attributes": {
        "first_seen_at": "2026-03-08T...",
        "last_seen_at": "2026-04-22T...",
        "source_type": "user_message"
      }
    }
  ],
  "edges": [
    {
      "id": "uuid",
      "source": "uuid",
      "target": "uuid",
      "relation": "co_occurs_with",
      "evidence_weight": 0.82,
      "attributes": { "source_ref_id": "uuid" }
    }
  ],
  "page_info": {
    "has_more": false,
    "next_page_token": null,
    "node_count": 12,
    "edge_count": 18,
    "truncated": false
  }
}
```

**Contract rules you must honor (from the approved decision):**
- **Neutral node‑link payload** — adapt **client‑side** to Cytoscape / Sigma. Do **not** assume a
  viz‑native server shape; C13 is deliberately library‑agnostic.
- `edges[].relation` uses the **constrained vocabulary** (see §6). `may_explain` is the strongest
  causal‑adjacent relation that can ever appear. `causes`/`diagnoses`/`proves`/`rules_out` cannot.
- `evidence_weight` is the edge's PotentialScore (0–1). Encode it with **thickness + opacity + a text
  label** — never colour alone (accessibility).
- Provenance in the payload is a **compact summary only** (`source_type`, `source_ref_id`,
  `evidence_weight`). **Full provenance / evidence trail is fetched from a separate scoped endpoint** —
  do not expect raw source text inline.
- **Out‑of‑thread nodes are structurally omitted** by the server. The view shows only this thread's
  subgraph; never try to render adjacency the API didn't return.
- Errors are RFC 9457 problem+json. A non‑owned/absent thread returns **404** (existence is never
  disclosed). Unknown `node_types`/`edge_types` return **422**.
- `page_info.truncated = true` means limits were hit — show a "show more"/expand affordance.

**Known current gap:** the seeded threads currently return `0 nodes / 0 edges` (C6 auto‑linking hasn't
populated graph content for the seed data). The contract is correct and live; you'll need populated
graph content (or fixtures shaped like the response above) to render anything meaningful. Build against
the schema with fixtures, then point at live data.

---

## 4. Visual design (authoritative — from the approved consultation brief)

### 4.1 Layout — decided
- **Expandable radial / mind‑map layout. NOT force‑directed.**
- **Stability is a hard requirement** — nodes must not jump/re‑flow when a branch opens. The user's
  spatial memory of "what is where" must survive every interaction.
- **Temporal order is NOT a layout axis.** Time is shown via edge semantics (`temporally_precedes`,
  edge labels) and the evidence‑drawer timeline. The radial layout is spatial, not chronological.

### 4.2 Two levels of view
1. **Health Map (top level)** — all active Health Threads shown as separate cards / root nodes. The
   **full patient graph is never shown as one network.** Clicking a thread card opens its Thread Graph.
   ```
   Health Map
     [Recurring headaches]   [Post-viral fatigue]   [Stomach pain]   [Back pain]
     click one → opens its Thread Graph
   ```
2. **Thread Graph** — the expandable radial view for one thread (the main build target).

(Per WEL‑78, a separate **investigation landscape** uses Sigma.js for broader exploration — see §8.
The Cytoscape **thread view** is the primary deliverable.)

### 4.3 Staged expansion — the four‑layer model
**Hard rule: one click = one layer only. One click must never reveal the whole graph.**

| State | User action | What appears |
|---|---|---|
| Layer 0 | Open thread | The **Thread root** node only (e.g. "Recurring headaches") |
| Layer 1 | Click root | **Category** nodes: Symptoms · Tests & labs · Medications · Visits & referrals · Documents · Pending items |
| Layer 2 | Click a category | The actual **entity** nodes inside it (Headache, Fatigue, CBC, MRI planned…) |
| Layer 3 | Click an entity | Its **directly connected details** (CBC → Haemoglobin 11.2, WBC normal, Lab PDF) |
| Layer 4+ | Keep clicking | Only direct neighbours of the clicked node. Existing open branches stay open unless collapsed. |

> **Category nodes are virtual UI groupings, not stored graph nodes.** Group the API's nodes by `type`
> under these headings at render time. Count badges = count of nodes of that type in this thread.
>
> | Category label | Node `type` values it groups |
> |---|---|
> | Symptoms | `Symptom` |
> | Tests & labs | `LabTest`, `LabResult`, `Finding` |
> | Medications | `Medication` |
> | Visits & referrals | `Visit`, `Referral` |
> | Documents | `Document` |
> | Pending items | `PendingItem` |

### 4.4 Node visual hierarchy

| Node tier | Size | Visual treatment |
|---|---|---|
| **Health Thread root** | Largest | Central, solid border, **status badge** ("Active — Unresolved"), title + last updated + summary counters |
| **Category** | Medium | Count badge ("Symptoms — 4 items"), expand/collapse affordance |
| **Health entity** | Smaller | Type‑specific icon + label |
| **ConditionHypothesis** | Smaller | **Dashed border + hypothesis badge + muted background + literal text "Hypothesis — not diagnosis"** |

Thread root status badge reads `HealthThread.status` (one of `active_unresolved`, `explained`,
`waiting_for_result`, `resolved`, `closed`).

### 4.5 Edge encoding (PotentialScore → visual)
- **Thickness + opacity + a readable text label** (`strong` / `medium` / `weak`).
- Example: a strong edge is thick, fully opaque, labelled "strong"; a weak edge is thin, faded,
  labelled "weak".
- **Never colour alone** (colour‑blind accessibility is a hard rule).
- Edge relation label uses the constrained vocabulary (§6) and must never read like a clinical
  conclusion.

### 4.6 Special cases
- **Cross‑thread shared node** → badge on the node: **"Appears in N threads"** or "Shared with [Thread
  name]". Cross‑thread expansion is an **optional action, not the default view**.
- **Contradiction** (`contradicted_by` edge) → **distinct warning edge style** + warning badge on the
  conflicted node. The resolution action ("mark wrong", "merge", "hide") lives **in the evidence
  drawer**, not as a floating control on the graph.
- **Sparse / empty** → the Thread Graph only appears once a thread has nodes to show. The Health Map
  handles the empty‑thread case (empty cards prompting data entry). Below a minimum, prefer a list /
  timeline over an empty canvas.

### 4.7 Node detail = side drawer (click any node)
Opens **without leaving the graph**. Contains:
- Label + node type
- First reported / last reported dates
- Health Threads this node belongs to
- Confidence score
- **Evidence trail** — the provenance chain, traceable back to raw submissions (fetched from the
  scoped provenance endpoint, not inlined in the graph payload)
- Connected items (other nodes linked to this one)
- **User actions:** rename · hide · mark wrong · merge · add to another thread

Example drawer content:
```
Label: Fatigue
Type: Symptom
First reported: 2026-03-08   Last reported: 2026-04-22   Reported in: 6 submissions
Threads: Recurring headaches, Post-viral fatigue
Confidence: 0.91 (high)

Evidence trail:
  → Message 2026-03-08: "been feeling exhausted all day"
  → Message 2026-03-15: "still tired, can't seem to shake it"
  → Lab result 2026-03-15: Haemoglobin 11.2 (contextual)

Connected to:
  ── co_occurs_with ──► Headache       (0.82, 7 co-occurrences)
  ── co_occurs_with ──► Sleep decline  (0.70, 5 co-occurrences)
  ← may_explain ──── Haemoglobin 11.2  (0.67, clinical source)
```

---

## 5. Capabilities & abilities

### 5.1 Filtering / progressive disclosure (four dimensions)
1. **Time window** — Last 30 days · Last 3 months · Last 12 months · Custom · All. (Hides older
   nodes/edges from the view; they remain in the graph.)
2. **PotentialScore threshold** — Focused (>0.7) · **Standard (>0.5, default)** · Exploratory (>0.3) ·
   All.
3. **Edge‑type filter** — e.g. only `co_occurs_with` ("what appears together"), `temporally_precedes`
   ("what came before what"), `may_explain` ("what might be connected"), `treated_with` ("what was
   used").
4. **Node‑type filter** — e.g. only symptoms+findings (clinical picture), only medications, only
   pending items (what's open).

> Map filters 2–4 onto the API where possible: `node_types` / `edge_types` are server params; score
> threshold and time window can be client‑side over the returned subgraph (or server‑side if added
> later).

### 5.2 Scoping
- **Thread‑scoped by default.** Default lens = this thread, last 3 months, PotentialScore > 0.5,
  ~2‑hop depth from the thread's core nodes.
- **Cross‑thread view (opt‑in).** Expands scope to show nodes that appear in multiple threads; shared
  entities are visually distinct. This is where cross‑thread patterns surface ("appeared in 3 threads
  over 18 months").
- **Full patient graph** = a high‑level "my health picture" — render as **clusters** (one per thread)
  with cross‑thread connection counts, not individual nodes/edges.

### 5.3 User actions (graph → which component executes)
| Action | Effect | Owner |
|---|---|---|
| Rename | Update node label | C6 |
| Hide | Set node status `retracted` / user pref; not rendered | C6 + C13 render filter |
| Mark wrong | Create correction → `contradicting` evidence link → recompute confidence | C11 Correction Service |
| Merge | Create `same_as` edge; one node canonical; entity resolution propagates | C6 |
| Add to another thread | Add thread UUID to node's `thread_ids` | C7 + C6 |

### 5.4 WEL‑78 acceptance criteria (what "done" means)
- Thread view renders the Health Thread subgraph using **Cytoscape.js**.
- Investigation landscape renders the broader graph using **Sigma.js** with configurable filters.
- **Clicking any node drills down to its source provenance** (raw context event).
- Both views respond to graph updates **within 2 seconds** of a backend change.
- Visualization works on **mobile viewport** (responsive layout).
- **No raw medical identifiers are displayed without user consent context.**

### 5.5 WEL‑60 (related) acceptance criteria
- Timeline shows symptoms, visits, tests, referrals, pending items in chronological order.
- Evidence graph shows entities and their connections within the thread (thread‑scoped).
- Timeline entries clickable → drill to source event. Graph nodes clickable → drill to evidence chain.

---

## 6. Data model reference

### 6.1 Node types (20)
`Symptom` · `Finding` · `LabTest` · `LabResult` · `Medication` · `ProcedureOrTest` · `Referral` ·
`Visit` · `ConditionHypothesis` · `ConditionMention` · `PendingItem` · `TimePoint` · `TimeInterval` ·
`BodyRegion` · `Clinician` · `Organization` · `Document` · `RawContextEvent` · `HealthSignal` ·
`ExtractedFact`.

> **Safety distinction:** `ConditionHypothesis` is the strongest diagnostic‑adjacent node type. It means
> "evidence points this way, WellBe does NOT confirm it." **There is no `Diagnosis` node type and no
> node meaning "this person has X."** Hard product constraint.

(API graph response also includes `Investigation` and `Theory` node types where present.)

### 6.2 Edge types (13 allowed)
`belongs_to_thread` · `mentioned_in` · `supported_by` · `co_occurs_with` · `temporally_precedes` ·
`same_as` · `part_of` · `located_in` · `measured_by` · `treated_with` · `referred_to` ·
`contradicted_by` · `may_explain`.

> `may_explain` is the **strongest allowed causal‑adjacent edge** (intentionally hedged).
> **Prohibited at the schema level (cannot be inserted, will never appear):** `causes`, `diagnoses`,
> `confirms_diagnosis`, `rules_out`, `proves`.

### 6.3 Edge language for UI copy
| Allowed | Prohibited |
|---|---|
| co‑occurs with · part of · mentioned in · treated with · may help explain · supported by · contradicted by | causes · diagnoses · proves · rules out · confirms diagnosis |

### 6.4 PotentialScore (the `evidence_weight` on each edge)
A 0–1 value: how likely this connection is meaningful **for this patient**, computed from their own
data. Inputs (weighted): C5 evidence confidence · co‑occurrence frequency · temporal proximity · source
quality · semantic similarity · same‑thread boost · cross‑thread recurrence · user confirmation ·
contradiction penalty · recency decay. Recomputed asynchronously (eventual freshness).

**It is NOT:** a diagnosis probability · a clinical significance score · "WellBe thinks A caused B" ·
population statistics. It is entirely derived from this patient's submitted data.

---

## 7. Non‑negotiable product & safety constraints

1. **No diagnosis.** No visual element may imply a confirmed medical conclusion. `ConditionHypothesis`
   nodes must always read as uncertain. No "caused by" / "diagnosed as" labels, ever.
2. **Every claim is traceable.** Every node and edge must have a one‑tap path to "show me the evidence"
   (raw submissions). The graph is explainable, not a black box.
3. **The individual is in control.** The user can hide, correct, merge, and re‑scope. The graph adapts
   to corrections. Nothing is immovable.
4. **No population data in the default view.** "Patients like you" is a separate opt‑in feature behind
   the cross‑patient consent gate (C1). Default graph = this patient only.
5. **Accessibility.** Score/confidence must never be communicated by colour alone. Touch targets ≥44px,
   labels on icon‑only controls, reduced‑motion support, text scaling.
6. **Calm, never alarm.** Reserve urgent visual treatment for Safety‑Gate‑approved guidance. No
   full‑surface red states for routine concern levels.
7. **Naming:** never "master node". Use `Health Thread` (object + graph root), "Main concern" / "Thread
   root" (UI copy), "Concern node" (technical).

---

## 8. Tech stack & rendering guidance
- **Thread view:** **Cytoscape.js** — radial/concentric layout, expand‑on‑click, stable positions.
  Consume the neutral payload and adapt to Cytoscape elements (`data.id`, `data.source`,
  `data.target`).
- **Investigation landscape (broader exploration):** **Sigma.js** (over Graphology) with configurable
  filters.
- **Adapter layer:** write one client‑side adapter `subgraphV2 → { nodes, edges }` for each library.
  Keep the API neutral; do not push viz attributes server‑side.
- **Web app:** Next.js, in `apps/web/app/(workspace)/graph/`. Replace `ComingSoon` in `page.tsx`.
  Data layer uses the existing React Query client over generated API types (WEL‑150).

**Calibration numbers (to size layout/limits):**

| Metric | Estimate |
|---|---|
| Nodes per active thread (typical) | 8–20 |
| Edges per active thread (typical) | 10–30 |
| Active threads per patient | 2–8 |
| Total nodes/patient after 1 year | 50–300 |
| Total edges/patient after 1 year | 100–1,000 |
| Default display scope | thread‑scoped · last 3 months · score > 0.5 |
| Max edges rendered before "show more" | ~50–80 |

---

## 9. Suggested build phases

1. **Adapter + fixtures.** Implement `c13.graph.subgraph.v2 → Cytoscape elements`. Build fixtures shaped
   like §3 (since seeded threads are currently empty). Unit‑test the adapter.
2. **Static thread graph.** Render root + categories + entities with the radial layout and the node
   hierarchy (§4.4). Stable positions; no force layout.
3. **Four‑layer expansion.** One‑click‑one‑layer; open branches persist; collapse support (§4.3).
4. **Edge encoding + relation labels.** Thickness/opacity/label from `evidence_weight`; constrained
   vocabulary copy (§4.5, §6.3).
5. **Evidence drawer.** Node click → drawer with detail + evidence trail (wire the scoped provenance
   endpoint) + user actions (§4.7, §5.3).
6. **Filters.** Time window · score threshold · node‑type · edge‑type (§5.1). Map node/edge type to API
   params.
7. **Special states.** Hypothesis treatment, contradiction warning, "appears in N threads" badge,
   empty/sparse state, `truncated` "show more" (§4.6).
8. **Responsive + a11y pass.** Mobile layout, ≥44px targets, no colour‑only meaning, reduced motion,
   2‑second update target (§5.4, §7).
9. **(Post‑MVP) Investigation landscape.** Sigma.js broader view, cross‑thread, full‑graph clusters
   (§5.2).

---

## 10. Reference map (where each thing is defined)

| Topic | Source |
|---|---|
| Visual design (layout, layers, node/edge visuals, drawer) | `docs/decisions/research-brief-c6-graph-visualization.md` |
| Node/edge types, PotentialScore, scoping, filters | `docs/system-design/knowledge_graph.md` + brief above |
| Live read API contract (query/response/scoping/versioning) | `docs/decisions/graph-query-api-contract.md` |
| API implementation (response shape) | `backend/apps/api/src/wellbe_api/routers/graph_v2.py` |
| Platform UI direction / where graph sits | `docs/implementation/ui_vision.md` |
| Viz story + acceptance criteria | Jira **WEL‑78** |
| Timeline + evidence graph view | Jira **WEL‑60** |
| Read API story (Done) | Jira **WEL‑156** |
| Relevance‑candidate model + review UX (design‑compatible, separate) | Jira **WEL‑141 / WEL‑142** |
