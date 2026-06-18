# Decision: Thread genesis triage decision contract & consumer event boundary

**Status:** Proposed  
**Date opened:** 2026-06-18  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-XXX (S1 — to be created on plan approval; research recommends a shared approval gate with the concern-key Spike, see Plan-level note)  
**Blocks:** Story B0 (genesis consumer skeleton + decision ledger) and Story B1 (high-confidence auto-create path)

---

## Question

The approved parent decision (`thread-genesis-from-capture.md`, WEL-170) settled that
genesis is hybrid and owned by a dedicated continuity/triage step that produces exactly
one durable outcome per health-relevant fact (`ATTACH_TO_EXISTING_THREAD`,
`CREATE_NEW_THREAD`, `CREATE_OR_UPDATE_PENDING_CANDIDATE`, `NO_THREAD_WITH_REASON`).
It did **not** decide how to build the consumer. This record answers, for sub-Spike S1:

- **Q1 — Event boundary & home.** Which event(s) trigger genesis — `fact.extracted`
  (per fact), `capture.processing_completed` (per capture), `graph.cluster_updated`
  (after entity resolution), or a combination? Should the consumer run inside the
  existing processing-worker or in a new continuity consumer?
- **Q2 — Decision-record schema.** What fields must the durable triage decision record
  carry? Is it append-only? Where is it stored?
- **Q3 — Classification thresholds.** What makes a signal thread-worthy enough to
  auto-create vs. route to a candidate? What is the default when confidence is unknown?
- **Q4 — Idempotency.** What deterministic key prevents redelivered events from
  double-creating threads/candidates/decisions?

## Context

This is the load-bearing genesis contract: it defines the durable, auditable record of
every genesis decision and where the decision logic lives. It touches **C4** (Processing
Pipeline, the source of facts), **C6** (Knowledge Graph, entity resolution input),
**C7** (Health Thread Engine, the create/attach target), and **C9** (Continuity &
Closure, the home of the triage/genesis capability and the candidate destination). The
risk of guessing wrong is high: a wrong event boundary either double-fires genesis or
runs before C6 has resolved entities (producing fragmented/duplicate threads), and a
weak decision-record schema means genesis decisions are not auditable — directly
violating the "nothing is silently lost" guardrail. This contract becomes a stable,
hard-to-change seam that Story B0/B1, and downstream C8/C9/C13/Ask/Prepare/Delta, build on.

## Research provided

_Research received: 2026-06-18_

Provided by the user as **"Thread Genesis Implementation Plan Review — Recommended
amendments for product-owner review"** (`thread_genesis_implementation_plan_review.docx`,
dated 2026-06-18). The relevant portions for S1 are recorded faithfully below.

**On the event boundary (review §6, "Suggested event-boundary direction"):**

> Avoid firing directly on raw `fact.extracted`. It is too granular and likely to
> fragment concerns before graph normalization helps. Also be cautious about using
> `graph.cluster_updated` as the primary trigger, because cluster updates can happen
> repeatedly and may be better treated as reconciliation inputs.
>
> The cleanest direction is a synthetic event emitted after the minimum inputs are
> available: **`genesis.input_ready`**. The event should be emitted after capture write,
> fact extraction, attempted graph/entity resolution, and evidence references are
> available. A possible flow:
> `capture.processing_completed` → includes extracted facts + graph resolution status →
> `genesis.input_ready` emitted when minimum required inputs exist → genesis consumer
> writes decision records → C7/C9 side effects happen idempotently.

**On ownership/home (review §5 Q13):**

> Keep the parent under WEL-12 / E1: Health Thread Core... Make ownership explicit: the
> consumer is a continuity/triage genesis capability, not a direct C4 feature. It
> consumes C4 facts and C6 resolution, then produces C7 threads, C9 candidates, C5
> evidence links, and durable triage records.

**On the decision-record schema (review §7, "Suggested decision-record shape"):**

> The durable triage decision record should be append-oriented and idempotent. It should
> distinguish event redelivery from intentional re-evaluation under a new policy version.

Fields (verbatim table): `decision_id` (stable identifier); `user_id` (user-scoped
isolation); `source_event_id` (outbox/event provenance); `capture_id` (raw source
context); `fact_id / fact_ids` (input facts considered); `graph_node_id /
graph_cluster_id` (C6 resolution input; nullable if unavailable); `concern_key` (dedup
key used for routing); `episode_bucket` (episode grouping input); `decision` (one of
attach, create, candidate, or no-thread); `reason_code` (required, especially for
no-thread and candidate decisions); `confidence` (classifier or rules confidence);
`policy_version` (which triage policy made this decision); `target_thread_id` (for
attach/create outcomes); `candidate_id` (for candidate outcomes); `created_thread_id`
(if a new thread was created); `evidence_link_ids` (C5 links created or attached);
`decision_inputs_hash` (supports auditability and idempotency); `created_at` (audit
time); `supersedes_decision_id` (for re-evaluation/backfill; nullable).

**On the classification default (review §9, "Suggested classification default"):**

> The default for an uncertain but health-relevant signal should be **candidate**, not
> thread and not `NO_THREAD_WITH_REASON`. Candidate preserves "never alarm" by avoiding
> premature active health threads. Candidate preserves "nothing silently lost" by keeping
> concern-bearing signals visible and actionable. `NO_THREAD_WITH_REASON` should be
> reserved for facts that were evaluated and found not to be concern-forming.

**On the lossless invariant (review §13):**

> Replace "Nothing lost is met via `NO_THREAD_WITH_REASON` + auto-create" with "Nothing
> lost is met via exactly one durable outcome for every health-relevant fact: attach,
> create, candidate, or no-thread-with-reason." Add this invariant: a genesis classifier
> must never use `NO_THREAD_WITH_REASON` as a substitute for an unavailable candidate
> store.

**On granularity / coupling with the concern key (review §5 Q11):**

> Merge S1 and S3, or require them to share one approval gate. The event boundary and
> concern key are interdependent: firing on `fact.extracted` lacks stable resolution;
> firing on `capture.processing_completed` may have partial graph confidence; firing on
> `graph.cluster_updated` can repeatedly retrigger genesis. A synthetic genesis-ready
> event is likely cleaner, but it must be designed together with the concern key. Also
> split Story B into a consumer/ledger story and an auto-create story.

## Approaches considered

All approaches below are grounded only in the provided review.

- **Approach 1: Fire per `fact.extracted`.** Genesis runs on each extracted fact.
  | Pro: simplest hook; immediate. | Con: the review judges this "too granular and likely
  to fragment concerns before graph normalization helps" — it lacks stable entity
  resolution at fire time. **Rejected.**
- **Approach 2: Fire on `graph.cluster_updated`.** Genesis runs after C6 clustering.
  | Pro: best entity resolution. | Con: the review warns cluster updates "can happen
  repeatedly and may be better treated as reconciliation inputs" — using them as the
  primary trigger risks repeated retrigger. **Rejected as primary trigger; retained as a
  reconciliation input.**
- **Approach 3: Fire on `capture.processing_completed` directly.** Genesis runs once per
  capture after extraction. | Pro: per-capture, not per-fact. | Con: the review notes it
  "may have partial graph confidence" — graph/entity resolution may be incomplete.
  **Rejected as the direct trigger; used as a precondition for the synthetic event.**
- **Approach 4: Synthetic `genesis.input_ready` event (recommended by the review).** A
  dedicated event is emitted only after capture write, fact extraction, attempted graph/
  entity resolution, and evidence references are available. | Pro: guarantees the minimum
  inputs exist before genesis runs; decouples genesis from the timing quirks of the raw
  pipeline events; clean idempotent re-fire boundary. | Con: requires defining and
  emitting a new synthetic event; must be designed jointly with the concern key (S3).
  **Accepted.**

For the decision-record store: the review specifies an **append-oriented, idempotent**
record that distinguishes redelivery from intentional re-evaluation (via
`policy_version` and `supersedes_decision_id`). No mutable-in-place alternative is
supported by the review.

For the classification default: the review is explicit that the default for an uncertain
but health-relevant signal is **candidate** (not thread, not no-thread). This is the
accepted approach; the only alternatives (default-to-thread → over-create/alarm;
default-to-no-thread → silent loss) are explicitly ruled out by the review's risk table.

## Decision

**1. Event boundary (Q1).** The genesis consumer fires on a **synthetic
`genesis.input_ready` event**, not on raw `fact.extracted` and not primarily on
`graph.cluster_updated`. `genesis.input_ready` is emitted only after, for a capture:
capture write completed, fact extraction completed, graph/entity resolution attempted,
and evidence references are available. `capture.processing_completed` is a precondition
that carries extracted facts + graph resolution status; `genesis.input_ready` is emitted
when the minimum required inputs exist. `graph.cluster_updated` is treated as a
**reconciliation input** (it may trigger a re-evaluation that supersedes an earlier
decision), never as the primary genesis trigger.

**2. Home (Q1).** The consumer is a **continuity/triage genesis capability** (C9-aligned),
not a direct C4 feature. It consumes C4 facts and C6 resolution and produces C7 threads,
C9 candidates, C5 evidence links, and durable triage decision records. It may be deployed
in or adjacent to the processing-worker, but it is owned conceptually by the
continuity/triage layer.

**3. Durable decision-record schema (Q2).** Genesis writes one **append-oriented,
idempotent** triage decision record per eligible input, carrying exactly the fields in
the review's table: `decision_id`, `user_id`, `source_event_id`, `capture_id`,
`fact_id`/`fact_ids`, `graph_node_id`/`graph_cluster_id` (nullable), `concern_key`,
`episode_bucket`, `decision` (attach | create | candidate | no-thread), `reason_code`
(required — mandatory for no-thread and candidate), `confidence`, `policy_version`,
`target_thread_id`, `candidate_id`, `created_thread_id`, `evidence_link_ids`,
`decision_inputs_hash`, `created_at`, `supersedes_decision_id` (nullable). The record is
append-only; a re-evaluation under a new `policy_version` writes a new record that
references the prior via `supersedes_decision_id` rather than mutating it.

**4. Exactly-one-outcome + lossless invariant (Q3).** Every health-relevant input
resolves to exactly one durable outcome: attach, create, candidate, or
`NO_THREAD_WITH_REASON`. The **default for an uncertain but health-relevant signal is
`CREATE_OR_UPDATE_PENDING_CANDIDATE`** — never auto-thread (would alarm) and never
`NO_THREAD_WITH_REASON` (would silently lose a real signal). `NO_THREAD_WITH_REASON` is
reserved for facts evaluated and found **not** concern-forming (duplicate detail,
context-only metadata, extraction noise, normal incidental measurement, irrelevant
entity). **Hard invariant: the classifier must never use `NO_THREAD_WITH_REASON` as a
substitute for an unavailable candidate store** — which is why the minimal candidate
object (S2) must exist before the auto-create path ships (see S2 record).

**5. Idempotency (Q4).** Each decision is keyed for idempotency by `decision_inputs_hash`
(a deterministic hash over the routing inputs: `user_id` + `concern_key` +
`episode_bucket` + `policy_version` + the source input identity). Redelivery of the same
`source_event_id`/input hash is a no-op (`ON CONFLICT DO NOTHING`); an intentional
re-evaluation under a new `policy_version` is distinguished by writing a new record with
`supersedes_decision_id` set. C7/C9 side effects are applied idempotently downstream of
the decision record.

## Trade-offs accepted

- Introducing a synthetic `genesis.input_ready` event adds a new event type and emission
  responsibility to the pipeline rather than reusing an existing raw event — more moving
  parts in exchange for a stable, well-defined genesis trigger.
- This contract cannot be finalized fully independently of the concern-key contract (S3):
  the review explicitly treats them as interdependent and recommends a single approval
  gate. Accepting this record on its own without the S3 record would be premature.
- The decision ledger is append-only and policy-versioned, which costs storage and adds
  re-evaluation/supersession bookkeeping, in exchange for full auditability of "nothing
  silently lost."
- Defaulting uncertain signals to candidate makes the minimal candidate store (S2) a
  hard prerequisite for the auto-create path, enlarging the MVP relative to the original
  §6 plan.

## Implementation notes

- New event `genesis.input_ready`: define its payload (capture_id, fact_ids, graph
  resolution status/refs, evidence refs) and its emission point (after
  `capture.processing_completed` once minimum inputs exist). Emit via the existing
  outbox/event mechanism so at-least-once redelivery is handled.
- Genesis consumer: a continuity/triage capability (e.g. `ThreadGenesisConsumer` /
  `HealthThreadGenesisService`) near `backend/apps/processing-worker/`, owned by the
  continuity layer (`backend/packages/c9_continuity/` adjacency). Subscribes to
  `genesis.input_ready`; treats `graph.cluster_updated` as a reconciliation re-eval input.
- Decision-record table: append-only, idempotent on `decision_inputs_hash`
  (`ON CONFLICT DO NOTHING`), with `policy_version` and `supersedes_decision_id` columns.
  Store within the continuity/genesis package schema.
- The concern_key and episode_bucket fields are produced by the contract decided in the
  concern-key record (`thread-genesis-concern-resolution-key.md`, S3); this record and
  that one must be implemented together. Story B0 builds the consumer skeleton + decision
  ledger; Story B1 builds the high-confidence auto-create path on top.
- Atomic thread + C5 evidence creation for the `create` outcome is enforced by Story A
  (`thread-genesis-from-capture.md` and the C7 genesis invariant); genesis calls that
  invariant and never creates a thread without evidence.

**Plan-level note (Q11/Q13 coupling):** The review recommends merging S1 and S3 into one
Spike, or at minimum a single shared approval gate, because the event boundary and the
concern key are interdependent. It also recommends keeping the work parented under
WEL-12 / E1 with explicit C4/C5/C6/C9 ownership cross-links, and splitting Story B into a
consumer/ledger story (B0) and an auto-create story (B1). These plan-shape decisions are
summarized for approval alongside this record.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
