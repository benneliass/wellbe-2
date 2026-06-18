# Decision: When and how a capture (or detected concern) opens a Health Thread

**Status:** Open  
**Date opened:** 2026-06-18  
**Date approved:** YYYY-MM-DD (fill on approval)  
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

<!-- To be filled when the user provides research. Verbatim or faithful summary; no agent self-research. -->

_Research received: YYYY-MM-DD_

## Approaches considered

<!-- To be filled after research is received. Each approach grounded in the provided research. -->

## Decision

<!-- To be proposed after research, approved by user. -->

## Trade-offs accepted

<!-- To be filled with the decision. -->

## Implementation notes

<!-- To be filled after approval. Likely touches: the capture/processing path (backend/apps/processing-worker, backend/apps/api/src/wellbe_api/routers/capture_v1.py), C7 ThreadService.create_thread, the fact.extracted event consumer, and the Ask/Workspace/Delta surfaces that depend on threads existing. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
