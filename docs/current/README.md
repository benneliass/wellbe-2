# Current behavior

This directory is the only place that answers what WellBe can do in the code today.

| Question | Read |
|---|---|
| What runs today? | [capability-index.md](capability-index.md), then the evidence path on that row |
| What are we building? | [component map](../architecture/component-map.md) and [feature backlog](../feature-backlog/feature_backlog.md) |
| What is still unbuilt? | [development backlog](../architecture/development-backlog.md) |
| Why was a core choice made? | [decision records](../decisions/README.md) |
| What must not change? | The bible files listed in `AGENTS.md` |
| What should the UI feel like? | [UI vision](../implementation/ui_vision.md) |

`docs/system-overview.md` is a pointer. It is not a status source.

## Status words

| Status | Meaning |
|---|---|
| `shipped` | A person can use this path on the local stack today. No remaining gap. |
| `partial` | Real code, and a named gap. |
| `designed` | Specified, and not in the code yet. |
| `deferred` | Explicitly out of the current build. |

The feature backlog `status` column is product phase (`core build`, `near-term`, `later`). It is not one of these four words.

## When the index changes

Update [capability-index.md](capability-index.md) in the same change as the code when a route or API operation appears, disappears, or changes what the user can do, when a status changes, or when a named gap opens or closes. Then run `python3 scripts/check-capability-index.py`.

Leave the index alone for a refactor that preserves behavior, and for tests, copy, styling, lockfiles, a decision-record approval, or a Jira-only edit. Approving a decision does not set `shipped`. Moving a Jira issue to Done does not set `shipped`.

One WEL issue covers the behavior change. Do not open a second issue whose only job is to update this index. A `partial` gap names that issue's key when one exists.

One sentence per row. No how-it-works, no identity prose, and no task diary.
