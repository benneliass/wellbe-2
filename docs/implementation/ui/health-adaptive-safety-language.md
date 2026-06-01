# Health-Adaptive UI Safety Language

**Jira:** WEL-143 (E10 UI Layer)
**Status:** Foundation spec / reconciliation
**Reconciles:** WEL-43 (WB2-F040 health-adaptive UI) and WEL-91 (WB-DEV-115 state-driven tokens, never-alarm rule)
**Grounds in:** `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`, `docs/implementation/ui_vision.md` (Adaptive State Should Be Calm)

## Why this exists

Two tickets describe health-adaptive UI with different tones:

- WEL-43 (WB2-F040) frames adaptive state as ambient signal about current health state, and earlier wording allowed strong state coloring including red banners.
- WEL-91 (WB-DEV-115) requires a never-alarm rule: subtle, state-driven design tokens with accessibility and no anxiety-inducing visual language.

This document reconciles them into one binding interpretation. Where the two conflict, **WEL-91's never-alarm rule governs the implementation of WEL-43.**

## Binding Interpretation

1. Health-adaptive UI is **context and prioritization**, not alarm decoration.
2. State is expressed through **subtle token shifts** on small elements: a rail tint, a pill, an icon, a next-action card border, or a panel tint.
3. The whole app surface is **never recolored** based on health status.
4. **Full-surface red / non-dismissable alarm banners are not used** for routine concern levels.
5. **Urgent visual treatment is reserved for Safety Gate-approved urgent guidance only** (C10 `route_urgent`). It is never triggered by client-side heuristics, raw metrics, or thread state alone.
6. Every state is paired with **plain language, source, confidence, and a next action**. A color is never the only carrier of meaning.
7. Accessibility and reduced motion are required from the first implementation, not retrofitted.

## State Token Set

A small, fixed set of semantic state tokens. These map to `state.*` tokens already named in `ui_vision.md`.

| Token | Meaning | Allowed visual treatment | Not allowed |
|---|---|---|---|
| `state.stable` | resolved / monitored / nothing needed | calm neutral/teal tint on small elements | celebratory or "all clear" claims |
| `state.watch` | something to keep an eye on | soft accent on pill/rail | amber flashing, urgency copy |
| `state.needs_attention` | an open loop or due action | warm amber on the relevant element + next-action card | full-surface fill, alarm icon, countdown panic |
| `state.urgent` | Safety Gate-approved urgent guidance only | prominent but plain urgent card with approved guidance + next step | ambient/decorative red, auto-recolor, blocking modal without action |

Rules:

- `state.urgent` may only be set from a C10 decision carrying `route_urgent`. If the client cannot confirm a Safety Gate approval, it must fall back to `state.needs_attention`, never invent urgency.
- `state.needs_attention` is the strongest tone the client may apply on its own.
- A thread or item shows at most one state token at its current disclosure level.

## Source-Of-Truth For State

| Input | Allowed to drive | Notes |
|---|---|---|
| C7 `HealthThreadStatus` | `stable` / `watch` / `needs_attention` mapping for a thread | e.g. `closed`/`chronic_monitoring` → stable; `escalated` → needs_attention (never auto-urgent) |
| C9 pending item due/overdue | `needs_attention` on the relevant ledger row | overdue raises priority/order, not alarm styling |
| C10 render decision `route_urgent` | `state.urgent` | the only path to urgent treatment |
| Raw metrics / wearable values | nothing directly | must pass through C9/C10 (e.g. Live Metrics Safety Monitor) before any state |

## Copy Rules

- Use plain, steady language: "worth following up", "a result is still pending", "this is overdue".
- No diagnostic or causal phrasing (see `do_not_diagnose_rules.md`).
- No panic or pressure language ("urgent!!", "act now", count-down timers) unless it is Safety Gate-approved urgent guidance, which uses the approved wording and includes a concrete next step.
- Reassurance must not imply closure: a normal result pairs with what remains unexplained (normal-test safety net).

## Accessibility

- WCAG 2.1 AA contrast for every state token in both themes.
- No color-only meaning: pair every state with an icon + text label.
- Respect reduced motion: no flashing, pulsing, or attention-grabbing motion for any state.
- Dynamic Type / text scaling must not break state pills or next-action cards.

## WEL-43 Wording To Treat As Superseded Or Narrowed

The following WEL-43 / WB2-F040 expectations are narrowed by this reconciliation. Do not edit those tickets here; treat the rows below as the governing interpretation when implementing.

| WEL-43 / F040 expectation | Governing interpretation |
|---|---|
| "Ambient signal about current health state" reflected in the experience | Allowed only as subtle token shifts on small elements; no whole-surface recolor |
| Strong state colors / red state banners | Superseded by WEL-91 never-alarm rule; reserve red for C10-approved urgent guidance only |
| Triage level reflected in the UI | Allowed as ordering/prioritization and `needs_attention` tone; never as client-side urgency or diagnosis |

## Acceptance Criteria Mapping (WEL-143)

- Documented intended interpretation (subtle tokens, no broad alarm, urgent only via Safety Gate): "Binding Interpretation" + "State Token Set".
- Identified WEL-43 wording superseded/narrowed by WEL-91: "WEL-43 Wording To Treat As Superseded Or Narrowed".
- Existing implementation objects left unchanged: this is a spec; it does not modify WEL-43 or WEL-91 fields or any backend.

## Consumed By

WEL-139 (Journey Rail state), WEL-145 (Home attention without alarm), WEL-144 (review/state markers), and any future health-adaptive token implementation under WEL-91.
