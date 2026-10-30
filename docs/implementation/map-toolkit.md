# Map toolkit: implementation and reuse

Reviewed 2026-10-29. This is an implementation guide, not a change to product meaning.

The approved Living pebble material is implemented once in `packages/ui/src/map`. The knowledge graph binds its own data, meanings and actions to that toolkit. The record context map composes the same `MapObject`, `useMapEffects` and `MapConnection`, retaining only its placement and record-walk policy. Its frame adapter supplies live scene geometry through `MapConnection.getFrame`, without duplicating the material, caption, emphasis or link paint. An optional `MapObject.hitRadius` preserves its minimum 44px target without enlarging the visible body. Both maps share size-by-weight, attached upright labels, hover/selection growth and edge glints. Record-kind colors and record-walk policy remain context-specific. Context links now use the same complete-scene route planner, peer-route costs, pastel endpoint gradients and connection layers as the graph. `useMapPan` and `useMapZoomBoundary` share background click/pan and zoom ownership, excluding hidden/inert scenes. `GraphWorkspace` hosts both retained scenes; Context map is a distinct segment in the same mode control, with matching responsive canvas proportions. Old context routes redirect into that workspace. The separate interaction-study sidebar and old orb renderer are removed. No new dependencies were introduced.

## Boundaries

| Layer | Responsibility | Main entry |
| --- | --- | --- |
| Geometry and physical state | Palette, silhouette, sizing, motion state, orbit dimensions, port sectors, routing, pointer math, collision primitives, constellation placement, shared frame scheduling | `@wellbe/ui/map/core` |
| React presentation | Surfaces, complete objects, miniatures, accents, badges, labels, group lights, elastic connections, tooltip placement, input bindings and environment hooks | `@wellbe/ui/map` |
| WellBe presentation adapter | Record/type glyphs, concern colors, relationship meanings, source identity, expansion eligibility, human-readable labels | `apps/web/components/graph/GraphObject.tsx`, `graphObjectProfiles.ts`, `graphMiniaturePresentation.tsx`, `graphAppearance.ts` |
| Scene and actions | Visible layers, selection, replay, evidence access, routing inputs, domain layout, manual positions, navigation, comparison and sharing | `GraphLive.tsx`, `GraphPanels.tsx`, `liveGraphLayout.ts`, `expandedGraphLayout.ts`, `graphDrag.ts` |
| Record walking | Accepted record associations; full map, neighbour hop, rewind, filter, stop and clear | `ContextMap.tsx`, `CosmosField.tsx` |

The toolkit imports neither application types nor routes, services or persistence. Its core entry imports no React code. A dependency-boundary test protects that separation. Some established math names retain “graph”, “bridge”, “silk” or “pebble”; none contains a health-record taxonomy or medical decision.

Keep genuinely different policies explicit. Concern-aware graph expansion and the context map's pinned record walk solve different navigation problems. Both use shared physical primitives; merging their selection state machines would change behavior.

## Element inventory

| Element | Single implementation / adapter | Preserved behavior |
| --- | --- | --- |
| Ceramic surface | `LivingPebbleSurface`, `MapSurface`, core material palette | Organic outline, pastel glaze, grain, recessed lighting, contact shadow and translucent body; glyphs/labels stay solid |
| Object composition | `MapObject`, `MapObjectFrame` | Stable identity and physical DOM contract; keyboard body emphasis, whole-body hit area, expansion state without an outer ring, labels and callbacks |
| Alternate silhouettes | `MapSurface` plus `graphObjectShape` | Pebble, diamond, dashed open loop and comparison; full and miniature objects use the same shape decision |
| Family accents | `MapAccents` plus `graphAccentProfile` | Explicit profiles for all ten graph types: ordinary records disable decorative outer rims; diamond, external, open-loop, comparison and segmented bridge metadata remain. The toolkit retains optional rim styles for other hosts |
| Metadata badges | `MapObjectBadge`, application badge descriptors | Upright pin and nonredundant clock beyond the full orbit; optional keyboard/click action and restrained glint. Semantic content and local preference persistence remain in the adapter |
| Source and concept miniatures | `MapMiniature`, `MapOrbit`, `presentGraphMiniature` | Actual type, shape, palette and glyph; invisible constant-distance rings, up to twelve items and six per ring by default |
| Source identity | `graphMiniatures.ts`, `graphSatellites.ts` | One canonical evidence list feeds orbit and inspector. Stable IDs deduplicate sources. Source miniatures remain orbiting; only related concepts expand |
| Group headings | `placeMapLabels`, `graphGroupLabels` | Mean member displacement sets preferred homes; headings yield to complete object envelopes and previously placed headings. Explicit heading dragging remains available; headings do not push map objects |
| Group illumination | `MapGroupLight`, `fitMapGroupLight`, `paintMapGroupLights` | Soft radial tint and perimeter; optional member IDs/anchor bounds fit actual bodies, text, metadata and complete orbits on the shared frame clock. App adapters own membership; shared bridges and inherited children participate. Isolated multiply blending combines overlapping backgrounds without tinting foreground content |
| Object motion | `PebbleMotion`, `useMapEffects` | Screen-size-adaptive breathing, local hover light/tilt, drift, bounded drag deformation and eased recovery; names share translation and lift while staying upright |
| Orbital and accent motion | `useMapEffects` | Slow rotations, upright miniature glyphs, bounded distance, hidden orbit tracks, local pause during drag and reduced-motion rest |
| Segmented fill and arcs | Core sector geometry and `alignSegmentedMaterial` | Segment fields face the actual rendered connection ports through hover and drag; hidden-link fallback retains every segment |
| Selected edge reflection | `MapEdgeFlow`, `MapShapeGeometry` | Shares body geometry across pebble, diamond, open-loop and comparison surfaces; a soft 12-second glint stays on the edge, pauses during drag and freezes with reduced motion. `--map-edge-flow-duration` can override its period |
| Connections | `MapConnection`, `SilkLink`, shared routing | Rim attachments, soft endpoint gradients, glow/reflection/hit area sharing one path, selected sheen, held drag corridors and elastic settling |
| Tooltip | `MapHoverTooltip`, core placement | Caller-owned content unchanged; avoids bodies, labels, metadata, complete orbital envelopes and controls; follows geometry/camera changes |
| Pointer and keyboard | `mapObjectHandlers`, core pointer math | Activate, context menu, long press, drag, click threshold, nudge, Shift nudge, Alt navigation, focus and cancellation |
| Camera boundary | `useMapZoomBoundary` | Map-only wheel, pinch and shortcut zoom; ordinary outside scrolling. Focus resolves keyboard ownership when multiple maps exist. Queued camera updates capture gesture coordinates before cleanup; release, leave, cancel and pinch cannot invalidate a pending update |
| Application controls | `GraphLive`, `GraphPanels` | Overview/detail/explore, Map/List, layers, strength, replay, Lens, comparison consent, narration, Share selection, evidence drawer, actions, hide/restore, manual links/dispute, recenter/default/reset and patient-scoped saved manual positions |

CSS that draws shared objects, connections and tooltips lives with the toolkit. Graph toolbar, inspector, layout and notices remain in `GraphLive.module.css`. Removed legacy mock styles and unused mark renderers are not alternative implementations to extend.

## Configuration

Use a stable descriptor/config object for a family; do not fork its renderer.

| Parameter | Location | Default / contract |
| --- | --- | --- |
| Base radius and weight growth | `MAP_SIZE`, `mapObjectRadius` | 14px base, 0.42px per weight unit capped at fourteen; alternate-family base 17px |
| Hover/selection emphasis | `MAP_MOTION.hoverScale`, `selectedScale`, `emphasisSettleMs`, `activeBreathFactor` | 1.12 / 1.35 body-and-glyph scale, eased over 160ms with softer breathing. Orbits widen by the added body radius while miniature sizes remain fixed. Metadata accents and badges follow the body. Names share translation and use `labelEmphasisFactor` (0.16) for a smaller size response; their weight gently strengthens. The existing layout clearance and label reservation accommodate the enlarged envelope; a soft surface glow replaces interaction rings |
| Breathing | `MAP_MOTION`, optional `useMapEffects` motion argument | 5.5 seconds; `clamp(1.6 / screenRadius, .025, .08)`; screen radius includes camera scale |
| Drift, lift, settling, deformation | `MapMotionConfig` | Existing defaults, with at most 2.4% drag stretch |
| Miniature radius, spacing and limits | `GraphOrbitConfig`, `MapObject.orbitConfig`, `MapOrbit.config` | 4.2px radius, 2.1px gap, six per ring, twelve total |
| Link tint, glow, hit width, reflection | `MapConnection.material` / `MAP_LINK` | Partial per-connection overrides; common physical defaults |
| Group lighting | `MapGroupLight` props | Center/radii fallback, color, opacity, blur, intensity and optional `layout` (member IDs, anchor bounds, padding, minimum radii and coverage). Use an isolated parent layer for background-only color mixing; fitting never affects physical node layout |
| Appearance | `MapSurfaceAppearance` | Explicit hex color, shape, surface opacity and optional segment colors/bearings |
| State | `MapVisualState` | Hot, grabbed, selected, expanded, whole-object opacity and optional emphasis |
| Accents and badges | `MapAccentProfile`, `MapBadge[]` | Presentation descriptors; action and health meanings stay outside |
| Labels | `MapObject.label` | Automatic orbit clearance, optional explicit baseline offset and secondary line gap |

The layout must use the same orbit configuration as the renderer. `graphOrbitSlots`, `graphOrbitExtent` and `graphOrbitLabelOffset` provide the shared dimensions. Keep room for the largest breathing silhouette, labels and badges. If changing the maximum breathing scale or the material's geometric envelope, update layout clearance too. Explicit label offsets remain the adapter's responsibility; the graph reserves its maximum preview envelope so names remain stable during expansion.

A miniature glyph uses a 24×24 view box. A complete object glyph is fitted into the existing 14px face slot; `MapMiniature.glyphSize` can override miniature sizing. Toolkit colors accept three- or six-digit hex. Per-object SVG paint IDs are unique, so multiple maps and repeated colors cannot steal one another's gradients.

## Reusing the same object

```tsx
import { useRef } from 'react';
import {
  MapObject, mapObjectHandlers, useMapEffects, useReducedMotion,
  type MapMiniatureItem,
} from '@wellbe/ui/map';

function Example({ open }: { open: (id: string) => void }) {
  const svg = useRef<SVGSVGElement>(null);
  const reduced = useReducedMotion();
  useMapEffects(svg, reduced, 'example-v1');
  const items: MapMiniatureItem[] = [{
    id: 'record-1', label: 'Stored document', kind: 'document',
    color: '#9780bc', shape: 'pebble',
    glyph: <svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6Z" fill="none" stroke="currentColor" /></svg>,
  }];
  return <svg ref={svg} viewBox="0 0 500 300">
    <MapObject
      objectId="example" position={{ x: 250, y: 120 }} radius={26}
      accessibleLabel="Example item"
      appearance={{ color: '#609b9a', shape: 'pebble', opacity: .9 }}
      glyph={<span>+</span>}
      accent={{ kind: 'paired', period: 72000, dash: '20 30' }}
      orbitItems={items} label={{ text: 'Example item' }}
      {...mapObjectHandlers({ activate: () => open('example') })}
    />
  </svg>;
}
```

This minimal example leaves layout, selection and dragging to its host. Supplying `mapObjectHandlers` callbacks binds those actions; the renderer does not invent them. Supply stable IDs, map positions, reduced-motion preference and a revision when changing a scene. `useMapEffects` mutates physical paint without React renders per animation frame. Objects and links subscribe to one cancellable per-SVG frame scheduler; links update before segment alignment. Unmounting removes subscribers, observers and listeners. Transient save/recenter emphasis uses owned, restartable timers.

`MapObjectFrame`, `MapSurface`, `MapObjectLabel`, `MapAccents` and `MapOrbit` are public building blocks when a host needs a different composition. Use them instead of copying `MapObject` internals. The context map's imperative SVG scene uses the same shader and core motion, routing and layout; its record controls are intentionally separate.

## Layout and route policy

The React object renderer keeps names inside the same translated object group. Captions remain upright and do not inherit body tilt or breathing deformation. Their emphasis is deliberately much smaller than the body’s, and label hit behavior stays unchanged.

The graph adapter builds one visible collision inventory: bodies, complete orbit envelopes, names, secondary labels, badges, concern headings and map controls. Expanded items are placed against that inventory. Previously clear homes and pinned/manual positions retain priority; derived collision placement is never saved as a manual move. The placement solver and family-reveal camera share a 16px top inset, allowing a short clear slide near the top edge instead of an unnecessary large sideways jump. During an active drag, `resolveMapContacts` projects local contacts from the previous positions instead of running the free-space placement search. The held object is fixed; only touching neighbours and their contact chain move. Current emphasis and orbit footprints are included. Expanded scene bounds do not imply a changed coordinate system and therefore do not reset held silk routes.

Shared routing compares radial curves and visibility detours by length, bend cost, crossing and long shared-track penalties. Haloed names may have lines behind them; bodies remain obstacles. Scene planning is separate from animation. A drag freezes corridor choice while the elastic material follows the live endpoints. It does not select a new route every frame. The optimizer is bounded and heuristic; it does not guarantee a globally shortest or crossing-free drawing for arbitrary graphs.

The core also exposes a bounded viewport constellation/walk (`fitMapConstellation`, `growViewportLook`) and a world-coordinate policy (`layoutWorldScene`, `growWorldLook`). These serve different camera constraints. Prefer the policy matching the host rather than combining them into a second renderer.

## Future context-brain integration

The current context-brain lab is a vanilla TypeScript/Vite surface. Its host can use the React-free `@wellbe/ui/map/core` geometry immediately. Reusing the exact React object/connection composition requires a React host or a deliberately designed DOM adapter. This refactor prepares that boundary; it does not port the lab or replace its navigation policy. Profile SVG/filter rendering against the lab's real scene size before replacing a large-scene renderer.

## Verification

The web unit suite covers domain adapters, canonical source miniatures, all type profiles, material math, routing, scene collision policies, persistence, record walks, accessibility and application actions. Toolkit contracts additionally cover unrelated-domain objects, configurable multi-ring label clearance, independent paint IDs, frame ordering/cleanup/error isolation, multiple-map keyboard ownership and dependency boundaries.

Browser regression suites exercise both maps at desktop and phone widths, live and sample data separation, every context-record opening, source orbit selection, concept expansion/collapse, dragged collision recovery, route quality/continuity, bridge-port alignment, hover placement, keyboard movement, breathing, accents, reduced motion and map-only wheel/touch zoom. Before/after visual captures live under `output/design/context-map-concepts/map-toolkit-audit/`.

Run from the repository root:

```sh
TZ=UTC npm run test --workspace @wellbe/web
npm run typecheck --workspace @wellbe/web
npm run typecheck --workspace @wellbe/ui
python3 scripts/check-capability-index.py
```

Use the project's map Playwright suites against a running local app for browser verification. The existing date-format assertions require UTC for the web unit run. No backend domain behavior is changed by this toolkit extraction.
