# Story Memory Display Lanes

**Jira:** WEL-146 (E3 Memory Layer / UI)
**Status:** Foundation spec
**Binds to (read-only):** C8 `MemoryType`, `AuthorshipMode`, `MemoryLifecycleState`; `/v2/threads/{id}/memories`
**Grounds in:** `docs/implementation/ui_vision.md` (Patient Voice), `docs/decisions/six-memories-store-structure.md`

## Purpose

Define how Story Memory is displayed so the user's own words are always visually distinct from AI-extracted summaries and from clinical-source content. This protects the Patient Voice principle: WellBe structures the story, it never overwrites it.

This is a **display** spec. It does not change the C8 store, the memory schema, or any write path.

## The Authorship Lanes

Story Memory entries are presented in three visual lanes, driven by C8 `AuthorshipMode`:

| Lane | Drives from `AuthorshipMode` | Visual identity | Meaning to the user |
|---|---|---|---|
| Voice | `controller_authored`, `controller_confirmed` | Quote styling: distinct left border, the user's own typography, no AI marker | "This is what you said / confirmed." |
| Derived | `system_derived`, `hybrid` | Card styling with an AI-summarized review marker and a path to source | "WellBe summarized this from your sources." |
| Shared-in | `role_authored_pending_acceptance` | Muted card with origin label + accept/decline affordance | "Someone you granted access added this; you decide if it joins your story." |

Rules:

- Voice lane content is shown verbatim. It is never paraphrased, truncated into a summary, or restyled to look system-generated.
- `hybrid` entries render in the Derived lane but must visibly attribute the user-quoted portion (inline quote) distinct from the derived portion.
- `role_authored_pending_acceptance` never silently merges into Voice. It stays in Shared-in until the controller confirms; on confirm it transitions to `controller_confirmed` (Voice lane).
- Lane is determined only by `AuthorshipMode`, never by `MemoryType`. All six memory types can appear in any lane.

## Review + Lifecycle Markers

Each entry shows two small status signals (see `evidence-ui-primitives.md` for the marker components):

- **Review marker** (C10 `ReviewMarker`): Voice entries carry `patient-entered`; Derived entries carry `AI-summarized` and, until reviewed, `not-clinician-reviewed`.
- **Lifecycle state** (C8 `MemoryLifecycleState`): `draft` (subdued, "not yet saved to your story"), `visible` (normal), `not_current` (dimmed, "older note"), `superseded_by_correction` (struck/linked to the correction), `projection_stale` (quiet "updating" hint, never an error).

A `superseded_by_correction` entry is never deleted from view. It is shown as superseded with a link to the correction overlay (C11), preserving the audit trail and the user's original words.

## Layout

```
Story Memory (within Thread Detail, L1 of the disclosure contract)
├── Voice lane            ← user's words, quote styling, newest-relevant first
│     └── [entry] patient-entered · {timeline date}
├── Derived lane          ← WellBe's summaries
│     └── [entry] AI-summarized · not-clinician-reviewed · [source ▸]
└── Shared-in lane        ← grant-authored, pending acceptance
      └── [entry] from {role/grantee} · [Accept] [Decline] [View source]
```

- Lanes are labeled, not just color-separated (accessibility + never color-only).
- Default sort: relevance to the current thread, then recency. Respect the progressive-disclosure contract: lanes render at L1; full per-entry source/timeline opens at L3.
- When a lane is empty it is omitted, except Voice, which shows a gentle "add to your story" entry point.
- A capture/edit affordance always writes into the Voice lane as `controller_authored`.

## Cross-Lane Integrity Rules

1. No derived or shared-in content may be promoted into the Voice lane without an explicit controller confirm action.
2. Editing a derived summary creates a correction overlay (C11), it does not overwrite the user's original source-linked text.
3. The user's verbatim text remains retrievable even after corrections, summaries, or supersession.
4. Authorship and review markers travel with the entry into any other surface (timeline, packet, graph) — a quote never loses its "your words" identity when reused.

## Acceptance Criteria Mapping (WEL-146)

- Distinct display lanes for patient voice vs extracted summaries: "The Authorship Lanes".
- Driven by C8 authorship/structure without changing the store: "Binds to (read-only)" + lane mapping to `AuthorshipMode`.
- Patient voice never overwritten or hidden by AI summary: "Cross-Lane Integrity Rules" + verbatim Voice rule.
- Markers for review and lifecycle: "Review + Lifecycle Markers".

## Consumed By

WEL-144 (marker components), WEL-140 (lane depth via disclosure levels), Thread Detail screen story (downstream), Memory Hub (post-MVP).
