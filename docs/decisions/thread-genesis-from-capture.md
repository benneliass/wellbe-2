# Decision: When and how a capture (or detected concern) opens a Health Thread

**Status:** Approved  
**Date opened:** 2026-06-18  
**Date approved:** 2026-06-18  
**Approved by:** User  
**Jira Spike:** WEL-170  
**Blocks:** WEL-22 — WB2-F001: Health Thread core object and lifecycle

---

## Question

Captures currently flow into C4 extracted facts and C6 graph nodes, but **nothing ever creates a C7 Health Thread**. Thread creation exists only as an explicit `POST /v1/threads` call with no UI or pipeline trigger. As a result, a real user who logs symptoms, labs, or notes sees an empty Workspace, an Ask that finds no sources (it grounds on threads + pending items), an empty Prepare-for-a-visit (needs open threads), and an empty Delta digest (its feed is thread-derived) — the entire thread-centric product loop stays empty even though the raw data and facts exist.

The specific decisions that must be made before implementing thread genesis:

1. **What is the genesis trigger?** Does every capture open a thread, or only certain capture types/signals? Is genesis fact-driven (react to `fact.extracted` from C4), graph-cluster-driven (C6 entity clustering), an explicit user action, or a dedicated triage step (the `/triage` surface)?
2. **Who owns thread creation?** The processing pipeline (C4) on `fact.extracted`, a new continuity/triage consumer, the API at capture time, or the user via a confirmation UI?
3. **How do we avoid thread sprawl while guaranteeing no concern is silently lost?** A naive "one thread per capture" rule produces a thread for every cough mention; a too-conservative rule drops concerns and violates the personal-first promise that nothing is lost. What is the grouping / dedup / resolution key that maps related captures (e.g. repeated "cough" mentions over weeks) onto a single thread?
4. **What initial state and provenance does an auto-created thread get?** `draft` vs `active_unresolved`, and how does the new thread link back to the originating captures/facts as C5 evidence (no orphan claims)?
5. **Is genesis fully automatic, fully user-confirmed, or hybrid** (system proposes a thread, user confirms/merges/dismisses)? This is a personal-first, never-alarm UX decision as much as a backend one — auto-opening threads the user didn't ask for could feel alarming or noisy.

## Context

C7 (Health Thread Engine + State Machine, layer L3) is the central product object that every higher component reads: C8 (Six Memories) organizes around threads, C9 (Continuity & Closure) tracks open loops per thread, C10 (Safety Gate) evaluates output in thread context, and C13/Ask/Prepare/Delta/Workspace all surface thread state. Genesis sits at the seam between C3/C4 (capture → facts), C6 (graph), and C7 (threads), and likely touches a triage step — so its blast radius is **cross-cutting**.

The state-machine *transitions* are already decided (`docs/decisions/health-thread-state-machine-enforcement.md`, WEL-92) and the thread object/lifecycle is being implemented (WEL-64), but **how a thread first comes into existence from the pipeline is undecided**. This contract — what opens a thread, the dedup/grouping key, and how a thread links to its originating evidence — becomes a stable, hard-to-change contract that C8, C9, C13, Ask, Prepare, and Delta all build on. Guessing wrong risks either thread sprawl (noisy, alarming, violates never-alarm) or silently dropped concerns (violates the personal-first "nothing is lost" promise).

## Research provided

_Research received: 2026-06-18_

The user provided a written analysis (`health-thread-genesis-research.md`). It
notes that no external/literature research was conducted; the synthesis is
grounded in WellBe's own product and architecture context. The full analysis is
recorded faithfully in the sections below (Approaches considered, Decision and
its sub-sections, Trade-offs, Implementation notes).

Headline of the provided analysis: use **hybrid, triage-owned thread genesis**.
Do **not** create one C7 Health Thread per capture or per extracted fact.
Introduce a continuity/triage-owned genesis step between C4/C6 and C7 so that
every health-relevant fact is accounted for, but only sufficiently thread-worthy
concerns become C7 threads automatically; weaker signals become pending thread
candidates that can later be confirmed, merged, dismissed, or promoted. This
preserves the "nothing is silently lost" promise without noisy/alarming sprawl.

## Approaches considered

### 1. One thread per capture
Every submitted capture opens a new C7 thread.
- **Pros:** Simple; guarantees captures enter the thread-centric loop.
- **Cons:** Severe sprawl (a diary note with five mentions → five threads;
  repeated mentions → duplicates). Violates "never alarm" by elevating every
  passing mention into a tracked issue.
- **Rejected.**

### 2. One thread per extracted fact
Every C4 `fact.extracted` carrying a health concept opens a thread.
- **Pros:** More structured; easy per-fact provenance.
- **Cons:** Still too noisy — facts are too granular to be the thread boundary.
  "cough", "worse at night", "started last week", "using inhaler" should not
  become four threads.
- **Rejected.**

### 3. Only user-confirmed creation
System never auto-creates; it only proposes, and the user confirms each.
- **Pros:** Strongest user control; least alarming.
- **Cons:** Loop depends on user effort; important concerns may stay untracked;
  Ask/Workspace/Prepare/Delta/C8/C9/C10 stay underpowered until manual curation.
- **Rejected as the only mechanism.**

### 4. Graph-cluster-only genesis
C6 clusters facts/entities; a thread is created once a stable cluster emerges.
- **Pros:** Better grouping/dedup; fewer duplicates across repeated captures.
- **Cons:** Too passive for important first-time events (new abnormal lab, new
  diagnosis, med side effect, explicit concern, clinician instruction) that
  deserve immediate creation before a long-lived cluster exists.
- **Rejected as the sole trigger, but C6 clustering should inform grouping.**

### 5. Hybrid triage-owned genesis
A dedicated continuity/triage step receives C4 facts and C6 signals and either
(1) attaches evidence to an existing thread, (2) creates a new C7 thread,
(3) creates/updates a pending thread candidate, or (4) records the fact as
non-thread-forming with an explicit reason.
- **Pros:** Balances losslessness, dedup, and UX calmness; high-confidence
  concerns enter automatically while weak signals stay reviewable.
- **Cons:** Requires a new triage contract and additional state; more complex
  than direct creation.
- **Accepted.**

## Decision

Thread genesis is **hybrid and owned by a dedicated continuity/triage step
between C4/C6 and C7.**

A capture does not directly create a Health Thread, and C4 fact extraction does
not directly create a Health Thread. Instead, extracted facts and graph/
entity-resolution signals are evaluated by a thread genesis triage consumer. For
every health-relevant fact, the triage consumer must produce exactly one durable
outcome:

1. `ATTACH_TO_EXISTING_THREAD` — attach the evidence to an existing thread;
2. `CREATE_NEW_THREAD` — create a new C7 Health Thread;
3. `CREATE_OR_UPDATE_PENDING_CANDIDATE` — create/update a pending thread candidate;
4. `NO_THREAD_WITH_REASON` — mark the fact as non-thread-forming with a reason.

This is a lossless accounting rule: **no concern-bearing evidence may be silently
dropped**, but weak or ambiguous signals do not automatically become active
threads.

Manual `POST /v1/threads` remains supported for **user-initiated** thread
creation, but pipeline-driven genesis is owned by the continuity/triage consumer.

### Genesis trigger
A capture itself does not open a thread. The trigger is a **thread-worthy concern
signal** derived from one or more of: C4 extracted facts; C6 graph entities/
clusters; explicit user intent; clinician/document-derived care instructions;
abnormal or follow-up-relevant labs; repeated/persistent symptoms; medication
concerns; diagnosis/condition mentions; unresolved questions, worries, or planned
actions.

### Ownership
```text
C3 Capture
  -> C4 Fact Extraction
  -> C6 Graph Update / Entity Resolution
  -> Continuity/Triage Genesis Consumer   (owns create/attach/propose decision)
  -> C7 ThreadService.create_thread / attach_evidence / update_thread
```
C4 emits facts; C6 resolves entities/clusters; C7 owns the lifecycle; the new
triage/genesis step owns the decision to create or attach. Thread creation is
**not** owned by C4 directly, the capture API directly, or C6 directly.

### Automatic vs user-confirmed (hybrid)
- **Auto-create a C7 thread (enters `active_unresolved`)** when the signal is
  strong enough that hiding it would be worse than surfacing it: new diagnosis/
  condition; abnormal trackable lab; medication side effect/adherence/change;
  explicit user concern; clinician instruction/referral/test order/follow-up;
  repeated symptom mentions across time; symptom with duration/progression/
  severity/functional impact; high-confidence graph cluster.
- **Create a pending candidate** when the signal is weak or ambiguous (single
  mild/passing mention, incidental mention in a long note, ambiguous extraction,
  low-confidence fact, wellness observation without persistence/follow-up).
- **User actions remain first-class:** confirm a candidate into a thread, merge
  into an existing thread, dismiss, mark not important, create manually, or
  rename/reframe in personal language. **Dismissal must not delete underlying
  facts/evidence** — it only stops active tracking unless stronger evidence
  appears later.

### Initial thread state
```text
High-confidence concern signal -> C7 thread in active_unresolved
Low-confidence / ambiguous signal -> pending candidate (not a draft C7 thread)
User manually starts a thread -> draft or active_unresolved per current C7 rules
```
Weak/ambiguous signals must not create `draft` C7 threads; they create pending
candidates instead.

### Grouping / dedup / resolution key
Genesis uses a stable, user-scoped **concern resolution key** — not capture ID,
not raw fact ID:
```text
user_id
+ normalized_concern_concept     (canonical C4/C6 concept; display title stays personal/calm)
+ concern_type                   (symptom | condition | lab_abnormality | medication_issue |
                                  care_gap | follow_up_task | question_or_worry |
                                  procedure_or_test | visit_preparation)
+ body_site / laterality / affected system   (when it changes meaning; conservative: merge if
                                              compatible, split if clinically/personally distinct)
+ temporal_episode_bucket        (distinguish repeated mentions in one episode from a new episode)
+ source-context modifiers       (user note | lab | clinician doc | transcript | med list | import)
```
Dedup precedence before creating anything new:
```text
active_unresolved thread
> draft/user-started thread
> recently resolved thread eligible for reopen
> pending candidate
> new thread
> new pending candidate
```
Reopen vs new: continuation/near-term recurrence reopens (or moves to
`active_unresolved`) per the approved C7 state-machine rules; a distinct later
episode creates a new thread linked to the prior as related/recurrent.

### Provenance and evidence (no orphan claims)
`CREATE_NEW_THREAD` must **atomically** create the C7 thread **and** its C5
originating evidence link(s). No auto-created thread may exist without evidence.
Minimum provenance: `thread_id, capture_id, fact_id(s), graph_entity_id(s),
source_type, source_timestamp, extraction_confidence, triage_decision,
triage_reason, created_by=system, created_via=continuity_triage`.

### UX rule (calm, personal-first)
System-created threads use neutral, personal labels ("Cough", "Cholesterol",
"Blood pressure", "Follow-up from visit", "Medication side effect") — never
alarming labels ("Possible serious respiratory condition", "Urgent health
issue"). The UI distinguishes **Open threads**, **Things WellBe noticed**
(pending candidates, framed as "Something I noticed" / "Possible thing to
track"), and **Dismissed / not tracking**.

## Trade-offs accepted

Accepts additional backend complexity in exchange for lower product risk:
- genesis requires a dedicated triage/continuity layer;
- not every fact immediately becomes a thread; some sit as pending candidates;
- creation depends on thresholds/classification rules that will need tuning;
- grouping will sometimes be imperfect and require merge/split support;
- C7 creation must be tightly coupled to C5 evidence linking;
- downstream surfaces must understand both active threads and pending candidates.

```text
Prefer calm, deduplicated, evidence-backed thread creation
over immediate visibility for every minor extracted fact.

Hard constraint: no concern-bearing evidence may be silently dropped.
```

## Implementation notes

> Touches core components C4, C5, C6, C7, C9 (and the Ask/Workspace/Prepare/Delta
> surfaces). Several sub-decisions here (e.g. the pending-candidate object, the
> triage decision contract) may themselves warrant their own Spikes when picked
> up for implementation.

### New component — thread genesis consumer
Add a continuity/triage genesis consumer (e.g. `ThreadGenesisConsumer` /
`HealthThreadGenesisService`), likely in or near the processing worker. It
consumes events such as `fact.extracted`, `graph.entity_resolved`,
`graph.cluster_updated`, `capture.processing_completed`. It must not create
threads before enough extraction/entity-resolution context exists.

### Triage decision output contract
The triage service produces a durable decision record, e.g.:
```json
{
  "decision_id": "tgd_123",
  "user_id": "user_123",
  "input_fact_ids": ["fact_101"],
  "input_capture_ids": ["cap_001"],
  "input_graph_entity_ids": ["ent_456"],
  "decision": "CREATE_NEW_THREAD",
  "concern_key": { "concept": "cough", "type": "symptom", "body_site": null, "temporal_episode": "2026-06" },
  "confidence": 0.87,
  "reason": "explicit_user_concern",
  "target_thread_id": null,
  "created_thread_id": "thr_123"
}
```

### C7 ThreadService changes
`ThreadService.create_thread` should support system-genesis metadata:
`created_by, created_via, genesis_reason, concern_key, originating_capture_ids,
originating_fact_ids, originating_graph_entity_ids, initial_evidence_links`, and
enforce: **a system-created thread requires at least one evidence link**. Manual
user-created threads may start without extracted evidence but still record user
provenance.

### C5 evidence requirements
Write evidence links immediately on creation/attachment. Roles may include
`originating_evidence, supporting_evidence, contradicting_evidence,
resolution_evidence, user_confirmation, user_dismissal`. Key requirement:
`CREATE_NEW_THREAD` must atomically create C7 thread + C5 originating evidence —
never a thread whose origin is untraceable.

### Pending candidate object
Introduce or reuse a pending item type with fields like `candidate_id, user_id,
concern_key, display_title, candidate_type, source_capture_ids, source_fact_ids,
source_graph_entity_ids, status, confidence, reason, first_seen_at, last_seen_at,
seen_count, suggested_actions, dismissal_state, promoted_thread_id`. Statuses:
`pending, promoted, dismissed, merged, expired`. A dismissed candidate preserves
evidence and triage history.

### Promotion rules (thresholds configurable per concern type)
```text
user_confirms
OR repeated_mentions_count >= threshold
OR duration_exceeds_threshold
OR associated_with_abnormal_lab
OR associated_with_medication_issue
OR associated_with_clinician_instruction
OR associated_with_follow_up_task
OR graph_cluster_confidence >= threshold
```
Example defaults: single explicit worry / single abnormal lab / single clinician
follow-up instruction / repeated symptom / symptom with duration → create thread;
single mild symptom mention → pending candidate.

### Surfaces affected
- **Workspace:** `active_unresolved` threads; may show candidates separately under
  a calm "Things noticed" section.
- **Ask:** ground on active threads + relevant pending candidates + their evidence.
- **Prepare-for-a-visit:** primarily open `active_unresolved` threads; candidates
  only when user-selected or clearly visit-relevant.
- **Delta digest:** new active threads, material updates, important pending
  candidates, resolved/closed loops — without framing every candidate as a health
  issue.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
