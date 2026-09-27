# Decision: C9 due/overdue reminders use a ledger sweeper on the homeserver

**Status:** Proposed (owner decisions on windows and in-app-only recorded below)
**Date opened:** 2026-09-27
**Refines:** [continuity-pending-ledger-durable-timers.md](continuity-pending-ledger-durable-timers.md) — scoped to non-safety reminders; that record stays authoritative for safety-bearing timers.

---

## Question

Which mechanism advances C9 pending items `scheduled -> due -> overdue` on the small homeserver cluster so the user gets in-app reminders: the per-item Temporal workflow, or a periodic sweep of the ledger?

## Context

- Owner decisions: result waits are due after **7 days**, referral waits after **4 weeks**; reminders are **in-app only** (no push, email, or messaging).
- The Temporal workflow and `fire_timer` activity exist (`wellbe_c9_continuity.temporal`), but nothing starts or signals per-item workflows (only `smoke.py` does). Wiring that means a new outbox consumer doing Signal-With-Start, reschedule/cancel signals on every resolution, and a second timer for overdue.
- Temporal (`temporalio/auto-setup`) already costs up to 768Mi on a node shared with media/GPU/monitoring stacks.
- These reminders never request a C7 thread transition. They set ledger status and emit `c9.pending_item.due` / `.overdue`. The approved record's objection to a poller applies to *safety-bearing* timers (closure, normal-test follow-up automation); it explicitly allows a relational poller for non-safety reminders.

## Decision

The continuity-worker runs **exactly one** timer mechanism, chosen by `WELLBE_C9_TIMER_MECHANISM`:

- `sweeper` (default, and the homeserver setting): every `WELLBE_C9_SWEEP_INTERVAL_SECONDS` (60s) it claims one due row at a time `FOR UPDATE SKIP LOCKED`, and fires it in that same transaction:
  - `scheduled` with `due_at <= now` → `ContinuityService.advance_due_item` = `fire_timer` (stale epoch / terminal → recorded no-op) then an epoch bump that arms the overdue phase;
  - `due` with `due_at + grace <= now` (grace `WELLBE_C9_OVERDUE_GRACE_DAYS`, 2) → `fire_overdue_timer` (same stale-epoch protocol).
- `temporal`: the existing per-item workflow worker. It is not started for these items today.

Running both against one ledger is unsupported. The switch is a single value, so the choice is explicit.

New waiting items are dated where C9 reconciles `thread.state_changed`: `due_at = C7 transition time + window`, `due_precision = relative_policy`, status `scheduled`. Windows live in one policy table (`wellbe_c9_continuity.policy.DuePolicy`), configured with `WELLBE_C9_RESULT_WINDOW_DAYS` / `WELLBE_C9_REFERRAL_WINDOW_DAYS`, which Helm renders from the single `c9Policy` values block. Migration 024 backfills existing active result/referral items with the same defaults.

In-app notifications come from a dedicated C12 **notification-worker**. It is the sole consumer of `c9.pending_item.created/.due/.overdue` and writes `notifications.in_app_notifications`, keyed idempotently by `(item, phase, timer epoch)`. It drops reminders for items that are already settled, and "due" once the item is already overdue.

## Trade-offs accepted

- Reminder latency is up to one sweep interval (60s), which is irrelevant for day-scale windows.
- Durability comes from the Postgres ledger itself. A sweeper outage only delays reminders, and the next sweep catches up (items past both thresholds go due then overdue in one sweep; the notification consumer then suppresses the superseded "due").
- Resolution and closure now lock the item row (`FOR UPDATE`) before bumping the epoch, so a concurrent sweep either skips the row or its fire is overwritten by the terminal status. The terminal status always wins.

## Revisit when

Any C9 timer must request a C7 transition (closure, safety-net automation). Those remain Temporal-only per the approved record: switch `timerMechanism` to `temporal`, wire Signal-With-Start from a C9 outbox consumer, and add the overdue phase to the workflow.
