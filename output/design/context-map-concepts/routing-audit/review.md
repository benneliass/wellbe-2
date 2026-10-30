# Connection routing audit

The old implementation was not choosing the shortest clean connection. It stopped at the first collision-free cubic, preferred side attachments even for vertical pairs, and planned edges independently. Its coarse-grid fallback and persistent carried paths could retain unnecessarily wide detours. It also dropped label-only obstacles in the fallback.

The final design allows connections behind titles, as requested. A narrow light halo protects record names, open-loop captions, concern headings and counts. Titles are not hard routing barriers in the knowledge graph; object bodies remain obstacles. The context map retains its own name-avoidance behavior.

## Measured results

Fixture preview, 14 visible connections, reduced motion, unchanged node positions. Lengths are in SVG graph units. Crossings are distinct edge pairs sampled from the actual SVG curves; shared-track detection checks parallel proximity beyond 24 graph units.

| Measurement | Desktop before | Desktop after | Phone before | Phone after |
| --- | ---: | ---: | ---: | ---: |
| Total connection length | 3027 | 2397 | 3300 | 2468 |
| Length saved | — | 20.8% | — | 25.2% |
| Crossing pairs | 8 | 1 | 8 | 2 |
| Long shared tracks | 0 | 0 | 4 | 0 |
| Largest length / endpoint-chord ratio | 2.008 | 1.150 | 2.657 | 1.186 |

Final routes have no measured object-body intersections. Some routes intentionally run beneath protected text. The initial audit mixed label contacts with body/focus-ring contacts; the final audit separates bodies from under-label passages. Raw evidence: [before](before.json), [after](after.json), [desktop before](before-1774.png), [desktop after](after-1774.png), [phone before](before-390.png), [phone after](after-390.png).

## Method and research

- Compare complete candidate curves and radial attachments at both ends. Score path length and curvature; reject body collisions and hairpins.
- For difficult cases, build an obstacle visibility graph with multiple source and target ports, run a shortest-path search, simplify its clear corridor and round corners only when sampled clearance remains valid.
- Optimize the settled graph in bounded passes, penalizing crossings and long near-parallel shared tracks. Prefer moderate detours rather than sending a line far around the map simply to remove one crossing.
- Keep planning separate from the existing elastic material motion. Hold routes during dragging. Revisit a settled route when positions or the scene proposal change.

Graphviz documents [visibility-based shortest-path spline routing](https://graphviz.org/Misc/spline-o-matic/) and explicitly distinguishes individual obstacle avoidance from global crossing prevention. The [yFiles routing guide](https://docs.yworks.com/yfiles-html/dguide/polyline_router/) describes separate costs for route situations and restrictions that discourage turning back. [libavoid](https://www.adaptagrams.org/documentation/classAvoid_1_1Router.html) likewise starts with shortest paths and exposes aesthetic penalties. These informed the custom TypeScript implementation; no external routing library was added.

The result is not a proof of the mathematical global optimum. Circle boundaries and candidate ports are approximated, crossing optimization is bounded, and a short fixed-position drawing can retain crossings. The measured remaining one/two crossing pairs are reported rather than claimed to be impossible.

## Validation

The full frontend run passes 390 tests in 55 files with TZ=UTC. A further regression verifies that a better scene proposal is adopted even without moving its endpoints; the final targeted routing/material run passes 12 tests. All 33 browser checks pass across context-map walking, desktop/phone geometry, metadata effects, tooltips, map-only zoom, motion/reduced motion, drag continuity and route quality. Six final route-quality/graph checks pass after the cache refinement. Typecheck, lint, capability-index and whitespace checks pass. The user's already-open preview was also inspected after hot reload: 12 of its 14 connections measured approximately straight; the remaining two were about 1.08 and 1.15 times their endpoint chord.

## Joint composition refinement

The route-only audit above held every object fixed. The next refinement addresses the user's desired arrangement: open a direct corridor by moving a peripheral object, rather than preserving a position that forces neighbouring links to curl.

The initial automatic layout now evaluates peripheral members of connected triangles when their body or an incident edge blocks another direct corridor. It considers positions on the outward face, scoring corridor clearance, straight-edge crossings, angular separation, total connection distance and movement from the prior layout. Label/body collisions, bounds and group identity remain protected. Its provisional legacy curves can be rerouted together with the position; an obsolete bend must not veto an otherwise clearer arrangement. This bounded step excludes pinned nodes and central bridges. Saved/manual positions still override automatic placement. No record names or ids are used by this refinement.

The scene router also discounts natural convergence close to a shared endpoint. A new coordinated proposal is authoritative after settling, so an individual link cannot reject it by applying a different local crossing score. Held gestures still retain their corridor.

### Requested examples

- Desktop Headache–Poor sleep now goes below Screen time on a direct route (length/chord ratio about 1.000).
- Late caffeine is below the Morning fatigue–Poor sleep line on both desktop and phone.
- Dizziness–Poor sleep is direct on both desktop and phone (about 1.000).

| Measurement | Desktop route-only | Desktop composed | Phone route-only | Phone composed |
| --- | ---: | ---: | ---: | ---: |
| Total connection length | 2397 | 2292 | 2468 | 2338 |
| Largest length/chord ratio | 1.150 | 1.006 | 1.186 | 1.037 |
| Crossing pairs | 1 | 2 | 2 | 2 |
| Object-body intersections / long shared tracks | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

This deliberately accepts an additional desktop crossing where avoiding it sent a route around the wrong side of the group. The user's priority is a clear arrangement with direct links, not an isolated crossing-count minimum. Evidence: [composed measurements](composed.json), [desktop](composed-1774.png), [phone](composed-390.png). Browser regressions assert the named corridor, relative placement and directness in addition to generic clearance and motion checks.

Joint-refinement validation: all 392 frontend tests pass with TZ=UTC; all 35 browser checks pass, including both named-corridor regressions at desktop and phone widths. Typecheck, lint, capability-index and whitespace validation pass. Inspection of the already-open user preview confirms Late caffeine at the lower position and the Headache–Poor sleep / Dizziness–Poor sleep length-to-chord ratios at approximately 1.000.
