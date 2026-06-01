# Evidence UI Primitives

**Jira:** WEL-144 (E10 UI Layer / Evidence)
**Status:** Foundation spec
**Binds to:** C13 `SourceRefV2`, `RenderApprovalV2`, `C10ObligationV2`; C10 `ReviewMarker`; C5 confidence + `confidence_basis`; C11 correction overlays
**Grounds in:** `docs/implementation/ui_vision.md` (Evidence Is Always Reachable), `docs/safety/safety_model.md`

## Purpose

Define the shared, reusable UI primitives that express **source**, **confidence**, **review state**, and **correction** for any derived claim, anywhere in WellBe. Every other surface composes these; no screen invents its own evidence styling.

This guarantees the "no orphan claims" principle at the UI layer: any AI-derived statement carries a marker and a path to its evidence.

## The Primitives

### 1. SourceMarker

Compact indicator that a claim is backed by one or more sources. Resolves to the Evidence Drawer.

```
SourceMarker:
  count: integer                 # number of backing sources
  top_component: c2 | c5 | c16   # SourceRefV2.component of the strongest source
  display_label: string          # SourceRefV2.display_label (human label)
  on_activate -> open EvidenceDrawer(sourceRefs)
```

- Component → plain label: `c2` = "your record", `c5` = "from your data", `c16` = "external reference" (external evidence is visually separated from personal data).
- Renders inline at L0–L2 as a small chip; full content only in the drawer (per disclosure contract).
- Never shows a raw id; uses `display_label`. Activatable by click/tap and keyboard.

### 2. ConfidenceMeter

Expresses how strongly a claim is supported, from C5 confidence (0..1) + `confidence_basis`.

```
ConfidenceMeter:
  level: tentative | moderate | well-supported   # bucketed from 0..1
  basis: string                                   # confidence_basis, shown on expand
```

- Buckets (default): `< 0.4` tentative, `0.4–0.75` moderate, `> 0.75` well-supported. Buckets are display-only; never invent a numeric score the backend didn't provide.
- Tentative uses cautious, non-alarming language ("early signal", "not confirmed"). Never implies diagnosis.
- Confidence is shown as words + a subtle meter, never color-only.

### 3. ReviewMarker

Provenance/review badge from C10 `ReviewMarker`. Tells the user who stands behind the text.

| `ReviewMarker` value | Label | Tone |
|---|---|---|
| `patient-entered` | Your words | neutral |
| `AI-summarized` | WellBe summary | neutral, with source path |
| `not-clinician-reviewed` | Not clinician-reviewed | quiet caution, never alarm |
| `clinician-reviewed` | Clinician-reviewed | affirmative neutral |
| `clinician-annotated` | Clinician note added | affirmative neutral |
| `ready-for-visit` | Ready for visit | affirmative |
| `needs-urgent-care-consideration` | Worth urgent attention | only via C10-approved urgent guidance (see safety language spec) |

- Markers come from the `RenderApprovalV2.review_markers` accompanying the text. The client renders all markers the approval carries.
- `not-clinician-reviewed` is the honest default for AI-summarized content and must not be hidden to look more authoritative.

### 4. CorrectionMarker

Indicates a claim has a user correction overlay (C11) and links to the correction history.

```
CorrectionMarker:
  state: none | corrected | superseded
  on_activate -> open CorrectionHistory(target)
```

- `corrected`: an overlay adjusts this claim; show the corrected view with a marker that the original is preserved.
- `superseded`: the claim was replaced; original remains viewable, never deleted.
- Editing a derived claim creates a correction overlay; it never mutates the source (matches C11 non-mutating model).

### 5. EvidenceDrawer / Source Inspector

The deep surface (disclosure L3–L4) that opens from any SourceMarker.

Shows, per backing source:
- `display_label`, component (your record / from your data / external reference), and timeline date
- confidence + `confidence_basis`
- review markers
- correction history (if any)
- for `c16` external references: source-quality tier and a clear "external, not about you specifically" separation

The drawer is read-first. Any edit affordance routes to a correction (C11), and any urgent guidance shown here must be C10-approved.

## Honoring Safety Gate Obligations

When text arrives with a `RenderApprovalV2`, the client must honor its obligations before/while displaying:

| `C10ObligationV2.display_location` | UI placement |
|---|---|
| `inline` | marker/notice rendered adjacent to the claim |
| `banner` | notice rendered above the content block |
| `source_panel` | satisfied within the Evidence Drawer |

- If `blocking_if_unfulfilled` is true and the surface cannot render the obligation (missing capability), the claim must not be shown. Fall back to a safe placeholder linking to a surface that can.
- `source_display_requirements` from the approval must be satisfiable by the SourceMarker/Drawer pair; a claim requiring source display cannot render without a reachable source.
- The client treats the render approval as authoritative; it never displays AI-derived clinical text without one.

## Composition Examples

- A derived Story Memory entry: `ReviewMarker(AI-summarized)` + `SourceMarker` + optional `ConfidenceMeter` + `CorrectionMarker`.
- A pending item rationale: `SourceMarker` + `ReviewMarker(not-clinician-reviewed)`.
- A visit-packet claim: `SourceMarker` + `ReviewMarker(ready-for-visit)` + per-claim source on expand.

## Accessibility + Behavior

- All markers are non-color-only (icon + text), AA contrast, focusable, with accessible names.
- Markers are compact at shallow disclosure and expand to full detail in the drawer.
- Reduced motion: drawer opens without large animated motion.

## Acceptance Criteria Mapping (WEL-144)

- Primitives for source, confidence, review state, correction: sections 1–4.
- Reachable evidence/source path without overwhelming primary view: SourceMarker (compact) → EvidenceDrawer (deep), aligned to disclosure L3+.
- Honors Safety Gate obligations and review markers from the contract: "Honoring Safety Gate Obligations" + ReviewMarker mapping.
- No new backend; binds to existing C13/C10/C5/C11 contracts: "Binds to".

## Consumed By

WEL-146 (lane markers), WEL-145 (Home cards), WEL-139 (Journey Rail evidence access), and every screen rendering derived claims.
