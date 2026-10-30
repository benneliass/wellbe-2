# Soft sculpted porcelain — implementation review

Implemented the option C visual direction in the context map and knowledge graph. Both use the same porcelain surface primitive, association router, and persistent elastic link model. The graph retains its concern/evidence semantics, special theory/bridge/open-loop marks, inspector, layers, and navigation; context-map colors continue to mean record kind only.

The WellBe heading wordmark now uses SVG outlines traced from the generated reference, with the same all-teal treatment across navigation, launcher, sign-in, and map headings. Record symbols were redrawn to match the reference proportions and weight: blank folded paper, filled result bars, rounded note and capture-hub shapes. The decorative launcher orb is separate from the heading lockup.

## Effects

- Slight ambient record drift and slow connection flex. Each connection keeps a persistent route; a damped spring on the bend gives it inertia during movement and settling after release.
- Hover lifts only the object; its label stays anchored. Highlights and contact shadows respond locally.
- Pointer dragging pins the grabbed object and updates attached curves, without turning a drag into selection. Attachment sides stay stable during the gesture, and the graph follows the actual rendered orb position through drift and hover. Clear routes remain in place after release; blocked routes ease into a new path after settling.
- New neighbors move into available space; already placed records keep their positions.
- The latest context-map step has a restrained traveling sheen. Graph connections use the same quiet sheen family on interaction.
- Reduced motion freezes drift, lift, connection flex, and animated sheen. Dragging and choices remain available.
- A viewport-aware fallback routes around circles and labels where a single smooth curve cannot clear them.
- The first context-map frame waits for measured geometry to prevent a flash of unplaced records. Resizing resets the link springs into the new coordinate system at the same time as the circles.

## Review surfaces

- `/context`: live personal records, with automatic layout.
- `/design/context`: directly accessible, fixture-only sample constellation and the reference sheet's hover/movement details; no sign-in required.
- `/design/graph`: directly accessible, fixture-only knowledge-graph sample with the shared porcelain material; no sign-in required.

The workspace routes and their legacy preview queries still require an onboarded session. Direct design previews neither create a session nor request personal records.

The static screenshots in this directory are browser captures of the implementation, not generated replacements. The interaction-detail inset belongs only to the labeled sample preview.

## Validation

- Full frontend unit suite: **365 passed** across 51 files. Run with `TZ=UTC` because existing date-only assertions assume UTC.
- Full backend suite from the preceding implementation pass: **1,184 passed, 25 skipped** by the suite's environment checks. This visual/motion refinement changed no backend code and did not repeat that suite.
- Full browser suite: **40 passed** using local Chrome, including desktop/phone geometry audits, actual SVG curve sampling against circles and labels, hover, drift, sheen, drag/click separation, keyboard choice, filters, rewind, explicit stop, and clear.
- Workspace type checks: passed for web, mobile, UI, and API client.
- Configured web lint: passed. Workspace type checks include mobile; its code was unchanged by this refinement.
- Capability index: 35 rows validated.
- Optimized Next build: checked in an isolated source copy to avoid changing the running development server's output directory. Declaration-file emission was disabled only in that temporary copy to avoid TypeScript portability errors from its shared dependency symlink; the repository's original configuration passed workspace type checking unchanged.

## Link glitch investigation

The earlier renderer chose a fresh obstacle route on every animation frame. Small movements could switch the route side or shape. A replay in this session recorded a largest frame-to-frame interior jump of approximately 129 pixels before the fix. The final replay sampled 24,435 interior points across 182 frames: the largest movement was **7.54 pixels**, with the corresponding endpoints moving **8.00 pixels** and the route plan unchanged. This is a development-browser measurement, not a frame-rate guarantee. The final replay is saved in `link-motion-review.json`.

Regression tests cover stable held routes, movement after release, reduced motion, and resetting on resize. Desktop and phone geometry checks sample actual SVG curves against unrelated circles and labels. Fresh screenshots show both maps with no browser page errors.

The subsequent click report exposed two more problems: obstacle fallbacks had tight grid corners, and independently delayed interior points could fold backwards during a neighbour hop. The router now tries smooth radial/diagonal cubic attachments, rejects tight hairpins, sizes short handles from rim separation, and uses wider rounding for the remaining obstacle paths. The link model carries the route as one shape while applying its damped spring only to the bend. Selection does not invalidate topology.

At the 689px preview width, all ten opened records plus a three-record walk pass circle/label clearance and bend checks. A motion audit of that walk previously measured temporary turns up to 170° over a 12px thread span; the corrected three transitions measured maxima of approximately 25°, 28°, and 31°. A browser regression now samples the animation itself, in addition to the settled geometry. See `selected-record-smooth-links.png`.

Browser data checks use explicitly labeled previews or intercepted test fixtures. Backend integration checks that require unavailable services remain skipped; no deployment was performed. Existing unrelated working-tree changes were preserved, and canonical bible files were not edited.
