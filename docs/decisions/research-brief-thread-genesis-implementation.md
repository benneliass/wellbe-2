# Research brief: Thread genesis implementation plan & sub-contracts

Prepared for: product owner review and external architecture consultant (self-contained — no prior WellBe knowledge assumed)
Date prepared: 2026-06-18
Owner: Ben Elias, product owner / individual data controller
Approved parent decision: `docs/decisions/thread-genesis-from-capture.md` (WEL-170, Approved 2026-06-18)
Related Jira: WEL-22 (Health Thread core object), WEL-64 (thread engine, in progress), WEL-23 (C5 evidence), WEL-92 (state-machine, done), WEL-12 (Epic E1)
Decision targets seeded by this brief: `docs/decisions/thread-genesis-triage-decision-contract.md`, `docs/decisions/thread-genesis-pending-candidate-object.md`, `docs/decisions/thread-genesis-concern-resolution-key.md` (to be created if the plan is approved)

---

## 0. What this brief is for

The conceptual genesis decision is **already approved** (hybrid, triage-owned: a
capture/fact never directly opens a thread; a triage step classifies every
health-relevant fact into attach / create-thread / create-or-update-candidate /
no-thread-with-reason). What is **not** decided is **how to actually build it** —
the consumer boundary, the durable contracts, the new candidate object, the
dedup key, and how to sequence and scope all of that.

This brief exists so we can decide, before committing anything to Jira or code:

> Is the proposed implementation breakdown (3 follow-up Spikes + 4 Stories, with
> the MVP/post-MVP split and the ownership/sequencing shown in §6) the right
> call — or should genesis be sliced, owned, or sequenced differently?

It also doubles as the seed for the three sub-Spikes: the specific research
questions in §7 are what those Spikes must answer before their Stories build.

This is a decision-support document, not an implementation. No code and no Jira
items are created on the basis of this brief until the plan is approved.

---

## 1. Product background (self-contained — no prior WellBe knowledge assumed)

**What WellBe is.** WellBe is a **Patient-Centered Health Investigation OS** built
on a sovereign *personal* core: a user-controlled health-memory layer that helps
an individual carry their health context forward until each concern is resolved,
explained, monitored, or safely handed off. It is not an EHR, not a clinician
workflow tool, and not a diagnosis engine.

**Who it's for.** The **individual managing their own health is always the primary
user and the data controller.** Clinicians, care teams, institutions, and
researchers may use role-scoped workspaces, but only under the individual's
explicit, revocable grant — never by default, never as controller. A business
(hospital, employer) may *distribute* WellBe to individuals but gets no data
access unless each individual opts in.

**The problem it addresses.** Health context is scattered across visits, devices,
labs, and time. Concerns fall through the cracks: a symptom mentioned once is
forgotten, a "normal" test closes a thread that should stay open, a referral or
pending result is never followed up. WellBe's job is to make sure **nothing the
user raised is silently lost**, and to help them understand their own data better
than they could without it.

**The operating loop** (every feature serves some step of it):

```text
Capture -> Connect -> Investigate -> Clarify -> Close -> Correct
```

**The non-negotiable guardrails** (they bound every genesis design choice):

- **Personal-first / nothing is silently lost.** A concern the user raised must
  never vanish. Genesis must serve the individual's understanding.
- **Investigate, never diagnose.** WellBe surfaces what is known/unknown/pending/
  unresolved and helps prepare for care conversations. It never says "you have X",
  "this rules out X", or ranks differentials.
- **Never alarm.** It must not elevate every passing mention into a tracked
  "health issue", and must not use clinical/alarming framing. Calm, personal-first
  labels only. Genesis is as much a UX decision as a backend one.
- **Source-linked / no orphan claims.** Every derived claim traces to a raw
  source. "WellBe says" is not a source.

**The central object — the Health Thread (C7).** A *Health Thread* is a living
container for **one** unresolved or ongoing concern (e.g. "Cough", "Low vitamin
D"). It holds the narrative, timeline, linked symptoms/labs/referrals, pending
items, and a lifecycle status (draft → active_unresolved → waiting_for_result /
watchful_waiting / explained / chronic_monitoring / closed, etc.). Nearly every
higher surface reads threads: **C8** Six Memories organize around them, **C9**
Continuity tracks open loops per thread, **C10** evaluates output in thread
context, and the user-facing surfaces (**Ask**, **Prepare-for-a-visit**,
**Delta**, **Workspace**) all render thread state. **This is why "what opens a
thread" is the highest-leverage missing contract in the product.**

### 1.1 Glossary (terms used throughout this brief)

| Term | Meaning |
|---|---|
| **Capture** | A single user-submitted input (symptom, lab, note, document) written to the immutable Raw Context Vault. |
| **Fact** | A structured claim the Processing Pipeline (C4) extracts from a capture (e.g. "cough", "duration: 3 weeks"). |
| **Graph node / entity** | A normalized entity in the Knowledge Graph (C6) that resolves/links facts across captures and time. |
| **Health Thread** | The C7 container for one concern (see above). |
| **Genesis** | The act of a thread (or candidate) coming into existence from the capture/processing pipeline — the subject of this brief. |
| **Concern resolution key** | A user-scoped key (normalized concept + type + body site + temporal episode + source context) used to decide whether new evidence belongs to an existing thread or a new one. Not the capture-id or fact-id. |
| **Pending thread candidate** | A proposed, not-yet-active thread for a weak/ambiguous signal; the user can confirm/merge/dismiss, or it auto-promotes on more evidence. |
| **Episode bucket** | A time window grouping repeated mentions of the same concern into one episode vs. a later recurrence. |
| **`NO_THREAD_WITH_REASON`** | A triage outcome recording that a fact was considered and deliberately not turned into a thread/candidate, with an auditable reason — so "nothing is silently lost" holds even when nothing is created. |
| **Surfaces** | The thread-dependent product views: **Ask** (Q&A grounded on the user's threads + pending items), **Prepare** (pre-visit packet from open threads), **Delta** ("what changed" digest), **Workspace** (the thread list / home). |
| **Spike** | A time-boxed research/decision task that must resolve an open design question before its implementation Stories may build (WellBe research protocol). |

---

## 2. The concrete gap this work closes

Today, captures flow into **C4 extracted facts** and **C6 graph nodes**, but
**nothing ever creates a C7 thread** — thread creation exists only as an explicit
`POST /v1/threads` call with no pipeline or UI trigger.

Verified during real-user end-to-end testing on the local cluster (and again with
the committed Dev-workspace seed): a capture-only user gets stored captures and
facts, but an **empty Workspace, empty Ask (it grounds on threads + pending
items), empty Prepare-for-a-visit, and empty Delta digest**. The entire
thread-centric loop stays empty even though the raw data exists.

So genesis is the missing edge between "data is captured" and "the product does
anything with it." That is why it is worth getting the contract right rather than
bolting on a quick `one-thread-per-capture` rule (explicitly rejected in the
approved decision).

### 2.1 Concrete before/after (what genesis should change)

Grounding example, using data shaped like the committed dev-workspace seed:

> A user logs, over two weeks: *"dry cough most mornings, ~3 weeks, plus
> afternoon tiredness"*, then *"cough still there"*, then a lab *"Vitamin D 22
> ng/mL (ref 30–100)"*, plus a note *"ask the doctor if low vitamin D explains
> the fatigue"*.

**Today:** four captures → C4 facts + C6 nodes are created, but **zero threads**.
Workspace is empty, Ask finds no sources, Prepare has nothing to assemble, Delta
shows nothing. The user sees a blank product despite having given it real data.

**With genesis (target):**
- The repeated cough mentions dedup (via the concern key) into **one** thread
  *"Cough"* in `active_unresolved`, linked to the two cough captures as C5
  evidence.
- The abnormal Vitamin D lab opens a thread *"Low vitamin D"* (or attaches, if the
  note ties them together), linked to the lab as evidence.
- The note's explicit worry is attached as supporting evidence (or raises a
  candidate), never lost.
- Nothing alarming is asserted; titles stay calm ("Cough", not "Possible
  respiratory illness"). Anything not turned into a thread is recorded as
  `NO_THREAD_WITH_REASON`.

The design questions in §7 are exactly what determine whether the above happens
correctly (right grouping, right confidence threshold, right provenance) instead
of producing four noisy threads or dropping the note.

---

## 3. The approved decision (fixed inputs — do not re-litigate)

From `docs/decisions/thread-genesis-from-capture.md` (treat as settled):

- Genesis is **hybrid and owned by a dedicated continuity/triage step between
  C4/C6 and C7.** Not C4 directly, not the capture API directly, not C6 directly.
- For every health-relevant fact, the triage step produces exactly one durable
  outcome: `ATTACH_TO_EXISTING_THREAD`, `CREATE_NEW_THREAD`,
  `CREATE_OR_UPDATE_PENDING_CANDIDATE`, or `NO_THREAD_WITH_REASON`.
- **Auto-create** a C7 thread (entering `active_unresolved`) only for
  sufficiently thread-worthy signals (new diagnosis/condition, abnormal trackable
  lab, medication issue, explicit user concern, clinician instruction/referral/
  follow-up, repeated/persistent symptom, high-confidence graph cluster).
- **Weak/ambiguous signals** become **pending thread candidates**, not active
  threads. The user can confirm / merge / dismiss; candidates can auto-promote on
  more evidence. Dismissal never deletes underlying evidence.
- **Dedup** on a user-scoped **concern resolution key** (normalized concept +
  concern type + body site/laterality + temporal episode bucket + source
  context), never capture-id or fact-id.
- **No orphan threads.** `CREATE_NEW_THREAD` must atomically create the C7 thread
  **and** its C5 originating-evidence link(s).
- Manual `POST /v1/threads` stays — but represents **user-initiated** creation
  only.

What is therefore **still open** (the actual subject of research): the consumer's
event boundary, the durable decision-record and candidate schemas, the concern-key
normalization/dedup algorithm, the promotion thresholds, and how to scope/sequence
the build. Those are §6 (the proposal) and §7 (the questions).

---

## 4. Architecture context — the seam genesis sits on

### 4.0 The component map (primer)

WellBe's core is 17 numbered components (C1–C17). A component is *core* if
removing it breaks the Capture→…→Correct loop. Genesis touches the L1–L5 spine
(C3–C9). Full canonical list in `docs/architecture/component-map.md`:

| # | Core component | One-line purpose |
|---|---|---|
| C1 | Trust & Consent | Auth identity, consent scopes, share grants, revocation, cross-patient opt-in gate. |
| C2 | Raw Context Vault | Immutable, append-only store of every raw input with provenance. |
| C3 | Ingestion Layer | Source adapters (manual, document, device, FHIR…) that write into the Vault. |
| **C4** | **Processing Pipeline** | **Extracts entities/facts/signals; quality & confidence scoring.** |
| **C5** | **Evidence & Provenance** | **Links every derived fact to its raw source; enforces "no orphan claims".** |
| **C6** | **Knowledge Graph** | **Typed nodes + evidence-weighted edges; entity resolution across threads/time.** |
| **C7** | **Health Thread Engine + State Machine** | **The central object: one concern's lifecycle, linking, status.** |
| C8 | Six Memories | Story/Clinical/Pattern/Decision/Responsibility/Equity memories around a thread. |
| **C9** | **Continuity & Closure** | **Pending-item ledger, referral/result trackers, durable timers, repeat-visit view.** |
| C10 | Safety & Governance Gate | Mandatory gate before any user-facing AI output (do-not-diagnose, anti-alarm, provenance, bias). |
| C11 | Correction Service | Captures user repairs as new source-linked layers; never overwrites raw/derived. |
| C12 | Notification & Audit | Append-only audit trail; low-alarm, closure-oriented notifications. |
| C13 | API & Contract Layer | The single REST/OpenAPI boundary all surfaces/features call through. |
| C14 | Investigation Engine | The Investigation object — the "Investigate" loop step (scope, participants, evidence bundles). |
| C15 | Theory Service | The Theory object — evidence-for/against, status, safety level; never diagnosis. |
| C16 | External Evidence Graph | Separate external-source graph; relevance links to personal facts; research watch. |
| C17 | Workspace, Role & Grant | Role-scoped workspaces + deep grant model; individual stays controller. |

**Bold rows are the components genesis directly touches.** The table below details
their current state.

### 4.1 The genesis seam (C3 → C7) and current state

Genesis spans the C3→C7 path. Components and their current state:

| Component | Role in genesis | Current state (repo) |
|---|---|---|
| C3 Ingestion / C2 Vault (`component:data-factory`) | Captures land here; emit ingest/outbox events | Implemented; capture write path approved (`capture-write-path-contract.md`) |
| C4 Processing Pipeline | Extracts facts; emits `fact.extracted` | Implemented (`processing-pipeline-extraction-orchestration.md`, WEL-81/82); dispatch loop fixed recently |
| C6 Knowledge Graph | Entity resolution / clustering; normalized concepts | Schema implemented (`knowledge-graph-node-edge-schema.md`); clustering maturity TBD |
| C5 Evidence & Provenance | No-orphan-claims enforcement; evidence links | Decision approved (`evidence-provenance-no-orphan-enforcement.md`); see WEL-23 status |
| C7 Health Thread Engine | `ThreadService.create_thread` / `transition_thread`; state machine | In progress (WEL-64); transitions approved (`health-thread-state-machine-enforcement.md`, WEL-92). `create_thread` currently creates `draft` with no genesis metadata or evidence requirement |
| C9 Continuity & Closure | Pending-item ledger, durable timers | Decision approved (`continuity-pending-ledger-durable-timers.md`); candidate object may live here or near it |
| Surfaces | Workspace / Ask / Prepare / Delta | Live but thread-only; Ask grounds on threads+pending; Delta feed is thread-derived |

Event-flow target (from the approved decision):

```text
C3 Capture -> C4 Fact Extraction -> C6 Entity Resolution
   -> Continuity/Triage Genesis Consumer (decides create / attach / candidate / none)
   -> C7 ThreadService.create_thread / attach_evidence  (+ C5 evidence, atomic)
```

This consumer does not exist yet. Which event(s) it subscribes to, and where it
runs (extend processing-worker vs a new continuity consumer), is an open
question (Q1).

---

## 5. Constraints any plan must satisfy

1. **Research protocol.** Genesis touches core components (C4/C5/C6/C7/C9), and
   the parent decision explicitly flagged three undecided sub-contracts. Those
   must be decided via Spikes before their Stories build. No core-contract code
   before the relevant Spike's Decision Record is approved.
2. **No orphan threads / lossless.** Every system-created thread carries C5
   evidence; every concern-bearing fact is attached, proposed, promoted, or
   explicitly marked non-thread-forming with a reason. Nothing silently dropped.
3. **Idempotency & at-least-once.** The consumer reacts to events that may be
   redelivered; genesis decisions and thread/candidate creation must be
   idempotent (deterministic decision keys, ON CONFLICT-safe writes), per the
   systematic-fixing rule.
4. **Never alarm / personal-first labels.** Auto-created threads use calm,
   personal titles; candidates surface as "things noticed", not health issues.
5. **C10 unaffected.** Genesis creates threads/candidates; any user-facing text
   still passes the safety gate. Genesis must not become a bypass.

---

## 6. The proposal to evaluate

All items parent under Epic **WEL-12 (E1: Health Thread Core)**, link back to the
decision (WEL-170), WEL-22 and WEL-64, and carry one triage-session label.

### Follow-up Spikes (decide the open contracts)

| # | Spike | Open question it closes | Touches | Proposed priority / phase |
|---|---|---|---|---|
| S1 | Thread genesis triage decision contract + consumer event boundary | Which event(s) trigger genesis; the durable triage decision-record schema; where the consumer runs; the auto-create-vs-candidate classification thresholds | C4, C6, C7, C9 | P2 / mvp |
| S2 | Pending thread candidate object, lifecycle, promotion rules | Candidate schema; statuses (pending/promoted/dismissed/merged/expired); owning component; promotion triggers | C7, C9 | P2 / post-mvp |
| S3 | Concern resolution key, dedup/grouping, reopen-vs-new-episode policy | Normalized-concept source (C6); key shape; temporal episode bucketing; dedup precedence; reopen policy | C6, C7 | P2 / mvp |

### Implementation Stories

| # | Story | Depends on | Touches | Proposed priority / phase |
|---|---|---|---|---|
| A | C7 ThreadService: system-genesis metadata + evidence-required invariant (atomic thread+C5 write) | WEL-23 (C5) | C7, C5 | P1 / mvp |
| B | Genesis consumer — high-confidence auto-create path (events → concern key → dedup → create `active_unresolved` + decision record) | S1, S3, A | C4, C6, C7 | P1 / mvp |
| C | Pending candidate store, API, and promotion | S2 | C7, C9 | P2 / post-mvp |
| D | Genesis surface integration (Workspace "Things noticed"; Ask/Delta/Prepare candidate-aware) | C | UI, surfaces | P3 / post-mvp |

### Dependency shape

```text
WEL-23 (C5 evidence) ─▶ A ─┐
S1 ──────────────────────▶ B ◀── S3
S2 ─▶ C ─▶ D
(all relate to WEL-170, WEL-22, WEL-64)
```

### The MVP/post-MVP split being proposed

- **MVP loop:** S1 + S3 + Stories A & B → high-confidence captures auto-open
  evidence-backed threads. Closes the empty-workspace gap. "Nothing lost" is met
  via `NO_THREAD_WITH_REASON` + auto-create.
- **Post-MVP:** S2 + Stories C & D → the pending-candidate layer that catches
  weak/ambiguous signals and exposes "things noticed".

This split is the single biggest judgment call in the plan and is explicitly up
for review (see Q6).

---

## 7. Research questions (what would settle each open point)

These are grouped by which Spike they feed. Answering them validates (or
reshapes) the plan in §6.

### For S1 — triage decision contract & consumer boundary

*Why it matters:* this is the load-bearing contract — it defines the durable
record of every genesis decision and where the logic lives. *What it unblocks:*
Story B (the auto-create path). *What breaks if we guess wrong:* a wrong event
boundary either double-fires genesis or runs before C6 has resolved entities
(producing fragmented/duplicate threads), and a weak decision-record schema means
genesis decisions aren't auditable — violating "nothing silently lost".

- **Q1 — Event boundary & home.** Should the consumer fire on `fact.extracted`
  (per fact), on a `capture.processing_completed` (per capture, after all facts),
  on `graph.cluster_updated` (after entity resolution), or a combination? Per
  fact is too granular; per capture may fire before C6 has resolved entities.
  Should it live in the existing processing-worker or a new continuity consumer?
- **Q2 — Decision-record schema.** What fields must the durable triage decision
  record carry (input fact/capture/graph-entity ids, decision, concern_key,
  confidence, reason, target/created thread id)? Is it append-only? Where stored?
- **Q3 — Classification thresholds.** What makes a signal "thread-worthy" enough
  to auto-create vs. route to a candidate? Per-concern-type thresholds? What is
  the default when confidence is unknown — candidate (safer) or thread?
- **Q4 — Idempotency.** What is the deterministic key for a genesis decision so
  redelivered events do not double-create? (e.g. uuid5 of concern_key + episode.)

### For S2 — pending candidate object

*Why it matters:* candidates are how weak/ambiguous signals stay visible without
alarming the user with premature threads. *What it unblocks:* Stories C and D (the
"things noticed" layer). *What breaks if we guess wrong:* either we build a second
candidate concept that overlaps C9's pending-item ledger and relevance candidates
(WEL-141/142), or — if deferred wrongly — a large class of real mid-confidence
signals becomes invisible, quietly breaking "nothing lost". Q6 is the pivotal
MVP-scoping question.

- **Q5 — Object & ownership.** Fields, statuses, and which component owns the
  candidate (extend C9 pending-tracker vs a new C7-adjacent store)? How does it
  relate to the existing C9 pending-item ledger and to "relevance candidates"
  (WEL-141/142) so we do not build two overlapping candidate concepts?
- **Q6 — Is the candidate layer MVP or post-MVP?** The proposed plan defers it.
  Does deferring it acceptably honor "nothing is silently lost" (via
  `NO_THREAD_WITH_REASON` + auto-create), or is the candidate inbox essential to
  MVP because too many real signals are mid-confidence and would otherwise be
  invisible? This is the key scoping decision.
- **Q7 — Promotion.** Which triggers/thresholds promote a candidate to a thread
  (user confirm, repeat count, duration, association with lab/med/clinician
  instruction, cluster confidence)? Configurable per concern type?

### For S3 — concern key & dedup

*Why it matters:* the concern key decides whether new evidence joins an existing
thread or spawns a new one — it is the difference between one coherent "Cough"
thread and four noisy fragments. *What it unblocks:* Story B (genesis can't create
without a dedup key). *What breaks if we guess wrong:* too-loose keys merge
unrelated concerns; too-tight keys fragment one concern across many threads; a
wrong episode/reopen policy either resurrects closed threads inappropriately or
loses the link between a recurrence and its history.

- **Q8 — Concept normalization source.** Does the normalized concept come from C6
  entity resolution, a separate normalization step, or C4 extraction? How mature
  is C6 clustering today, and is it enough to anchor dedup, or does dedup need a
  simpler interim key?
- **Q9 — Key shape & episode bucketing.** Exact key composition; how to bucket
  temporal episodes; the reopen-vs-new-episode policy (tie into the approved C7
  state-machine: reopen vs. linked recurrence).
- **Q10 — Dedup precedence & merge/split.** Confirm the precedence order
  (active thread > draft > recently-resolved-eligible-for-reopen > candidate >
  new) and how user merge/split corrections feed back into the key.

### For the plan/sequencing itself

- **Q11 — Granularity.** Is 3 Spikes + 4 Stories right, or should S1/S3 merge
  (the consumer contract and the dedup key are tightly coupled), or should Story
  B be split (consumer skeleton vs. classification logic)?
- **Q12 — Sequencing & parallelism.** Is the WEL-23 (C5) dependency on Story A
  real and ready? Can S1/S3 run in parallel? Is anything blocked that would stall
  the MVP loop?
- **Q13 — Parent/epic placement.** Genesis spans C4/C6/C7/C9 but is parented under
  E1 (Health Thread Core). Is that the right home, or should the consumer-side
  work sit under the processing/intelligence epic with cross-links?

---

## 8. Alternatives to weigh (so the decision is deliberate)

| Alternative | Upside | Downside |
|---|---|---|
| **A. Proposed plan (3 Spikes + 4 Stories, candidate layer post-MVP)** | Clean separation; MVP closes the empty-loop gap fast; candidate complexity deferred | Mid-confidence signals invisible until post-MVP; two-phase rollout |
| **B. Candidate layer in MVP (S2/C promoted)** | Fully honors "nothing lost" from day one; richer UX | Larger MVP; more schema to settle before any thread appears |
| **C. Thin slice, no spikes yet** — ship Story A + a minimal auto-create on one high-signal type (e.g. abnormal lab), defer all dedup/candidates | Fastest visible result; learns from real data | Risks an interim contract that the Spikes later overturn; still trips the core-component Spike gate |
| **D. Fold S1+S3 into one contract Spike** | Fewer artifacts; consumer + key decided together | One big Spike; slower to unblock Story B |
| **E. Defer genesis; keep manual `POST /v1/threads` + dev seed** | Zero new core work now | Product loop stays empty for real users; only delays the inevitable |

The proposal is Alternative A. The most likely competing choice is B (if the
candidate inbox is judged MVP-essential) or D (if we want fewer, bigger Spikes).

---

## 9. What "the right call" looks like — decision criteria

Approve the plan as-is if:

- the MVP loop (auto-create high-confidence threads with evidence) is genuinely
  the highest-value first slice, **and**
- deferring candidates does not leave an unacceptable share of real signals
  invisible, **and**
- the 3 Spikes are the right cut of the open questions (Q11/Q12/Q13 resolved).

Reshape the plan if any of the above fails — most likely by promoting the
candidate layer to MVP (Alt B) or merging Spikes (Alt D).

### 9.1 What "genesis works" looks like (observable success criteria)

Independent of the plan decision, the *feature* is successful when, on the live
cluster with the dev-workspace seed (and for a real capture-only user):

1. **The empty loop is closed.** After capturing health-relevant data, the user
   sees at least one thread; Workspace, Ask, Prepare, and Delta are no longer
   empty.
2. **Right grouping.** Repeated mentions of the same concern produce **one**
   thread (deduped via the concern key), not one-per-capture; distinct concerns
   produce distinct threads.
3. **No orphan threads.** Every system-created thread has ≥1 C5 evidence link to
   the originating capture/fact (verifiable in the DB), created atomically.
4. **Nothing silently lost.** Every health-relevant fact ends in exactly one
   recorded outcome — attached, created, candidate, or `NO_THREAD_WITH_REASON` —
   and that record is auditable.
5. **Idempotent.** Re-delivering the same event (or re-running the pipeline) does
   not create duplicate threads/candidates/decisions.
6. **Calm & safe.** Auto-created titles are personal/non-alarming; no genesis path
   emits user-facing text that bypasses C10.

---

## 10. Files to reference

Approved/related decisions:

- `docs/decisions/thread-genesis-from-capture.md` (parent, approved)
- `docs/decisions/health-thread-state-machine-enforcement.md`
- `docs/decisions/capture-write-path-contract.md`
- `docs/decisions/processing-pipeline-extraction-orchestration.md`
- `docs/decisions/c4-extraction-scope-split-wel81-wel82.md`
- `docs/decisions/knowledge-graph-node-edge-schema.md`
- `docs/decisions/evidence-provenance-no-orphan-enforcement.md`
- `docs/decisions/continuity-pending-ledger-durable-timers.md`

Canonical / architecture:

- `docs/system-design/core_objects.md`, `system_design.md`, `system_principles.md`
- `docs/architecture/component-map.md`

Implemented package areas:

- `backend/packages/c7_thread/`, `c5_evidence/`, `c6_graph/`, `c9_continuity/`
- `backend/apps/processing-worker/`
- `backend/apps/api/src/wellbe_api/routers/capture_v1.py`, `threads_v1.py`
- `backend/apps/api/src/wellbe_api/{ask,signals}/engine.py` (thread-dependent surfaces)

---

## 11. Non-goals

- Do not turn genesis into a diagnosis or triage-severity engine — it decides
  whether a concern is *tracked*, never what it *is*.
- No `one-thread-per-capture` or `one-thread-per-fact` rule (already rejected).
- No institution/clinician-driven genesis; genesis serves the individual.
- No auto-created thread without C5 evidence.
- Do not let genesis emit user-facing text that bypasses C10.

---

## 12. Agent protocol note

Research results must be provided by the user. The agent may record, summarize,
and propose Decision Records (S1/S2/S3) from provided research, but may not
self-research these Spikes or implement Stories A–D before the relevant Decision
Records are approved. This brief itself is decision-support: approving it means
approving the §6 plan (and authorizing creation of the Jira Spikes/Stories);
it does not by itself resolve the S1/S2/S3 design questions.

---

_Status: Draft for review. If the plan is approved, create the three sub-Spike
Decision Record stubs named in the header and run the triage EXECUTE step to
create the Jira items in §6._
