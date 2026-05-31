# C6 Knowledge Graph — Visualization & Presentation Consultation Brief

**Prepared:** 2026-05-31  
**Research received:** 2026-05-31  
**Component:** C6 — Knowledge Graph Store  
**Purpose:** External consultation on how the knowledge graph should be presented to end users.  
**Context:** WellBe is a personal health intelligence platform. The individual user (patient or caregiver) is always the primary audience. WellBe does not diagnose. It investigates, connects, and surfaces patterns from data the user has submitted.

---

## Research Results (received 2026-05-31)

### Core decision
C6 should be presented as a **guided, expandable Health Thread graph**. The default view starts with one main concern (a C7 HealthThread object) as the root. The first click reveals category branches. Each subsequent click expands only one more layer of directly connected nodes. Evidence is always available through a side drawer. The graph never implies diagnosis; it shows user-controlled, source-backed relationships in the patient's own data.

This is an **expandable radial / mind-map layout** — not a force-directed graph. The layout is stable; nodes do not jump as branches open.

### Answers to the open questions

**Q1 — Layout algorithm:** Expandable radial / mind-map layout. Not force-directed. Stability is a requirement — the user's spatial memory of what is where must not be reset on every interaction.

**Q2 — Temporal ordering:** Temporal ordering is handled at the edge level (edge labels, `temporally_precedes` edges) and in the evidence drawer timeline — not via a timeline-axis layout. The radial layout is spatial, not temporal.

**Q3 — PotentialScore encoding:** Line thickness + opacity + readable text labels (`strong`, `medium`, `weak`). Not colour alone — accessibility requirement. Example: a strong edge is thick, fully opaque, labelled "strong"; a weak edge is thin, faded, labelled "weak".

**Q4 — ConditionHypothesis visual treatment:** Dashed border + hypothesis badge + muted/lighter background + explicit text label reading "Hypothesis — not diagnosis". This makes the investigative status unambiguous to a non-technical user.

**Q5 — Cross-thread shared nodes:** Badge on the node reading "Appears in N threads" or "Shared with [Thread name]". Cross-thread expansion is an optional action, not the default view.

**Q6 — Sparse/empty state:** The Health Map (top-level view of all Health Thread cards) handles this gracefully — a new user sees empty thread cards prompting data entry. The Thread Graph only appears once a thread has at least some nodes to show.

**Q7 — Contradiction display:** `contradicted_by` edge uses warning visual treatment (distinct edge style). The conflicted node gets a warning badge. The resolution action ("mark wrong", "merge", "hide") lives in the evidence drawer, not as a floating UI element on the graph itself.

**Q8 — Progressive reveal:** Staged, click-driven expansion — not animation for its own sake. Each click reveals exactly one more layer. Existing open branches stay open. The user is always in control of what is visible.

### The expansion model (four layers)

| State | User action | What appears |
|---|---|---|
| Layer 0 | Open thread | Only the Health Thread root node (e.g. "Recurring headaches") |
| Layer 1 | Click root | Category nodes: Symptoms, Tests & labs, Medications, Visits & referrals, Documents, Pending items |
| Layer 2 | Click a category | Actual entity nodes inside that category (e.g. Headache, Fatigue, CBC, MRI planned) |
| Layer 3 | Click an entity node | Directly connected details (e.g. CBC → Haemoglobin 11.2, WBC normal, Platelets normal, Lab PDF) |
| Layer 4+ | Continue clicking | Only direct neighbours of the clicked node appear. Existing branches stay open unless collapsed. |

**Hard rule: one click = one layer only. One click must never reveal the entire graph.**

### Visual node hierarchy

| Node tier | Size | Visual treatment |
|---|---|---|
| Health Thread root | Largest | Central, solid border, status badge (e.g. "Active — Unresolved"), title + last updated + summary counters |
| Category nodes | Medium | Count badge ("Symptoms — 4 items"), expand/collapse affordance |
| Health entity nodes | Smaller | Type-specific icon, label |
| ConditionHypothesis nodes | Smaller | Dashed border, hypothesis badge, muted background, text: "Hypothesis — not diagnosis" |

### Health Map (top-level view)

The top-level experience is a **Health Map** — all active Health Threads shown as separate cards or root nodes. The user clicks one card to enter its expandable Thread Graph. The full patient graph is never shown as a single network.

```
Health Map
  [Recurring headaches]   [Post-viral fatigue]   [Stomach pain]   [Back pain]

Click one → opens its Thread Graph
```

Cross-thread connections surface as badges or optional expansions inside the Thread Graph, not as cross-graph edges in the Health Map.

### Naming conventions (product language)

Do not use "master node" anywhere in backend, API, or product language. Use:
- `Health Thread` (the C7 object and the graph root)
- `Main concern` or `Thread root` (in UI copy)
- `Concern node` (in technical discussion)

### Edge language (confirmed)

| Allowed | Prohibited |
|---|---|
| co-occurs with | causes |
| part of | diagnoses |
| mentioned in | proves |
| treated with | rules out |
| may help explain | confirms diagnosis |
| supported by | |
| contradicted by | |

### Component ownership (clarified)

```
C4 extracts "headache" as ExtractedFact
  → C5 verifies evidence link (source-backed)
  → C7 decides whether to create/update a HealthThread
  → C6 stores the Thread root node + entity nodes + edges
  → C13 renders the expandable graph and evidence drawer
```

The "Health Thread root" node in C6 represents a **C7 HealthThread object**, not a symptom. This is a distinct node type — `Thread` — separate from `Symptom`. C13 renders the Thread as the expandable root; it does not treat the thread and the symptom as the same object.

### Evidence and correction drawer (node detail panel)

Clicking any node opens a side drawer containing:
- Label and node type
- First reported / last reported dates
- Health Threads this node belongs to
- Confidence score
- Evidence trail (traceable back to raw submissions)
- Connected items (other nodes linked to this one)
- User actions: rename, hide, mark wrong, merge, add to another thread

_Research received: 2026-05-31_

---

## Component Traceability Map

Every term in this document traces to exactly one owning system component. This section is the authoritative cross-reference. When implementing any part of the graph UI, the relevant component owner must be consulted before that piece is built.

### Graph nodes — where they come from

| Term in report | C6 node type | Produced by | Evidence-linked by | Displayed by |
|---|---|---|---|---|
| "Recurring headaches" (the concern itself) | `Thread` | **C7** creates the HealthThread object; C6 stores the `Thread` node | — (C7 object, not an extracted claim) | C13 renders as expandable root |
| "Headache" (the symptom entity) | `Symptom` | **C4** extracts from raw event | **C5** links to C2 source | C13 renders as Layer 2 node under Symptoms |
| "Fatigue" | `Symptom` | **C4** | **C5** | C13 |
| "CBC" (the test) | `LabTest` | **C4** extracts from document or FHIR | **C5** | C13 renders under Tests & labs |
| "Haemoglobin 11.2" (the result) | `LabResult` or `Finding` | **C4** extracts from lab PDF/FHIR | **C5** | C13 renders as Layer 3 child of CBC |
| "MRI planned" | `ProcedureOrTest` | **C4** extracts from clinical note or user message | **C5** | C13 renders under Tests & labs |
| "MRI planned" (the pending part) | `PendingItem` | **C9** Continuity & Closure Engine creates a PendingItem when a procedure is ordered but no result exists | C5 links PendingItem to source event | C13 renders under Pending items category |
| "Ibuprofen 400mg" | `Medication` | **C4** | **C5** | C13 |
| "Referred to neurologist" | `Referral` | **C4** extracts from visit note or user message | **C5** | C13 renders under Visits & referrals |
| "GP visit 2026-03-10" | `Visit` | **C4** extracts from document or user entry | **C5** | C13 |
| "Tension-type headache (hypothesis)" | `ConditionHypothesis` | **C10** Intelligence Engines propose a hypothesis when pattern evidence is sufficient | **C5** links to supporting evidence | C13 renders with dashed border + hypothesis badge |
| "Patient has a history of migraines" | `ConditionMention` | **C4** extracts from FHIR or clinical document | **C5** | C13 |
| "Lab result expected, not yet in" | `PendingItem` | **C9** creates when result is expected but not received | **C5** | C13 renders under Pending items |
| "Lab report PDF" | `Document` | **C3** ingests the file; **C2** stores the raw blob; C6 stores a `Document` node | **C5** | C13 renders as document reference |
| "Average pain level 6.2/10" | `HealthSignal` | **C4** computes aggregate signal from multiple raw events | **C5** links to all contributing raw events | C13 |
| "2026-04-12" (a specific date) | `TimePoint` | **C4** extracts temporal markers | **C5** | C13 |
| "Past 6 weeks" (a period) | `TimeInterval` | **C4** | **C5** | C13 |

### Category nodes — important: these are NOT stored in C6

The expansion Layer 1 categories (Symptoms, Tests & labs, Medications, Visits & referrals, Documents, Pending items) are **virtual UI groupings** rendered by C13. They are not nodes in `kg_nodes`. C13 groups nodes by `node_type` under these category headers at render time.

| Category label | C6 node types it groups | Count badge source |
|---|---|---|
| Symptoms | `Symptom` | C13 queries `COUNT(kg_nodes) WHERE node_type = 'Symptom' AND thread_id = ?` |
| Tests & labs | `LabTest`, `LabResult`, `Finding` | Same pattern |
| Medications | `Medication` | Same pattern |
| Visits & referrals | `Visit`, `Referral` | Same pattern |
| Documents | `Document` | Same pattern |
| Pending items | `PendingItem` | **C9** manages the pending item ledger; C13 queries `PendingItem` nodes from C6 |

### Health Thread root node — what the status badge reads from

| UI element | Data source | Owner |
|---|---|---|
| Title ("Recurring headaches") | `HealthThread.title` | **C7** |
| Status badge ("Active — Unresolved") | `HealthThread.status` — one of: `active_unresolved`, `explained`, `waiting_for_result`, `resolved`, `closed` | **C7** |
| Last updated | `HealthThread.updated_at` | **C7** |
| Summary counters (e.g. "4 symptoms") | C13 aggregates from C6 `kg_nodes` count per thread | **C6** data, **C13** computes |

### Evidence drawer — where each field comes from

| Drawer field | Data source | Owner |
|---|---|---|
| Label, node type | `kg_nodes.label`, `kg_nodes.node_type` | **C6** |
| First reported / last reported | `ExtractedFact.captured_at` or `RawContextEvent.captured_at` | **C4** / **C2** |
| Threads connected | `kg_nodes.thread_ids` | **C6** |
| Confidence | `kg_nodes.confidence` (originally set by **C4** extraction_confidence, carried into C6) | **C4** → **C6** |
| Evidence trail (raw messages, documents) | `evidence_links` join table → `raw_context_events` | **C5** → **C2** |
| Connected items (other nodes) | `kg_edges` where `from_node_id` or `to_node_id` = this node | **C6** |

### User actions in the evidence drawer — which component executes each

| User action | What it does | Owning component |
|---|---|---|
| **Rename** | Updates `kg_nodes.label` for this node | **C6** (label update) |
| **Hide** | Sets `kg_nodes.status = 'retracted'` or stores a user preference; node stays in graph but is not rendered | **C6** node status + **C13** render filter |
| **Mark wrong** | Creates a correction record that adds a `link_type = 'contradicting'` evidence link and recalculates confidence | **C11** Correction Service — this is C11's primary function |
| **Merge** | Creates a `same_as` edge between two nodes; one becomes canonical; entity resolution propagates | **C6** `same_as` edge + entity resolution worker |
| **Add to another thread** | Adds the thread's UUID to `kg_nodes.thread_ids`; C7 may evaluate whether to link the threads | **C7** thread linking command + **C6** node update |

### PotentialScore inputs — which component produces each signal

| Score input | Produced by | How it reaches C6 |
|---|---|---|
| C5 evidence confidence | **C5** | Carried in `evidence.linked` event payload |
| Co-occurrence frequency | **C6** scoring worker | Computed from `kg_edges` history |
| Temporal proximity | **C6** scoring worker | Uses `TimePoint` nodes and `temporally_precedes` edges |
| Source quality | **C4** quality_flag on ExtractedFact | Carried in `fact.extracted` event payload |
| Semantic similarity | **C6** pgvector cosine distance on `embedding_id` | Computed during scoring |
| Same-thread boost | **C6** scoring worker | Checks `thread_ids` overlap between two nodes |
| Cross-thread recurrence | **C6** scoring worker | Counts how many threads share this edge pair |
| User confirmation | **C11** `correction.applied` event (positive correction) | C11 emits event; C6 scoring worker raises weight |
| Contradiction penalty | **C11** `correction.applied` event (negative correction / "mark wrong") | C11 emits event; C6 scoring worker applies penalty |
| Recency decay | **C6** scoring worker | Uses `last_scored_at` and `captured_at` |

### Events that drive C6 scoring — which component emits each

| Event | Emitted by | Consumed by |
|---|---|---|
| `fact.extracted` | **C4** Processing Pipeline | C6 scoring worker |
| `health_signal.created` | **C4** | C6 scoring worker |
| `evidence.linked` | **C5** Evidence & Provenance | C6 scoring worker |
| `correction.applied` | **C11** Correction Service | C6 scoring worker |
| `thread.state_changed` | **C7** Health Thread Engine | C6 scoring worker |

### Cross-patient gate

The "Appears in N threads" badge uses only this patient's own data and does not require the cross-patient gate. Any query that would aggregate data across multiple patients (e.g. "other people with similar patterns") is governed by **C1** Trust & Consent — cross-patient access requires explicit individual opt-in and is off by default.

---

## 1. What the Knowledge Graph Is

The Knowledge Graph is a **per-patient, per-session network of health entities and their relationships**, built entirely from data the user has submitted to WellBe over time. It is not a medical ontology. It is not a generic disease database. Every node and every edge in the graph came from this specific person's health history.

The graph is built in layers:

```
User submits data (text, photos, documents, FHIR records, wearable exports)
  ↓
Raw events stored immutably (C2 — Raw Context Vault)
  ↓
Facts and signals extracted from raw events (C4 — Processing Pipeline)
  ↓
Evidence links validated — every fact traces back to raw source (C5 — Evidence & Provenance)
  ↓
Facts and signals become nodes and edges in the graph (C6 — Knowledge Graph Store)
  ↓
Intelligence engines traverse the graph to surface patterns (C10 — Intelligence Engines)
  ↓
UI presents insights grounded in graph nodes/edges (C13 — API + UI Layer)
```

C6 is the storage and structure layer. It does not generate insights. It provides the connected, evidence-weighted substrate that the intelligence layer traverses.

---

## 2. What the Graph Contains

### 2.1 Node Types (20 initial types)

Every node represents one named health entity that appeared in the user's data at least once.

| Node type | What it represents | Example |
|---|---|---|
| `Symptom` | A user-reported symptom | Headache, fatigue, nausea, shortness of breath |
| `Finding` | A clinically sourced observation | "Haemoglobin 11.2 g/dL" from an imported lab report |
| `LabTest` | A test that was ordered | CBC (complete blood count) |
| `LabResult` | The actual result of a test | Haemoglobin 11.2 on 2026-03-15 |
| `Medication` | A medication mentioned or taken | Ibuprofen 400mg |
| `ProcedureOrTest` | A medical procedure ordered or performed | MRI head |
| `Referral` | A referral to a specialist | Referred to neurologist 2026-04-01 |
| `Visit` | A medical appointment | GP visit 2026-03-10 |
| `ConditionHypothesis` | A potential condition the evidence points toward — WellBe does NOT confirm it | Tension-type headache (hypothesis) |
| `ConditionMention` | A condition a clinical source or the user mentioned — not a WellBe assertion | "Patient has a history of migraines" |
| `PendingItem` | Something expected but not yet received | Lab result expected, not yet in |
| `TimePoint` | A specific date relevant to a health event | 2026-04-12 |
| `TimeInterval` | A period over which a pattern was observed | "Past 6 weeks" |
| `BodyRegion` | An anatomical region | Head, lower back, left knee |
| `Clinician` | A healthcare professional referenced | Dr. Smith |
| `Organization` | A healthcare org referenced | City General Hospital |
| `Document` | A submitted document | Hospital discharge summary PDF |
| `RawContextEvent` | A reference to a raw submission | Linked for provenance display |
| `HealthSignal` | An aggregate or computed signal | Average pain level 6.2/10 past 4 weeks |
| `ExtractedFact` | A discrete fact extracted from raw text | "User reported headache on 2026-04-12" |

**Important safety distinction:** `ConditionHypothesis` is the strongest diagnostic-adjacent node type WellBe uses. It explicitly means "the evidence is pointing this direction but WellBe is not confirming it." There is no `Diagnosis` node type. There is no node that means "this person has X." This is a hard product constraint, not a stylistic choice.

### 2.2 Minimum fields on every node

```
id                UUID
patient_id        UUID  (every node belongs to exactly one patient)
node_type         string (from the allowed type list above)
label             string (human-readable: "Headache", "Ibuprofen 400mg")
normalized_key    string | null  (e.g. SNOMED code key if available)
code_system       string | null  (e.g. "SNOMED", "LOINC", "RxNorm")
code              string | null  (e.g. "25064002" for SNOMED headache)
thread_ids        UUID[]  (which Health Threads this node belongs to)
evidence_refs     UUID[]  (which raw events this node was extracted from)
confidence        numeric 0–1  (how reliably was this entity identified)
status            string  (active | resolved | pending | retracted)
created_at        timestamp
updated_at        timestamp
embedding_id      UUID | null  (pgvector embedding for semantic similarity)
metadata          jsonb  (node-type-specific extras)
```

### 2.3 Edge Types (13 allowed types)

Every edge is typed, directed, and carries a PotentialScore.

| Edge type | Meaning | Example |
|---|---|---|
| `belongs_to_thread` | This entity is part of a Health Thread | Headache node → Thread "Recurring headaches" |
| `mentioned_in` | This entity was mentioned in this document/event | Ibuprofen → Document (discharge summary) |
| `supported_by` | This node is supported by this evidence | ConditionHypothesis → LabResult |
| `co_occurs_with` | These entities appear together repeatedly | Headache ↔ Fatigue |
| `temporally_precedes` | This entity appeared before the other | Sleep decline → Fatigue |
| `same_as` | Two extracted entities refer to the same real thing | "Ibuprofen" = "Advil 400mg" |
| `part_of` | This entity is a component of the other | Haemoglobin → CBC panel |
| `located_in` | This entity is localised to this body region | Headache → Head |
| `measured_by` | This test measures this entity | CBC → Haemoglobin |
| `treated_with` | This medication was used for this symptom/finding | Headache → Ibuprofen |
| `referred_to` | This referral was for this concern | Headache → Referral: neurologist |
| `contradicted_by` | This evidence contradicts this node | ConditionHypothesis → contradicting Finding |
| `may_explain` | This entity may help explain the other | Haemoglobin 11.2 may_explain Fatigue |

**`may_explain` is the strongest allowed causal-adjacent edge.** It is intentionally hedged — "may explain" not "causes" or "confirms". The following edge types are explicitly **prohibited** at the schema level and cannot be inserted: `causes`, `diagnoses`, `confirms_diagnosis`, `rules_out`, `proves`. These are blocked by a combination of a lookup table constraint, service-layer validation, and automated tests.

### 2.4 Minimum fields on every edge

```
id               UUID
patient_id       UUID
from_node_id     UUID
to_node_id       UUID
edge_type        string (from the allowed type list)
potential_score  numeric 0–1  (evidence-weighted relevance of this connection)
score_version    integer
score_inputs     jsonb  (the inputs that produced this score — see section 3)
last_scored_at   timestamp
needs_rescore    boolean  (flag for async recomputation)
thread_ids       UUID[]  (which threads this edge belongs to)
evidence_refs    UUID[]
created_at       timestamp
```

---

## 3. PotentialScore — How Relevance Is Computed

PotentialScore is the numeric value (0–1) on every edge that represents how likely this connection is to be meaningful for this patient. It determines which edges are surfaced prominently and which are filtered out at low-confidence thresholds.

### 3.1 What goes into PotentialScore

Ten inputs, weighted and combined:

| Input | What it measures |
|---|---|
| **C5 evidence confidence** | How well-supported by raw sources are the two connected nodes |
| **Co-occurrence frequency** | How many times have these two entities appeared together in the user's history |
| **Temporal proximity** | Did they appear close together in time (same week, same month) |
| **Source quality** | Is the evidence from a clinical document (high) or a casual message (lower) |
| **Semantic similarity** | How semantically close are the two entities (pgvector cosine distance on embeddings) |
| **Same-thread boost** | Both nodes belong to the same active Health Thread (positive) |
| **Cross-thread recurrence** | This same connection has appeared across multiple Health Threads (strong positive) |
| **User confirmation** | The user has explicitly confirmed this connection is meaningful (strong positive) |
| **Contradiction penalty** | There is contradicting evidence against one or both nodes (negative) |
| **Recency decay** | Older connections decay in score unless they are reinforced by recent evidence |

### 3.2 When PotentialScore is recomputed

Score is materialized on the edge and recomputed asynchronously (not at query time) when any of these events occur:

```
fact.extracted          → a new fact was extracted from a raw event
health_signal.created   → a new aggregate signal was computed
evidence.linked         → new evidence was linked to a node
correction.applied      → the user corrected something (triggers contradiction penalty)
thread.state_changed    → a Health Thread changed state (e.g. resolved)
```

The scoring worker sets `needs_rescore = true` on affected edges and recomputes in the background. Edges are readable during recomputation — they return the last known score with `needs_rescore = true` as a staleness indicator.

### 3.3 What PotentialScore does NOT represent

- It is not a probability of diagnosis
- It is not a clinical significance score
- It does not mean "WellBe thinks A caused B"
- It does not factor in population statistics ("patients like you have...")
- It is entirely derived from this patient's own submitted data

---

## 4. Subgraph Structure — How the Graph Is Scoped

The full patient graph is never shown at once. It is always presented through a scoping lens.

### 4.1 Health Thread as primary scope

A **Health Thread** is the top-level organising object for a health concern (e.g. "Recurring headaches since February", "Post-surgery recovery", "Managing fatigue"). Each thread has:
- A lifecycle state: `active_unresolved → explained → waiting_for_result → resolved → closed`
- A set of associated nodes (everything the user has submitted under this concern)
- A subgraph: all nodes where `thread_ids` contains this thread's ID

The primary graph view is always **thread-scoped**: show nodes and edges belonging to this thread, within a configurable hop depth (default: 2 hops from the thread's core nodes).

A patient might have 5–10 active threads and dozens of resolved threads. The graph for each thread is independently navigable.

### 4.2 Cross-thread view

When a user wants to see how a concern connects to other threads, they can enable a cross-thread view. This expands the scope to show nodes that appear in multiple threads — the shared entities are visually distinct from thread-local entities.

This is the view where the intelligence layer's cross-thread patterns become visible: "this entity has appeared in 3 different threads over 18 months."

### 4.3 The full patient graph

A consolidated view showing all threads and all connections. This is the high-level "my health picture" view. At this scope, individual edges are likely too numerous to show — the sensible presentation is probably cluster-level (each thread as a cluster) with cross-thread connection counts, not individual nodes.

---

## 5. Filtering and Progressive Disclosure

The graph supports four filtering dimensions that progressively narrow what is rendered:

### 5.1 Time window
Show only nodes and edges observed within a selected period:
- Last 30 days
- Last 3 months
- Last 12 months
- Custom range
- All time

Older nodes and edges are hidden from the rendered view but remain in the graph.

### 5.2 PotentialScore threshold
Show only edges above a minimum score. Suggested defaults:
- **Focused** (score > 0.7): only strong, well-supported connections
- **Standard** (score > 0.5): meaningful connections, default view
- **Exploratory** (score > 0.3): includes weaker, speculative connections
- **All** (no threshold): everything, including low-confidence tentative edges

### 5.3 Edge type filter
Show only edges of selected types. Common use cases:
- Show only `co_occurs_with` → "what tends to appear together"
- Show only `temporally_precedes` → "what came before what"
- Show only `may_explain` → "what might be connected causally"
- Show only `treated_with` → "what interventions were used"

### 5.4 Node type filter
Show only certain entity types. Common use cases:
- "Show only symptoms and findings" → clinical picture
- "Show only medications" → medication history
- "Show only pending items" → what's still open or awaiting follow-up

---

## 6. What a Specific Node Shows When Selected

When a user taps/clicks a node in the graph, the node detail view should show:

```
Label: Fatigue
Type: Symptom
First reported: 2026-03-08
Last reported: 2026-04-22
Reported in: 6 submissions
Threads: Recurring headaches, Post-viral fatigue
Confidence: 0.91 (high — mentioned explicitly multiple times)

Evidence trail:
  → Message on 2026-03-08: "been feeling exhausted all day"
  → Message on 2026-03-15: "still tired, can't seem to shake it"
  → Lab result 2026-03-15: Haemoglobin 11.2 (contextual)

Connected to:
  ── co_occurs_with ──► Headache       (score: 0.82, 7 co-occurrences)
  ── co_occurs_with ──► Sleep decline  (score: 0.70, 5 co-occurrences)
  ← may_explain ──── Haemoglobin 11.2  (score: 0.67, clinical source)
```

The evidence trail is the provenance chain — every node is traceable back to the raw submissions that produced it.

---

## 7. Open Questions for External Consultation

These are the specific design questions we are seeking external input on:

### Q1 — Graph layout algorithm at thread scope
At the thread scope (typically 8–20 nodes, 10–30 edges), what layout algorithm produces the most readable and health-intuitive result? Options include:
- **Force-directed** (e.g. D3 force, Fruchterman-Reingold): nodes repel each other, edges pull connected nodes together. Natural, but non-deterministic layout
- **Hierarchical** (e.g. Dagre): nodes in levels, useful when temporal ordering matters
- **Radial/ego layout**: one focal node (e.g. the thread's primary symptom) at centre, connected nodes radiating outward by hop count
- **Timeline-anchored**: x-axis = time, y-axis = entity type — shows temporal sequence explicitly

Is there a layout that is specifically recommended for personal health graphs where the user's primary goal is understanding sequence and pattern, not exploring a complex network?

### Q2 — How to handle temporal ordering visually
The graph has `temporally_precedes` edges and timestamped nodes. But force-directed layouts don't respect time. Should temporal order be:
- An explicit visual axis (timeline layout)
- A secondary visual cue (node colour/position indicates relative time)
- Only visible through the `temporally_precedes` edge type filter
- Or is temporal order better shown as a separate timeline view entirely, with the graph reserved for connection/co-occurrence display?

### Q3 — PotentialScore as a visual variable
The PotentialScore (0–1) is on every edge. Should it be encoded as:
- Edge thickness (thicker = stronger)
- Edge opacity (more opaque = stronger, faded = weaker)
- Edge colour (gradient from grey to a highlight colour)
- Or something else?

And for nodes — should node confidence be encoded visually? If so, how? Size, opacity, border style?

### Q4 — `ConditionHypothesis` nodes — visual treatment
These nodes are special: they represent what the evidence points toward, but WellBe explicitly does not confirm them. They need to read as investigative / uncertain, not as conclusions. What visual treatment communicates "this is a hypothesis, not a fact"? Options:
- Dashed border instead of solid
- Different fill style (e.g. striped, gradient)
- A specific icon or badge ("hypothesis" tag)
- Greyed out compared to confirmed facts
- A distinct node shape (e.g. hexagon vs circle)

### Q5 — Cross-thread shared nodes
When a user enables the cross-thread view, some nodes appear in multiple threads. How should shared nodes be visually indicated? Options:
- Multi-ring border (one ring per thread colour)
- A badge showing "3 threads"
- Positioned at the intersection of thread clusters
- Highlighted with a distinct colour when cross-thread mode is active

### Q6 — Empty states and low-data states
A new user or a user with only 1–2 submissions will have a sparse graph. What is the right experience here — should the graph UI be shown at all for sparse data, or is there a minimum data threshold below which a different view (e.g. a simple timeline or a list) is more appropriate?

### Q7 — The contradiction / conflicting evidence case
If two pieces of evidence point in opposite directions (`contradicted_by` edge), how should this be presented in the graph? Should it:
- Show the contradicting edge as a red/warning coloured edge
- Show a warning badge on the conflicted node
- Surface it as an alert outside the graph view entirely
- Allow the user to "resolve" the contradiction directly from the graph

### Q8 — Progressive reveal vs. all-at-once render
At thread scope (8–20 nodes), should the graph appear all at once with animation, or should there be a staged reveal where the core nodes appear first and secondary nodes animate in? Research question: for health data specifically, does staged reveal reduce anxiety or increase engagement, or does it feel gimmicky?

---

## 8. Technical Architecture Context (for reference)

The graph is stored in two parallel structures:

**Relational tables (hot-path API queries):**
```
kg_nodes(patient_id, node_id, node_type, label, thread_ids, confidence, ...)
kg_edges(patient_id, from_node_id, to_node_id, edge_type, potential_score, thread_ids, ...)
```
These are the source of truth for API responses. Indexed for fast thread-scoped queries.

**Apache AGE (graph traversal and exploration):**
Apache AGE is a PostgreSQL extension that brings Cypher graph query language into Postgres. The same nodes and edges are projected into AGE for traversal queries (e.g. "find all paths between symptom A and finding B within 3 hops"). AGE is used for exploration and visualization queries, not for hot-path API reads.

**pgvector (semantic similarity):**
Every node has an optional vector embedding. Semantic similarity between nodes is computed using cosine distance. This is one of the PotentialScore inputs and is also used for entity resolution (`same_as` edge candidates — "is 'Advil 400mg' the same entity as 'Ibuprofen 400mg'?").

**Event-driven scoring:**
PotentialScore is not computed at query time. It is materialized on the edge row and recomputed asynchronously by a scoring worker that consumes events. This means graph reads are always fast; score freshness is eventual (typically seconds to minutes after new data arrives).

---

## 9. Product Constraints the Visual Design Must Respect

1. **No diagnosis.** No visual element may imply a confirmed medical conclusion. `ConditionHypothesis` nodes must always read as uncertain. Edge labels like "caused by" or "diagnosed as" must never appear.

2. **Every claim is traceable.** Every node and edge in the UI must have a path to "show me the evidence" — the raw submissions that produced it. The graph is not a black box; it is an explainable picture.

3. **The individual is in control.** The user can hide nodes, correct connections, and mark things as irrelevant. The graph adapts to their corrections. Nothing is immovable.

4. **No population data in the default view.** "Patients like you" comparisons are a separate opt-in feature (cross-patient gate). The default graph shows only this patient's own data.

5. **Accessibility.** PotentialScore and confidence cannot be communicated *only* through colour — colour-blind users must be able to read the graph.

---

## 10. Summary of Key Numbers

To help external consultants calibrate the design:

| Metric | Estimate |
|---|---|
| Nodes in a single active thread (typical) | 8–20 |
| Edges in a single active thread (typical) | 10–30 |
| Threads per patient (active) | 2–8 |
| Threads per patient (lifetime, including resolved) | 10–50 |
| Total nodes per patient after 1 year of use | 50–300 |
| Total edges per patient after 1 year of use | 100–1,000 |
| Default display scope | Thread-scoped, last 3 months, PotentialScore > 0.5 |
| Max edges rendered at once (recommended limit) | ~50–80 before "show more" is needed |
