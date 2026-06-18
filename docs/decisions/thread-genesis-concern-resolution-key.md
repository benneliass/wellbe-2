# Decision: Concern resolution key, dedup/grouping, and reopen-vs-new-episode policy

**Status:** Approved  
**Date opened:** 2026-06-18  
**Date approved:** 2026-06-18  
**Approved by:** User  
**Jira Spike:** WEL-171 (merged S1+S3 — one shared approval gate with the triage-decision-contract record `thread-genesis-triage-decision-contract.md`)  
**Blocks:** WEL-176 (Story B1 — high-confidence auto-create path; cannot dedup without the key)

---

## Question

The approved parent decision (`thread-genesis-from-capture.md`, WEL-170) settled that
genesis dedups on a user-scoped **concern resolution key** (normalized concept + concern
type + body site/laterality + temporal episode bucket + source context), never on
capture-id or fact-id. It did not finalize the key's source, shape, episode bucketing, or
reopen policy. This record answers, for sub-Spike S3:

- **Q8 — Concept normalization source.** Does the normalized concept come from C6 entity
  resolution, a separate normalization step, or C4 extraction? Is C6 clustering mature
  enough to anchor dedup, or is a simpler interim key needed?
- **Q9 — Key shape & episode bucketing.** The exact key composition; how to bucket
  temporal episodes; the reopen-vs-new-episode policy (tied to the approved C7 state
  machine).
- **Q10 — Dedup precedence & merge/split.** The precedence order for routing new
  evidence, and how user merge/split corrections feed back into the key.

## Context

The concern key decides whether new evidence joins an existing thread or spawns a new
one — it is the difference between one coherent "Cough" thread and four noisy fragments.
This touches **C6** (Knowledge Graph — source of normalized concepts) and **C7** (Health
Thread Engine — dedup target and reopen lifecycle). The risk of guessing wrong is direct:
too-loose keys merge unrelated concerns; too-tight keys fragment one concern across many
threads; a wrong episode/reopen policy either resurrects closed threads inappropriately
or loses the link between a recurrence and its history. The key and the genesis event
boundary (S1) are interdependent — the trigger determines what C4/C6 material is
available for keying.

## Research provided

_Research received: 2026-06-18_

Provided by the user as **"Thread Genesis Implementation Plan Review — Recommended
amendments for product-owner review"** (`thread_genesis_implementation_plan_review.docx`,
dated 2026-06-18). The relevant portions for S3 are recorded faithfully below.

**On the concern key (review §8, "Suggested concern-key direction"):**

> The concern key should be stable enough for dedup without being so over-specific that
> every mention fragments.
>
> `user_id  concern_type  normalized_concept_id  body_site  laterality  episode_bucket
> source_context_class`
>
> - `normalized_concept_id` should prefer C6 resolution when available.
> - Fallback normalization is acceptable for MVP if C6 confidence is insufficient.
> - `episode_bucket` should use event date or onset date when available, not just
>   ingestion time.
> - `source_context_class` should distinguish symptom mention, lab abnormality, clinician
>   instruction, medication issue, and similar categories.
> - Do not include `capture_id` or `fact_id` in the concern key. Those belong in decision
>   and evidence records.

**On dedup precedence (review §8):**

> Recommended dedup precedence: **active thread > watchful_waiting / waiting_for_result
> thread > draft/user-created compatible thread > candidate > recently closed thread
> eligible for reopen > new thread or new candidate.**

**On reopen policy (review §8):**

> Be careful with auto-reopening closed threads. A recurrence should often become a
> linked recurrence rather than silently reopening a closed concern, unless it is inside
> a defined grace window or the user explicitly confirms it is the same concern.

**On the event-boundary coupling (review §6):**

> Avoid firing directly on raw `fact.extracted`. It is too granular and likely to
> fragment concerns before graph normalization helps... The cleanest direction is a
> synthetic event emitted after the minimum inputs are available (`genesis.input_ready`),
> [emitted] after capture write, fact extraction, attempted graph/entity resolution, and
> evidence references are available.

**On granularity / coupling with S1 (review §5 Q11):**

> Merge S1 and S3, or require them to share one approval gate. The event boundary and
> concern key are interdependent... A synthetic genesis-ready event is likely cleaner,
> but it must be designed together with the concern key.

> **Note on Q10 (merge/split feedback into the key):** the provided review specifies the
> dedup precedence order and the reopen policy, but it does **not** give a detailed
> mechanism for how user merge/split corrections feed back into the concern key. That
> mechanism is flagged below as not fully covered by the provided research.

## Approaches considered

All approaches below are grounded only in the provided review.

- **Approach 1: Concept from C4 extraction only.** Use the raw extracted concept as the
  key anchor. | Pro: always available at extraction time. | Con: the review warns that
  firing/keying before "graph normalization helps" fragments concerns — raw extraction
  lacks cross-capture resolution. **Rejected as the primary source.**
- **Approach 2: Concept from C6 resolution only, no fallback.** Require a resolved C6
  `normalized_concept_id`. | Pro: best grouping. | Con: the review notes C6 confidence may
  be "insufficient" and explicitly allows a fallback for MVP — a hard C6 requirement would
  block keying when resolution is weak. **Rejected as an absolute requirement.**
- **Approach 3: Prefer C6 resolution, fall back to a simpler normalization for MVP (the
  review's recommendation).** Use `normalized_concept_id` from C6 when available;
  otherwise a fallback normalization. | Pro: stable grouping when C6 is confident, without
  blocking genesis when it is not. | Con: two normalization paths to maintain; fallback
  keys may occasionally regroup once C6 matures. **Accepted.**
- **Episode bucketing — by event/onset date vs. ingestion time.** The review prefers
  **event date or onset date when available, not just ingestion time**, so a backdated or
  late-logged mention groups into the correct episode. **Accepted (event/onset preferred,
  ingestion as fallback).**
- **Reopen — auto-reopen closed thread vs. linked recurrence.** The review prefers
  **linked recurrence** over silent auto-reopen, except inside a defined grace window or
  on explicit user confirmation. **Accepted.**

## Decision

**1. Concept normalization source (Q8).** The key's concept anchor is
`normalized_concept_id`, which **prefers C6 entity resolution when available** and falls
back to a simpler normalization step for MVP when C6 confidence is insufficient. Genesis
is not blocked when C6 resolution is weak; the fallback key is used and may be
reconciled as C6 matures.

**2. Key shape (Q9).** The user-scoped concern resolution key is:

```text
user_id
+ concern_type
+ normalized_concept_id      (prefer C6; MVP fallback normalization allowed)
+ body_site
+ laterality
+ episode_bucket
+ source_context_class       (symptom mention | lab abnormality | clinician instruction |
                              medication issue | similar categories)
```

`capture_id` and `fact_id` are **excluded** from the concern key — they belong in the
decision record and evidence records (per the S1 contract).

**3. Episode bucketing (Q9).** `episode_bucket` is computed from **event date or onset
date when available, not just ingestion time**, so repeated mentions of one episode group
together and a genuinely later recurrence buckets separately.

**4. Dedup precedence (Q10).** New evidence is routed by this precedence before creating
anything new:

```text
active thread
> watchful_waiting / waiting_for_result thread
> draft / user-created compatible thread
> candidate
> recently closed thread eligible for reopen
> new thread or new candidate
```

**5. Reopen-vs-new-episode policy (Q9/Q10).** Auto-reopening a closed thread is avoided.
A recurrence becomes a **linked recurrence** (a new thread/episode linked to the prior as
related/recurrent) rather than silently reopening a closed concern — **unless** it falls
inside a defined grace window **or** the user explicitly confirms it is the same concern.
This is consistent with the approved C7 state machine
(`health-thread-state-machine-enforcement.md`).

**6. Merge/split correction feedback (Q10) — partial.** The provided research does not
specify the mechanism for feeding user merge/split corrections back into the concern key.
Pending that detail being resolved within the (merged) Spike, the default is: **user
merge/split actions are authoritative and recorded as corrections (C11-layered), creating
a key-mapping override** that subsequent genesis decisions honor — corrections never
overwrite raw/derived data. This sub-point is explicitly flagged as not fully grounded in
the provided research and to be confirmed during the Spike.

## Trade-offs accepted

- Two normalization paths (C6-preferred + MVP fallback) add maintenance and the
  possibility that fallback-keyed items regroup once C6 clustering matures.
- Preferring linked-recurrence over auto-reopen means a true recurrence of a recently
  closed concern may appear as a new (linked) thread rather than continuing the old one,
  unless within the grace window or user-confirmed — chosen to avoid inappropriately
  resurrecting closed concerns.
- The concern key cannot be finalized fully independently of the genesis event boundary
  (S1): they are interdependent and the review recommends a single approval gate.
- The merge/split-feedback mechanism is only provisionally decided (C11-layered override
  default) because the provided research does not detail it.

## Implementation notes

- Key construction lives in the genesis consumer (S1) and is the dedup input to both
  thread routing (Story B1) and candidate create/update (S2/Story C0). The
  `concern_key` and `episode_bucket` fields written into the S1 decision record are
  produced here.
- `normalized_concept_id`: prefer the C6 resolved concept
  (`backend/packages/c6_graph/`); implement a deterministic MVP fallback normalization for
  low-confidence cases. Body site / laterality / source_context_class derive from C4/C6.
- `episode_bucket`: derive from event/onset date where the capture carries it, else
  ingestion time; bucketing granularity to be set in the Spike.
- Dedup precedence and reopen logic interoperate with the approved C7 state machine; the
  "recently closed thread eligible for reopen" tier and the grace window are the
  integration points with `health-thread-state-machine-enforcement.md`.
- Merge/split: record user corrections via the Correction Service (C11,
  `correction-service-layered-provenance.md`) as authoritative key-mapping overrides;
  finalize the exact representation in the Spike.

**Plan-level note (Q11/Q12):** The review recommends **merging S1 and S3 into one Spike**
(or one shared approval gate) because the event boundary and concern key are
interdependent, and confirms the WEL-23 (C5) → Story A dependency is real. These
plan-shape decisions are summarized for approval alongside this record.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
