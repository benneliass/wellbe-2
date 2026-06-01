# Home — Continuity, Open Loops, and What Changed

**Jira:** WEL-145 (E2 Care Continuity / UI)
**Status:** Foundation spec
**Binds to (read-only):** C9 `PendingItemType`, `PendingItemStatus`, `next_action_code`, `/v2/pending-items`; C7 threads; C13 `PendingItemV2`
**Grounds in:** `docs/implementation/ui_vision.md` (Personal Home, Continuity), `docs/workflows/`

## Purpose

Define Home so it is led by **continuity** — open loops, what's overdue, and what changed — instead of being a feed or a dashboard of metrics. Home answers one question on open: *what does this person need to know or do about their health right now?*

This is a **composition** spec over existing C9/C7 data. It does not add backend or change the pending-item ledger.

## Home Information Hierarchy

Following the progressive-disclosure contract (L0–L2 visible without scroll):

```
HOME
├── L0  Holistic status line   "Two things need a look. Everything else is steady."
├── L1  Attention region        open loops + what changed (the heart of Home)
│        ├── Needs attention     overdue / due pending items, escalated threads
│        ├── In motion           waiting on results/referrals, watchful waiting
│        └── What changed        recent transitions/results since last visit
├── L2  Primary action          one capture entry point + per-item next action
└── L3+ (on intent)             open a thread's journey, ledger, packet, memory
```

- Home never opens into raw timelines, graphs, or metric walls (those are deeper levels / other surfaces).
- At most one primary action is emphasized; everything else is a quiet next step.

## Open Loops (Continuity Ledger Surface)

Open loops are drawn from C9 pending items. Home shows the **actionable** subset, grouped by what the user can do, not by internal type.

| Home grouping | C9 `PendingItemStatus` | C9 `PendingItemType` examples |
|---|---|---|
| Needs attention | `due`, `overdue` | `follow_up_due`, `repeat_test_due`, `normal_test_safety_net`, `user_next_step` |
| In motion | `waiting_external`, `scheduled`, `in_progress`, `result_received` | `result_pending`, `referral_pending` |
| Steady (folded) | `active`, `no_due_date` | any low-urgency item, shown on expand |
| Done (out of Home) | `resolved`, `cancelled`, `superseded` | not surfaced on Home; visible in the ledger |

Rules:

- `overdue` raises **order and priority**, and uses `state.needs_attention` tone — never alarm styling or a panic timer (see `health-adaptive-safety-language.md`).
- Each open loop shows its `next_action_code` as a single plain next step (e.g. "book follow-up", "log result", "ask about referral").
- `normal_test_safety_net` items are surfaced as gentle open loops, never as "all clear" — a normal result does not silently close a concern.
- Items the user can't act on yet (`waiting_external`) live under "In motion" with a "what we're waiting on" label, not in "Needs attention".

## What Changed

A short, scannable region of recent, meaningful changes since the user last looked:

- new results received, thread transitions (C7), corrections that updated something, newly surfaced relevance candidates (post-MVP).
- each entry is one calm line + a `SourceMarker`/`ReviewMarker` (see `evidence-ui-primitives.md`) + a tap target into the thread's Journey Rail (WEL-139).
- non-diagnostic, no causal claims; "your result came back" not "your result is abnormal/concerning" unless C10-approved.

## Threads On Home

Active Health Threads appear as compact Journey Rails (WEL-139), ordered by attention then recency. Each card shows: thread title, current stage, "what changed" line, and one next action. Closed/archived threads are not on Home; they're reachable via search/history.

## What Home Is Not

- Not a social/activity feed.
- Not a metrics dashboard (no vitals walls as the default surface).
- Not an institution or clinician view — Home is the individual's, personal-first, no default cross-patient or aggregate content.
- Not an alarm surface — attention is expressed by ordering and subtle tone, not by recoloring the screen.

## Accessibility + Behavior

- L0 status line is the page's accessible summary; regions are landmarked and labeled.
- Not color-only: groupings carry labels + icons.
- Empty state is calm and affirming without implying medical closure ("Nothing needs your attention right now. We'll surface anything that changes.").
- Reduced motion respected for any what-changed/rail movement.

## Acceptance Criteria Mapping (WEL-145)

- Home led by continuity, open loops, and what changed: "Home Information Hierarchy" + "Open Loops" + "What Changed".
- Open loops driven by C9 without changing the ledger: read-only binding + status/type mapping.
- Calm, non-alarming, personal-first framing: "What Home Is Not" + safety-language conformance.
- Composes existing primitives (rails, markers, disclosure): "Threads On Home" + cross-links.

## Consumed By

WEL-139 (compact rails), WEL-140 (Home disclosure), WEL-144 (markers), Personal Home screen story (downstream).
