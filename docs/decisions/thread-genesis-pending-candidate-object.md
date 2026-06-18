# Decision: Pending thread candidate object, lifecycle, and promotion rules

**Status:** Proposed  
**Date opened:** 2026-06-18  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-XXX (S2 — to be created on plan approval; research recommends splitting into S2a minimal-MVP contract and S2b post-MVP enrichment, see Plan-level note)  
**Blocks:** Story C0 (minimal pending-candidate path) and Story C1 (candidate promotion / merge-dismiss polish / richer API)

---

## Question

The approved parent decision (`thread-genesis-from-capture.md`, WEL-170) settled that
weak/ambiguous signals become **pending thread candidates** rather than active threads,
and that `CREATE_OR_UPDATE_PENDING_CANDIDATE` is one of the four durable genesis
outcomes. It did not decide the candidate object itself, its owner, or whether it is MVP.
This record answers, for sub-Spike S2:

- **Q5 — Object & ownership.** What fields and statuses does the candidate carry, and
  which component owns it (extend the C9 pending-item ledger vs. a new C7-adjacent
  store)? How does it relate to the existing C9 pending-item ledger and to "relevance
  candidates" (WEL-141/142) so we do not build two overlapping candidate concepts?
- **Q6 — Is the candidate layer MVP or post-MVP?** The §6 proposal defers it entirely.
  Does deferring it acceptably honor "nothing is silently lost," or is a candidate
  destination essential to MVP?
- **Q7 — Promotion.** Which triggers/thresholds promote a candidate to a thread, and are
  they configurable per concern type?

## Context

Candidates are the non-alarming, lossless destination for concern-bearing signals that
should stay visible without becoming active health threads. This touches **C7** (Health
Thread Engine — promotion target and adjacency) and **C9** (Continuity & Closure — the
pending-item ledger where the candidate most naturally lives). The risk of guessing
wrong is two-sided: build a second candidate concept that overlaps C9's pending-item
ledger and relevance candidates (WEL-141/142), or — if deferred wrongly — leave a large
class of real mid-confidence signals invisible, quietly breaking "nothing is silently
lost." Q6 is the pivotal MVP-scoping decision and the single biggest judgment call in the
genesis plan.

## Research provided

_Research received: 2026-06-18_

Provided by the user as **"Thread Genesis Implementation Plan Review — Recommended
amendments for product-owner review"** (`thread_genesis_implementation_plan_review.docx`,
dated 2026-06-18). The relevant portions for S2 are recorded faithfully below.

**Executive recommendation (review header):**

> Do not approve the section 6 plan exactly as written. Approve a reshaped Alternative
> A/B hybrid: MVP should include high-confidence auto-thread genesis and a minimal
> pending-candidate path. Full candidate UX and richer promotion behavior can stay
> post-MVP, but **the durable candidate object itself should not be deferred.**
>
> Reason: The approved parent decision already defines
> `CREATE_OR_UPDATE_PENDING_CANDIDATE` as a durable genesis outcome. If candidates are
> deferred entirely, the MVP consumer must either over-create active threads, misuse
> `NO_THREAD_WITH_REASON` for concern-bearing signals, or make mid-confidence signals
> invisible. Each option conflicts with at least one guardrail.

**On why deferral is too large (review §1):**

> `NO_THREAD_WITH_REASON` is appropriate for facts that are deliberately not
> concern-forming: duplicate detail, context-only metadata, unsupported extraction noise,
> normal incidental measurement, or irrelevant extracted entity. For weak or ambiguous
> **concern-bearing** facts, the approved parent decision points to
> `CREATE_OR_UPDATE_PENDING_CANDIDATE`. A candidate is the non-alarming, lossless
> destination for signals that should stay visible without becoming active health threads.

Risk if candidates are entirely post-MVP (verbatim): over-create threads → "Violates
'never alarm' by turning too many weak mentions into active tracked concerns"; mark
concern-bearing signals as `NO_THREAD_WITH_REASON` → "Weakens 'nothing silently lost'
because real signals are internally logged but not product-visible or actionable";
ignore mid-confidence signals until later → "Recreates the empty-loop problem for a
large class of real user inputs."

**On the MVP-minimal vs post-MVP split (review §2.1 and §2.2):**

> **2.1 MVP candidate layer — required:** Candidate table/store: Yes. Candidate status
> model: Yes: pending, promoted, dismissed, merged, and possibly expired. Durable triage
> decision outcome: Yes: `CREATE_OR_UPDATE_PENDING_CANDIDATE` must be real. Evidence
> links: Yes: candidate must trace to source facts/captures. Idempotent create/update:
> Yes. User visibility: Yes, at least basic Workspace "Things noticed" or equivalent.
> User actions: Minimal confirm, dismiss, and merge. Auto-promotion rules: Basic
> repeat-signal promotion can be MVP if simple; richer rules can wait.
> Ask/Prepare/Delta candidate-aware behavior: Can stay post-MVP.
>
> **2.2 Post-MVP candidate layer — optional enrichment:** Richer promotion logic and
> configurable thresholds. Candidate-aware Ask, Delta, Prepare, and notification
> behavior. Expiry policies and more nuanced merge/dismiss workflows. More polished
> "things noticed" UX beyond the minimal MVP visibility requirement.

**On ownership (review §5 Q13):**

> Make ownership explicit: the consumer is a continuity/triage genesis capability, not a
> direct C4 feature. It consumes C4 facts and C6 resolution, then produces C7 threads,
> **C9 candidates**, C5 evidence links, and durable triage records.

**On the classification default (review §9):**

> The default for an uncertain but health-relevant signal should be **candidate**, not
> thread and not `NO_THREAD_WITH_REASON`.

**On the revised MVP definition (review §10):**

> After a real capture-only user submits health-relevant data, WellBe creates
> evidence-backed active threads for high-confidence concerns, **creates evidence-backed
> pending candidates for weak/ambiguous concern signals**, records an auditable genesis
> decision for every health-relevant fact, and keeps Workspace non-empty without creating
> alarming noise.

**On story shape (review §4):** C0 — "Minimal pending-candidate path" (MVP): create or
update candidate for weak/ambiguous concern-bearing signals and expose minimally in
Workspace or equivalent. C1 — "Candidate promotion, merge/dismiss polish, richer API"
(post-MVP): add fuller lifecycle behavior and configurable promotion rules.

> **Note on Q5 (relationship to C9 pending-item ledger and relevance candidates,
> WEL-141/142):** the provided review places the candidate as a "C9 candidate" produced
> by the continuity/triage genesis capability, and warns generally against building two
> overlapping candidate concepts, but it does **not** give a detailed reconciliation
> between the genesis pending-candidate, the existing C9 pending-item ledger, and the
> relevance candidates of WEL-141/142. That reconciliation detail is flagged below as not
> fully covered by the provided research.

## Approaches considered

All approaches below are grounded only in the provided review.

- **Approach 1: Defer the candidate object entirely to post-MVP (the original §6 plan).**
  | Pro: smaller MVP; candidate complexity deferred. | Con: the review rejects this — with
  no candidate destination the MVP consumer must over-create threads (violates never
  alarm), misuse `NO_THREAD_WITH_REASON` for concern-bearing signals (violates nothing
  lost), or drop mid-confidence signals (recreates the empty-loop problem). **Rejected.**
- **Approach 2: Full rich candidate layer in MVP.** | Pro: complete candidate UX from day
  one. | Con: the review scopes this down — full UX, richer promotion logic, configurable
  thresholds, candidate-aware Ask/Delta/Prepare, and expiry policies are explicitly
  marked optional enrichment that "can stay post-MVP." **Rejected as MVP scope.**
- **Approach 3: Minimal durable candidate object in MVP + post-MVP enrichment (the
  reshaped A/B hybrid recommended by the review).** | Pro: makes
  `CREATE_OR_UPDATE_PENDING_CANDIDATE` a real, lossless, non-alarming destination from day
  one while keeping rich behavior deferred; satisfies the revised MVP statement. | Con:
  enlarges MVP relative to §6; adds a durable store and basic visibility before any rich
  candidate UX exists. **Accepted.**

For ownership, the review's only explicit grounding is that candidates are produced as
**"C9 candidates"** by the continuity/triage capability — i.e. a continuity-owned object,
not a direct C4 feature. The detailed choice between extending the C9 pending-item ledger
vs. a distinct C7-adjacent store, and reconciliation with WEL-141/142 relevance
candidates, is not fully resolved by the provided research (see note above).

## Decision

**1. The durable pending-candidate object is MVP, not deferred (Q6).** A minimal but
durable candidate object ships in MVP. `CREATE_OR_UPDATE_PENDING_CANDIDATE` must be a
real, persisted outcome so the genesis classifier has a lossless, non-alarming
destination for weak/ambiguous concern-bearing signals. The MVP loop is therefore "create
evidence-backed active threads for high-confidence concerns **and** evidence-backed
pending candidates for weak/ambiguous signals," per the review's revised MVP statement.

**2. Minimal MVP candidate contract (Q5, scope).** The MVP candidate object provides:
- a durable candidate table/store;
- a status model: `pending`, `promoted`, `dismissed`, `merged`, and `expired`;
- evidence links tracing the candidate to its source facts/captures (no orphan candidates);
- idempotent create/update (keyed off the concern key from S3, consistent with the S1
  decision-record idempotency);
- basic user visibility — at least a Workspace "Things noticed" (or equivalent) surface;
- minimal user actions — confirm, dismiss, merge (dismissal preserves evidence and triage
  history, per the parent decision);
- basic repeat-signal auto-promotion only (simple), if simple to implement.

**3. Ownership (Q5).** The candidate is a **continuity-owned ("C9") object** produced by
the continuity/triage genesis capability, promotion-linked to C7. It is conceptually
distinct from a generic C9 pending-item (referral/result/task) and from WEL-141/142
relevance candidates. To avoid building two overlapping candidate concepts, the candidate
store must be reconciled against the existing C9 pending-item ledger and relevance
candidates during implementation. **This reconciliation detail is not fully resolved by
the provided research** and is carried as an explicit implementation question to settle
within S2a, defaulting to: a single continuity-owned candidate concept that the genesis
path writes to, rather than a new parallel store, unless reconciliation shows the
existing ledger cannot represent a genesis candidate.

**4. Promotion (Q7).** MVP promotion is limited to **basic repeat-signal promotion** plus
explicit **user confirm**. The richer promotion triggers from the parent decision
(duration thresholds, association with abnormal lab / medication issue / clinician
instruction / follow-up task, graph-cluster confidence) and **per-concern-type
configurable thresholds** are **post-MVP** enrichment (Story C1).

**5. Phasing split (Q6 / plan).** Split the candidate work into:
- **S2a (MVP):** the minimal durable candidate contract above (Decision points 1–4 MVP
  scope), unblocking Story C0.
- **S2b (post-MVP):** richer promotion logic, configurable thresholds, candidate-aware
  Ask/Delta/Prepare/notifications, expiry policies, nuanced merge/dismiss, polished
  "Things noticed" UX — unblocking Stories C1 and D.

## Trade-offs accepted

- MVP grows relative to the original §6 plan: a durable candidate store, basic
  visibility, and minimal user actions must ship before the genesis loop is "done." This
  is accepted because deferring the candidate object entirely conflicts with the
  already-approved genesis contract and the guardrails.
- The C9-ledger-vs-new-store and WEL-141/142 reconciliation is not fully answered by the
  provided research; we accept resolving it inside S2a with a documented default
  (single continuity-owned candidate concept) rather than blocking on more research.
- MVP promotion is deliberately thin (repeat-signal + user confirm). Some mid-confidence
  signals that would promote under richer rules will sit as candidates longer until the
  post-MVP enrichment lands.
- Candidate-aware behavior in Ask/Prepare/Delta is deferred, so those surfaces remain
  thread-primary in MVP even though candidates exist and are visible in Workspace.

## Implementation notes

- Candidate object fields (aligned with the parent decision and the S1/S3 contracts):
  `candidate_id`, `user_id`, `concern_key`, `episode_bucket`, `display_title`
  (calm/personal), `candidate_type`, `source_capture_ids`, `source_fact_ids`,
  `source_graph_entity_ids`, `evidence_link_ids`, `status` (pending | promoted |
  dismissed | merged | expired), `confidence`, `reason_code`, `first_seen_at`,
  `last_seen_at`, `seen_count`, `promoted_thread_id`. Create/update is idempotent on the
  concern key + episode bucket.
- Owns reconciliation with `backend/packages/c9_continuity/` (pending-item ledger) and the
  relevance-candidate concept (WEL-141/142): prefer one continuity-owned candidate
  concept; do not stand up a second parallel store unless the ledger cannot represent a
  genesis candidate.
- Genesis writes candidates via the `CREATE_OR_UPDATE_PENDING_CANDIDATE` outcome of the
  S1 decision contract; the candidate is the default destination for uncertain
  health-relevant signals.
- Promotion to a thread reuses Story A's atomic thread + C5 evidence invariant; a promoted
  candidate sets `promoted_thread_id` and transitions to `promoted`.
- Minimal Workspace "Things noticed" surface renders `pending` candidates with calm,
  personal-first framing ("Something I noticed" / "Possible thing to track"), never
  clinical/alarming language; any user-facing candidate text still passes the C10 gate.

**Plan-level note (Q6/Q11):** The review recommends splitting this Spike into S2a
(minimal MVP candidate contract, run before implementation of the auto-create path) and
S2b (post-MVP enrichment), and splitting the candidate Story into C0 (MVP minimal path)
and C1 (post-MVP polish). These plan-shape decisions are summarized for approval
alongside this record.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
