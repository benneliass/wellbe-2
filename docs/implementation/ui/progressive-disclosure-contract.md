# Progressive Disclosure Contract

**Jira:** WEL-140 (E10 UI Layer)
**Status:** Foundation spec
**Grounds in:** `docs/implementation/ui_vision.md` (Journey Funnel), `docs/system-design/system_principles.md`

## Purpose

Define a single, shared progressive-disclosure model so every patient-facing WellBe surface reveals complexity by relevance and user intent, not by default. This is the contract that makes "Journey Funnel" concrete and consistent across screens.

## Disclosure Levels

Every primary surface is organized into the same ordered levels. A surface renders the lowest levels by default and only expands deeper levels on user intent or strong relevance.

| Level | Name | Always shown? | Content |
|---|---|---|---|
| L0 | Holistic status | Yes | One plain-language line: what is the state of this concern / this person's health right now |
| L1 | Active concern | Yes | The thread or item the user is looking at: title, state, what changed |
| L2 | Next action | Yes when one exists | The single most useful next step; never more than one primary action per view |
| L3 | Timeline / evidence | On expand | Chronological events and the facts behind the summary |
| L4 | Graph / source chain | On expand | Relationship view and full provenance drill-down |
| L5 | Investigation / packet | On intent | Deeper investigation workspace or a shareable visit packet |

Rules:

- L0–L2 must be readable without scrolling on a standard mobile viewport.
- A surface must never open at L3+ by default, even when WellBe has a lot of data.
- Deeper levels are reached by an explicit affordance (expand, "Show evidence", "Explore connections", "Open investigation"), never by auto-expansion.
- Each level may itself be summarized; expanding one level must not force-expand the levels below it.

## Disclosure State Model

Each disclosable region exposes a small, predictable state contract for implementers:

```
DisclosureRegion:
  level: L0 | L1 | L2 | L3 | L4 | L5
  state: collapsed | expanded
  default_state: collapsed | expanded   # only L0–L2 may default to expanded
  has_more: boolean                      # whether a deeper level exists
  relevance: low | normal | elevated     # may surface a hint, never auto-expand
  source_access: inline | drawer | none  # how provenance is reached at this level
```

- `relevance: elevated` may add a quiet "worth a look" hint or ordering boost. It must not auto-expand or use alarm styling (see `health-adaptive-safety-language.md`).
- Expansion state is per-region and should persist within a session, not reset on every navigation.

## Provenance Requirement At Depth

Source and provenance access must be available at L3 and deeper, and must never overwhelm L0–L2.

- L0–L2: at most a compact source marker (see `evidence-ui-primitives.md`); no full evidence content inline.
- L3+: source markers resolve to the evidence drawer / source inspector.
- Any AI-derived text shown at any level must carry its review marker and a path to source, regardless of disclosure depth.

## Applying The Contract Per Surface

| Surface | L0 | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|---|
| Home | "what needs attention today" headline | active threads + open loops | primary capture / next action | open a thread's timeline | — | open packet / investigation |
| Thread Detail | thread state line | patient story + clarify strip | next action on this thread | timeline + evidence panel | thread graph preview + source inspector | prepare packet / open investigation |
| Timeline | period summary | event cards | jump to relevant event | expanded event detail | source chain per event | — |
| Graph | "explore connections" entry | scoped node set | focus a node | node/edge detail | full source drill-down | investigation landscape |
| Visit Packet | packet purpose | included sections summary | recipient + scope + expiry | section preview/edit | per-claim source | send / revoke |
| Investigation (post-MVP) | primary question | theories + open items | next investigative step | evidence for/against | source + external context | handoff / packet |

## Acceptance Criteria Mapping (WEL-140)

- Shared disclosure levels defined: L0–L5 above.
- Applied to Home, Thread Detail, Timeline, Graph, Visit Packet, and future Investigation UI: per-surface table above.
- Source/provenance access required at deeper levels without overwhelming the first view: "Provenance Requirement At Depth".
- Grounded in `ui_vision.md` and Journey Funnel: see Purpose and Grounds in.

## Implementation Notes

- Provide one shared `DisclosureRegion` primitive; do not let each screen invent its own expand/collapse behavior.
- Respect reduced motion: expansion is an instant or short (150–300ms) in-place reveal, never a large animated reflow.
- Keyboard: every expand affordance is focusable and operable; expanded content is in DOM order.
- This contract is consumed by WEL-139 (Journey Rail), WEL-145 (Home), WEL-144 (evidence access at depth), and WEL-146 (memory lanes).
