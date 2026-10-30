# C · Living pebble — implementation review

The selected reference is [C · Living pebble](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/3d-object-options/c-living-pebble.png). Both maps now use one shared surface and pose renderer.

## Appearance and interaction

- A gently asymmetric, near-circular silhouette replaces the concentric disk treatment. Tonal layers, a hemisphere height map, diffuse/specular lighting, seeded ceramic grain, soft reflections, and two contact-shadow layers create depth.
- The context palette follows the reference's muted aqua, lavender, blue and pearl grey. Actual record kinds still determine colors; the knowledge graph retains concern colors and split colors on shared-concern nodes.
- Record glyphs have rounded, recessed outlines with a restrained light bevel. Labels stay outside the moving object.
- Resting objects breathe and turn very slightly. Hover adds lift, tilt, moving light and a separated shadow. Dragging introduces up to 2.4% directional deformation and a small lean; release eases the silhouette back.
- Reduced motion holds the complete material at rest, including its light, shape and shadow. Navigation and dragging remain available.
- The context design preview includes enlarged Rest, Hover and Drag examples using the same renderer as the map.
- Existing elastic connections, walk behavior, keyboard controls, filters and inspectors remain covered by the browser suite. Theory diamonds and open-loop marks retain their graph-specific meanings.

## Startup fixes found during review

Inherited SVG visibility could leave newly mounted artwork hidden when motion was reduced. The initial scene now uses an opacity gate until geometry is ready.

The graph also measured labels differently during server rendering and browser hydration. Static advances measured from the bundled Figtree face now give both the same layout inputs. Large maps receive additional spacing passes. The final captures report **zero browser page errors**.

## Verification

- Full frontend suite: **365 passed** in 51 files, with UTC and four workers.
- Full browser suite: **46 passed**, including six new material tests covering first paint, reduced motion, light/shadow response, label stability, directional deformation and recovery.
- Desktop and phone circle/label clearance and sampled SVG-curve checks passed, including every opened record at the narrow preview width.
- Web, mobile, UI and API-client type checks passed; configured web lint passed.
- Optimized production build passed in an isolated source copy. Declaration emission was disabled only in that temporary copy because it shares a dependency symlink; the repository configuration passed type checking unchanged.
- Capability index: 35 rows validated. Backend code was not changed by this visual refinement.

## Review images

[Context desktop](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/living-pebble-implementation/context-desktop.png) · [Context hover](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/living-pebble-implementation/context-hover.png) · [Context phone](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/living-pebble-implementation/context-phone.png)

[Graph desktop](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/living-pebble-implementation/graph-desktop.png) · [Graph hover](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/living-pebble-implementation/graph-hover.png) · [Graph phone](/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/living-pebble-implementation/graph-phone.png)

This is a scalable, live recreation of the reference. Visual comparison was manual; pixel-identical equivalence to the generated still has not been established. Object sizes, graph-specific marks and record-kind colors continue to follow the actual data.

## Rendering research

The lighting implementation follows SVG's alpha-height-map approach: [MDN: specular lighting](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/feSpecularLighting), [MDN: surface scale](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/surfaceScale). The fine material texture uses [SVG turbulence](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/feTurbulence). No generated bitmap is used as the interactive object.

## Lighter palette and breathing refinement

Following the visual review, the ceramic crown, body and underside were lightened while retaining the recessed icon contrast. Resting objects now breathe uniformly in both dimensions by ±0.75% over 8.7 seconds, with staggered phases. Dragging takes precedence, and reduced motion freezes breathing.

Concern groups use feathered radial light with a 14% center tint fading to transparency; their dotted boundaries are quieter. The six screenshots above were refreshed and report no page errors.

This refinement passed 21 distinct browser interaction/layout checks, including two new checks of the actual breathing range and uniform scale. Web type checking, web lint, the capability index and whitespace checks also passed. The full-suite results above describe the preceding implementation pass.


## Normal-zoom breathing and transparency

After checking the user's running preview, the previous motion was active but mostly subpixel on the small graph objects. The breathing is now a staggered, uniform ±3.5% cycle lasting 5.5 seconds. Concern overview pebbles use the same animation clock. The surface is 90% opaque, while icons and labels remain solid. The contact shadow follows the breathing subtly.

The browser regression now samples actual rendered silhouette widths as well as transform values, so a changing attribute alone cannot satisfy the breathing check. Drag recovery is checked independently of the resting breathing phase. Reduced motion continues to freeze the effect.

### Size-adaptive breathing

A fixed percentage still lost visibility when density or fit-to-view made the graph objects small. Both maps now derive breathing amplitude from the unanimated screen radius: `clamp(1.6 / screenRadiusPx, 0.025, 0.08)`. The 5.5-second staggered cycle, 90% surface opacity, drag behavior, and reduced-motion freeze are unchanged. The screen transform is read once per scene frame outside the animated body, so viewport resizing and graph zoom affect the equation without the breathing feeding back into its measurement. Limits preserve layout clearance. Regression coverage compares actual screen-space movement before and after zoom, plus small/large radii and extreme zoom bounds.

### Case-colored connection material

The earlier renderer kept most knowledge-graph connections gray and only added an almost invisible stroke around strong links. Ordinary graph links now carry the concern hue, with endpoint gradients across concerns. A soft colored bloom and fine white reflection give the line depth; hovering or selecting a node or link strengthens its glow. Relationship-specific colors and dashes remain intact. Every visible layer uses the same geometry, and gradient coordinates follow the moving endpoint centers. Reduced motion keeps the material visible while freezing glow and sheen. The context map retains its equal neutral full-map lines. Desktop, hover, and phone captures were refreshed.

Connection color refinement: mix endpoint hues with 45% white, reduce core weight by 10% and resting opacity by 18%, and lower the glow and moving sheen intensity. Hover and selection retain a gentle increase in emphasis.

### Object and metadata accent audit

| Object or metadata | Resting effect | Hover/focus effect |
| --- | --- | --- |
| Symptom / personal context | Slow short / broad rim reflection | Soft reflected-edge glow |
| Lab result / vital | Paired rim reflections with distinct spacing | Both reflections brighten |
| Visit / capture | Layered edge glints | Layered glints brighten |
| Theory / investigation | Shimmer inside the diamond edge; shape stays upright | Diamond-edge glow |
| External context | Slow sheen on a tilted rim | Soft rim glow |
| Open loop / comparison | Distinct dashed / dotted edge sheen | Edge brightens; open-loop clock stays upright |
| Bridge across concerns | Counter-moving arcs in the existing concern hues | Each colored arc brightens |
| Expandable object | Exact existing dot count on a shallow 48–64 second orbit | Track and dots softly illuminate |
| Expanded object | Satellite cue removed, expanded ring retained | Expanded ring softly illuminates |
| Pinned object / open-loop clock | Small badge glint without rotating its icon | Badge softly illuminates |
| Concern overview hub | Slow rim reflection around the larger pebble | Rim and material respond to hover/focus |

Accents share the existing graph clock, stay decorative and ignore pointer events. Orbit height keeps every satellite above the label over its entire circuit. Dragging pauses orbital and edge motion without resetting its phase; reduced motion freezes all accent transforms and badge glints. Classification covers all ten GraphNode types and composes with metadata, including cases hidden behind Investigation, External, Compare and expansion controls.

Validation: all 380 frontend tests pass with `TZ=UTC`; the local-time run exposes two existing date-format expectation failures in `adapters.test.ts` and `home-continuity.test.ts` (UTC midnight becomes the previous local day), outside graph changes. All eight focused graph browser checks pass, including desktop/phone orbit clearance, expansion/collapse, hidden special cases, drag pause/resume, reduced motion, selection, and link continuity. The nine existing living-pebble browser checks also pass. Typecheck, lint, capability-index validation and whitespace checks pass. Phone geometry after hydration has no overlaps or link crossings. Captures: `graph-diet-accents.png`, `graph-all-accents.png`, and `graph-accent-phone.png`.

### Popup, zoom boundary, clock and orbit refinement

- Root causes: the tooltip was positioned a fixed 16px from the record center; React's delegated wheel handler could be passive; open-loop records drew the clock twice; the shallow ellipse varied the dots' radius and crossed the material.
- The existing popup content now passes unchanged through measured placement that prefers empty map space and avoids the object's effects, labels and map controls.
- Non-passive native handlers capture wheel, ctrl-wheel/trackpad pinch, Safari gesture events, two-finger touch and browser zoom shortcuts while the graph is mounted. They zoom the map within its boundary, suppress page zoom outside it, retain ordinary outside scrolling, and clean up when leaving the graph. Browser-owned toolbar/menu zoom remains outside webpage control.
- Open-loop clock badges render only when their primary glyph is different. Pending objects retain the primary clock, dashed boundary and open-loop label.
- Satellite paths are not rendered. Dots follow a fixed-radius circle beyond the maximum breathing silhouette, with name and layout clearance reserved for the complete orbit. Shared derived satellite metadata keeps labels, route obstacles and layout boxes consistent.

Validation for this refinement: all 384 frontend tests pass with TZ=UTC. Twenty map browser regressions pass; the four final interaction-boundary checks also pass with actual ctrl-wheel and two-finger touch input. Desktop/phone popups preserve their text and avoid the hovered circle, metadata and labels. Circular orbits retain their radius and clear the material and name over the entire circuit. Typecheck, lint, capability-index and whitespace checks pass. Six captures were refreshed with no page errors.

### Settled-scene routing and readable title underlays

See [the routing audit](../routing-audit/review.md) for research, before/after measurements, screenshots and limitations. Routing now compares full curves, uses a visibility graph for difficult clearances and applies scene crossing/shared-track costs. Graph connections can sit behind halo-protected titles instead of detouring around words. The context map retains name avoidance. Route corridors remain fixed during dragging and can improve after settling.

Joint composition refinement now opens direct corridors by moving eligible peripheral triangle members outward during automatic layout, while preserving manual positions and pinned nodes. The requested Headache/Poor sleep and Dizziness/Poor sleep examples and Late caffeine placement are covered by desktop/phone browser regressions; see the routing audit for current captures and tradeoffs.
