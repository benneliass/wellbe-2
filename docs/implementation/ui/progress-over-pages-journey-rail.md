# Progress Over Pages — Journey Rail

**Jira:** WEL-139 (E1 Health Thread Core / UI)
**Status:** Foundation spec
**Binds to (read-only):** C7 `HealthThreadStatus`, `/v1/threads`, `/v1/threads/{id}/transition` history
**Grounds in:** `docs/implementation/ui_vision.md` (Progress Over Pages, Journey Rail), `wellbe` legacy "Progress Over Pages"

## Purpose

Make a Health Thread feel like **one continuous journey** rather than a set of disconnected pages. The Journey Rail is the persistent representation of where a concern has been, where it is now, and what comes next — shown on Home (compact) and on Thread Detail (full).

This is a **presentation** of C7 state and transition history. It does not change the state machine, statuses, or transition rules.

## The Journey Rail

A horizontal/vertical progress rail mapped to the Health Thread lifecycle. It shows the path traveled (history), the current state, and the likely next step — without implying a clinical outcome.

### State → Rail stage mapping

C7 has eleven statuses. The rail groups them into legible journey stages while keeping the precise status one tap away.

| Journey stage | C7 `HealthThreadStatus` | Rail treatment |
|---|---|---|
| Started | `draft` | faint "not saved yet" node |
| Open | `active_unresolved`, `reopened` | active node, `state.needs_attention` if action due |
| In motion | `waiting_for_result`, `referred`, `watchful_waiting` | active node + "what we're waiting on" label |
| Needs attention | `escalated` | active node, `state.needs_attention` (never auto-urgent; see safety spec) |
| Understood | `explained` | calm completed node |
| Ongoing | `chronic_monitoring` | steady "monitored" node, not "done" |
| Closed | `closed` | calm completed node |
| Archived | `archived` | collapsed/desaturated, retrievable |

Rules:

- The rail reflects only real C7 transitions; it never fabricates stages the thread has not entered.
- Current stage is always visible; past stages are shown as traveled; the next stage is shown as a quiet "likely next" hint, never a promise.
- `chronic_monitoring` is presented as ongoing care, never as a finished/closed outcome.
- State tone follows `health-adaptive-safety-language.md`: subtle tokens, no alarm, urgent only via C10.

## Progress Over Pages Behavior

1. **One object, continuous view.** Capturing more, getting a result, or adding a note advances the *same* thread's rail. It does not spawn a new page the user has to reconcile.
2. **Movement is the feedback.** When a thread transitions, the rail visibly advances (respecting reduced motion) and a one-line "what changed" is recorded — this is the user's sense of progress.
3. **History is a path, not a log dump.** The traveled rail expands (disclosure L3) into the timeline of transitions and events; collapsed by default.
4. **No dead ends.** Every stage shows a single next action when one exists (capture, view result, prepare for visit, follow up), per the disclosure contract's L2.
5. **Returning is normal.** `reopened` is shown as the journey continuing, never as a failure or regression.

## Home (compact) vs Thread Detail (full)

| | Home compact rail | Thread Detail full rail |
|---|---|---|
| Shows | current stage + one-line what changed + next action | full traveled path, current stage, likely next, expandable history |
| Disclosure | L0–L2 | L0–L4 |
| Interaction | tap → open thread at current stage | tap stage → jump to that point in timeline |
| Evidence | SourceMarker on the "what changed" line | per-event source via Evidence Drawer |

## "What Changed" Line

Each thread surfaces a short, plain "what changed since you last looked" line, derived from the most recent transition/event. It:

- uses calm, non-diagnostic language;
- carries a `SourceMarker` and review marker (see `evidence-ui-primitives.md`);
- is the connective tissue between Home (WEL-145) and the rail.

## Accessibility + Motion

- Rail is keyboard-navigable; each stage is a focusable item with an accessible name (stage + status + what changed).
- Not color-only: stage state conveyed by label + icon + position, not hue alone.
- Reduced motion: rail advancement is a short, optional transition; the static state is always fully meaningful.

## Acceptance Criteria Mapping (WEL-139)

- Health Thread presented as a continuous journey, not disconnected pages: "Progress Over Pages Behavior".
- Journey Rail reflects C7 lifecycle without changing the state machine: "State → Rail stage mapping" + read-only binding.
- Compact on Home, full on Thread Detail: "Home (compact) vs Thread Detail (full)".
- Calm, non-diagnostic progress feedback: "What Changed" line + safety-language conformance.

## Consumed By

WEL-145 (Home rail + what-changed), WEL-140 (rail disclosure levels), WEL-144 (markers on the what-changed line), Thread Detail screen story (downstream).
