# WellBe UI/UX Implementation Prompt

Use this prompt when asking a UI/UX designer, frontend developer, or product designer to implement or extend the WellBe interface. Keep this file synchronized with `docs/implementation/ui_vision.md`.

## Prompt

You are designing and implementing the WellBe product UI.

Read `docs/implementation/ui_vision.md` first. Treat it as the product-facing UI source of truth. Your job is to translate that vision into usable screens, flows, components, interaction states, and implementation-ready UI details.

Then read the foundation specs in `docs/implementation/ui/` — they are the binding implementation contracts behind this brief: progressive disclosure levels, health-adaptive safety language (never-alarm), Story Memory display lanes, evidence UI primitives, the Progress Over Pages Journey Rail, and Home continuity. Where this brief and a foundation spec describe the same behavior, the foundation spec is authoritative.

WellBe is not a generic health dashboard, medical portal, EHR, or clinician command center. It is a calm personal health memory workspace for an individual managing unresolved health concerns over time. The individual is always the primary user and data controller.

## Shared map implementation

- Implementation contract: share the portable map toolkit in `packages/ui/src/map` through `@wellbe/ui/map` and its React-free `@wellbe/ui/map/core` entry. Object surfaces, miniatures, accents, badges, group lights, elastic connections, tooltip placement and input helpers are composed from parameterized descriptors. Keep WellBe types, colors, source identity and actions in application adapters; keep the knowledge graph’s concern expansion and the context map’s record walk distinct. One cancellable per-map frame scheduler drives physical motion. Tooltip placement follows object geometry and reserves the complete orbit. Secondary labels sit below primary names; custom orbit sizes must reserve matching layout clearance. Preserve existing interaction and reduced-motion behavior when reusing the toolkit. See `docs/implementation/map-toolkit.md` for the element inventory, configuration and integration contract.

## Core Product Feeling

The UI should feel like:

- a calm continuity workspace
- a personal health memory
- a source-linked notebook for unresolved concerns
- a progress-oriented journey across time
- a user-controlled sharing and preparation tool

The UI should not feel like:

- a hospital system
- a diagnosis engine
- a clinician worklist
- a wall of vitals
- an alarm dashboard
- a gamified health tracker
- an AI chatbot as the center of the product

## Non-Negotiable Guardrails

Every design and implementation decision must preserve these rules:

- The Health Thread is the primary UI object.
- The user controls their data, sharing, grants, corrections, and meaning.
- Patient voice must remain visually distinct from AI summaries, clinical records, and extracted structure.
- Every derived claim needs nearby evidence, source, confidence, review, or correction access.
- Safety language must be calm, plain, non-diagnostic, and never alarmist by default.
- Red or urgent visual treatment is allowed only for Safety Gate-approved urgent guidance.
- Cross-patient, institution, research, and clinician collaboration surfaces are opt-in, grant-scoped, and never default.
- Clinicians and institutions may participate only under explicit scoped grants; they are never controllers.

## Primary Navigation

Design around five primary destinations:

1. **Home**: active Health Threads, open loops, what changed, next actions.
2. **Threads**: all Health Threads grouped by state.
3. **Capture**: add symptom, story, mood/energy, document, result, referral, medication/access clue, or neutral note.
4. **Packets**: visit packets, share links, exports, and scoped grants.
5. **Memory**: Story, Clinical, Pattern, Decision, Responsibility, Equity/Access memories, sources, corrections, and grants.

On mobile, use bottom navigation with one major task per screen. On desktop/tablet, use split views where helpful: thread list plus selected thread, timeline plus evidence drawer, graph plus source inspector, packet preview plus inclusion controls.

## Core Screens To Design First

### 0. Front Door, Onboarding, and Workspace Switcher

Purpose: deliberately enter WellBe. There is **no auto-login** — an unauthenticated visitor sees a calm chooser, never a populated dashboard.

Design modules:

- front door with three honest paths: **New to WellBe** (start onboarding → fresh empty personal workspace), **Continue** (returning identity signs back in), and **choose a specific workspace** (e.g. a labelled Dev/test workspace; later grant-scoped role workspaces) — selecting a workspace is always explicit, never automatic
- first-run onboarding: personal-first welcome → minimal **core** consent (create private workspace, store/retrieve what the user adds, organise into threads, keep a private audit record) → optional, skippable baseline (name, what they hope WellBe helps with) → finalize. Resumable and idempotent; nothing beyond core consent is pre-granted (everything else is asked at point of use)
- persistent workspace switcher in the nav rail: shows the active scope, lists only the contexts the individual can act in (personal first), makes switching explicit, and is the only place to sign out. It is display-safe — membership is presence, never data access; each non-personal context shows what it does NOT imply, with a standing note that membership never means access to others' data
- no institution can enable, switch on, or reveal a workspace on the user's behalf

Design target: backend onboarding (`/v1/onboarding`) and persisted workspace enumeration (`/v2/workspaces`) exist; the real ZITADEL OIDC redirect is a later adapter swap behind the same sign-in seam.

### 1. Personal Home

Purpose: answer "what needs my attention today?"

Design modules:

- short human status headline
- what changed since last visit
- active Health Threads
- open loops ledger: pending results, referrals, post-visit tasks
- possible relevance candidates, if any
- primary action: add or update a Health Thread
- secondary actions: import, prepare visit, share packet

Do not lead with a metric dashboard. Trends, graphs, and external evidence should open from relevant threads.

### 2. Thread Detail

Purpose: show the living memory of one concern.

Design modules:

- Thread header: title, lifecycle state, review markers, next action, share status
- Journey Rail: Capture, Connect, Clarify, Prepare, After visit, Close loops, Monitor/Reopen
- Patient Story card: user's own words, main fear/question, baseline change, daily impact
- Clarify strip: known, pending, missing, unexplained, changed from baseline
- Timeline: symptoms, visits, tests, referrals, pending items, corrections
- Evidence panel/drawer: sources, confidence, review state, correction history
- Graph preview: thread-scoped "Explore connections" layer, not default density
- Actions: update, correct, prepare packet, add pending item, share

The Thread Detail screen should feel like a user-owned case notebook, not a clinician chart.

### 3. Capture Flow

Purpose: make adding context fast and non-exhausting.

Design fields:

- what is happening in the user's own words
- what changed from normal
- when it started and how it changed
- daily-life impact
- main fear or question
- prior visits, tests, referrals
- current medication/access changes
- access, language, caregiver, or cost needs

Capture must allow neutral logging. The user should not have to know the right destination before adding a note, metric, document, or symptom. Thread assignment can happen later through relevance candidates.

Always preserve raw narrative. Show extracted structure separately for confirmation.

### 4. Continuity Ledger

Purpose: remember open loops.

Rows should show:

- what is pending
- status
- expected date or unknown date
- owner/contact if known
- next user action
- source
- linked Health Thread

Use practical language. Overdue items can rise in priority, but the tone must stay steady and non-alarmist.

### 5. Visit Packet Builder

Purpose: help the user share the right context, not everything.

Use a preview-first three-step flow:

1. Choose thread and time window.
2. Review/edit packet sections.
3. Set recipient, permissions, expiry, and export/comment options.

Default packet sections:

- key concern in the user's words
- concise timeline
- baseline change and daily impact
- pending results and referrals
- normal-test context when relevant
- open questions
- corrections or disagreements
- source links

Sharing must always show scope, duration, recipient, permissions, and revocation.

### 6. Memory Hub

Purpose: browse and correct the user's health memory.

Represent memory types distinctly:

- Story Memory: what the user said and experienced
- Clinical Memory: what sources or records say
- Pattern Memory: observed patterns, trends, recurrence
- Decision Memory: what was considered, uncertain, or should trigger reassessment
- Responsibility Memory: who does what next, by when
- Equity/Access Memory: language, cost, transport, disability, caregiver, trust, and access context

Always distinguish authored memory from derived memory.

A memory names the input it came from. Result opens that result. File opens that file. Note and What you reported show the original wording on the memory, because those inputs have no separate page. From a result, the person can step to the thread and back to Memory.

### 7. Context map

Purpose: show this person's stored records and the links between them.

It is a secondary view in the knowledge graph's circle-and-link language. Use the approved C / Living pebble reference (`output/design/context-map-concepts/3d-object-options/c-living-pebble.png`): softly organic near-circular ceramic volumes with recessed kind icons, pastel kind colors, broad reflected light, soft glaze, fine grain, grounded contact shadows, readable labels, and fine curved connections on an open white surface. Both maps must use the same material and pose renderer. Use the graph’s complete shared object and connection components, not merely its shader: common radius-by-weight sizing, glyph slot, attached upright 12.5px names with a 2.5px white halo, 12% hover and 35% selection growth, matching glow and silhouette glint. The selected context record has no extra outer ring. Match canvas and inspector finish; replace the preview-only interaction-study sidebar with record details.  Present Context map as a distinctly highlighted segment inside the same Overview / Cluster detail / Explore all control, not a separate pill or page. Both views use matching responsive map proportions, whole-scene routing, peer-route crossing costs, held drag corridors, camera controls, background deselection, map-only zoom and local drag-contact collision handling. Preserve each scene’s state when switching and ignore hidden maps for gesture ownership. Legacy context URLs open this view in the graph workspace. Retain the context map’s accepted associations, fixed walk placements, neighbour hops, filters, rewind, stop and clear. Record links share the graph’s quiet stroke, pastel endpoint-kind gradients, reflection and interaction glow. The current walking step keeps its flow cue. Do not invent concern groups or source orbits when the record data does not define them. It is not the Memory hub and not the knowledge graph.

The full map opens first. Choosing a record emphasizes it and its neighbours while unrelated records fade. The chosen record stays in place; new neighbours take a short hop into open space and previously placed records stay put. Hover lifts and gently tilts the object while its label remains readable; the reflected light moves and the contact shadow separates. A uniform breathing size change over about 5.5 seconds keeps resting objects alive; stagger the phases so they do not pulse together. Adapt amplitude to the unanimated on-screen radius, including layout density, viewport size, and zoom: clamp(1.6px / screenRadius, 2.5%, 8%). Small objects get a stronger percentage so the visible movement stays comparable to larger objects, within the reserved layout clearance. Keep the ceramic palette light while retaining underside shading. Use 90% opacity on the material surface while keeping icons and labels solid. In the knowledge graph, make the soft concern-group lights readable as feathered color washes, with quiet boundaries that blend into the surface. Fit each wash to every visible member, including shared bridge objects and children inheriting their anchor’s concern. Cover rendered bodies, upright names, metadata and complete orbital envelopes on the shared material clock; refresh static coverage for reduced motion and loaded fonts. Keep coverage separate from node placement and semantic group centers. Group headings follow the mean displacement of their visible members and yield to complete object envelopes and other headings. Keep manual heading dragging available; a heading must not cover a body, name, badge or orbit. Orbit miniatures use a 4.2px radius (20% larger) and a 2.1px gap, retaining the previous total orbital footprint. Pin badges sit outside the orbital sweep and use a quiet miniature scale. A node pin is distinct from the saved camera view: pin and unpin through the badge or inspector, with device-local preferences scoped to the person and a separate sample-preview scope. Preserve the current soft palette and feathering. Blend overlapping tints with multiply inside an isolated background layer so both colors contribute while foreground objects, links and names retain their own colors. During dragging use at most 2.4% directional squash/stretch with eased recovery, staying within the reserved layout clearance. Reduced motion freezes the complete pose, including light and shadow, while preserving choices and dragging. During local dragging, the circle stays under the pointer and attached curves flex; distant records stay anchored. Keep drift subtle. Reduced motion freezes drift and hover lift. A filter stays on that record. A neighbour steps once. Stop here keeps the path and ends navigation. Clear choice returns to the full map. Drag lasts for that view only. The whole circle is the control; its label is not a click target. Offer neighbour buttons as Open plus record id, never as a clinical conclusion.

Circle color is the kind of record. Size is how many links it has. A line means the records may relate. It is not a diagnosis.

Use this same porcelain material and curved connection treatment in the knowledge graph, preserving its concern/evidence semantics, special shapes, and source inspector. Preserve relationship identity across mode and layer filters so retained connections keep their material state. A newly visible weak link may change whole-scene routing costs even when record positions stay fixed; do not reset existing connection components solely because their display index changed. Route graph connections as a settled scene: compare symmetric radial ports and all clear candidate curves by length, bends, crossings and long shared tracks. Use multi-port visibility-graph shortest paths with checked rounded corners when one cubic cannot clear the bodies. Prefer direct, visually simple corridors over fewer crossings obtained by curling around a group. During initial automatic layout, a bounded refinement may move an unpinned peripheral member of a connected triangle to its outside face, freeing straight corridors for other connections. Preserve label and badge clearance, group membership and manually positioned objects. Treat natural convergence near a shared endpoint differently from an unrelated shared track. Let graph connections pass behind record names and concern headings; protect those texts with a narrow light halo, so words stay readable without forcing U-turns. Object bodies remain routing obstacles. Cache planning outside animation frames, hold a chosen corridor throughout a drag, and only adopt a meaningfully better settled route. These are bounded routing heuristics, not a proof of a globally shortest or crossing-free drawing. Ordinary graph connections carry the shared concern color; links across concerns blend endpoint colors. Add a fine reflected highlight and faint, softly blurred pastel-colored glow, quiet at rest and brighter on hover or selection. Glow indicates interaction, not support or medical importance. Preserve relationship-specific colors and dashed styles. Anchor gradients to the moving endpoints, sharing one curve across all link layers. Reduced motion freezes glow and sheen. Keep the context map full-view connections equally quiet and neutral, as its lines only mean “may relate.” Keep notices above the map and reserve space for names, badges, and other visible text. Place source/date detail in the inspector or tooltip. Keep ordinary records and concern hubs free of decorative spinning rim arcs so source miniatures have a clear orbital corridor. Retain meaningful shape and metadata accents: a diamond-edge shimmer for theories and investigations; a tilted rim sheen for external context; distinct dashed-edge movement for open loops and comparison items; concern-colored bridge arcs with a small bounded shimmer, facing their actual connection ports; upright pin and nonredundant clock badges with soft glints. Use one miniature model and orbit renderer for actual source records and hidden related concepts. Source records stay in orbit before and after selection; selecting a parent opens its inspector without creating connected source objects. Only hidden related concepts can expand into standalone map objects. One canonical source-record list feeds the inspector and source miniatures, with stable identities and no duplicated source projection. Orbit geometry, miniature size, spacing, and preview limits come from shared parameters. Preview at most twelve actual items, with at most six per invisible constant-distance ring, over 48–64 seconds, entirely outside the largest breathing silhouette. Full source details remain available in the inspector. Reserve space below the complete orbit for the name, including while expanded. Miniatures inherit the represented item’s shape, palette, and type icon. Items without their own concern color inherit their explicit expansion anchor’s palette in both miniature and expanded form, without changing membership. Source orbit miniatures use the shared record-kind palette: teal notes/self-reports, lavender documents, blue results/wearable readings, and green references; they do not imply a source count. Source orbit miniatures use the actual source kind, including lab, wearable, note, self-report, and reference glyphs. Bridge fill sectors and arcs follow each concern’s rendered connection bearings through hover tilt and dragging; retain every concern if some links are hidden. Semantic relationship styling takes precedence over concern color, so an explicitly conflicting relationship remains dashed amber within a purple concern. Recalculate the visible layout after expansion, collapse, layer changes, and manual moves. Include expanded concepts, complete parent orbit envelopes, full labels, adornments, concern headings, and map controls in one collision inventory. Preserve the clicked record and existing clear positions; find nearby clear space for additions, move blocked neighbours during dragging, and grow the virtual canvas when needed. During dragging, warm-start a local contact solver from the previous scene, hold the grabbed object under the pointer, and pass small displacements through touching neighbours instead of searching for distant free slots. Unaffected objects and the camera stay put. Growing scene bounds must not reset held connection corridors. Gently reveal a newly opened family within the usable map area without resetting the person’s view unnecessarily. Rewrap group lights and reroute connections around the resulting concept scene. Keep derived placements separate from saved manual positions. Opening related concepts removes only their miniature previews; source miniatures remain in orbit. Expansion state remains available in the inspector and does not add an outer ring. The Observations layer controls source orbit visibility. Source-only parents offer details and evidence without an Expand on map control. Hover emphasizes graph objects with a gently eased 12% increase in the body and glyph, plus a soft color-matched glow. Selection keeps a stronger 35% increase and glow, replacing interaction halo circles and selection ripples. Names share the object’s translation and hover lift, remain upright, and gain a much smaller emphasis than the body (about 1.9% on hover and 5.6% on selection), with a slightly stronger weight. Source orbit radii widen by the body’s added radius; miniature sizes stay constant. Metadata arcs and upright badges follow the growing body. Existing layout clearance accommodates the enlargement, names reserve the complete enlarged orbit, and breathing softens while emphasized. Links follow the changing rim radius without changing corridor. Keyboard focus uses the same material emphasis. Reduced motion applies the size and glow immediately, with no animated transition, breathing or lift. These temporary interaction cues do not change the size-by-links meaning. A short, soft reflected glint travels once around the selected object’s exact silhouette over 12 seconds, following ceramic and diamond shapes rather than adding an outer ring. The edge light pauses during dragging and becomes a still glint with reduced motion. Hover and keyboard focus gently brighten these accents. Keep their shapes, meanings, counts and labels intact. Keep the hover popup content unchanged, placing it in free map space clear of the hovered object, its adornments and nearby labels. While the graph is open, page-zoom gestures and shortcuts belong to the map boundary: wheel, trackpad pinch and two-finger touch zoom the map only inside it; ordinary scrolling outside continues. Omit a clock badge if the primary symbol is already a clock. One shared material clock drives the accents; dragging pauses their local motion without changing phase, and reduced motion freezes all accents while keeping static hover emphasis. The current context-map step gets a subtle moving sheen, not a causal arrow or transmission stream. Links breathe gently and flex locally with a damped spring on their bend. Carry the curve as a complete shape with its endpoints during neighbour hops; independent delayed points must not fold back on themselves. Prefer smooth radial and diagonal attachments around obstacles, and keep short links free of elbows or hairpins. Separate path planning from animation: hold the chosen route side during a drag, preserve a clear route after release, and smoothly settle any necessary obstacle reroute. Never swap between cubic and grid routes on animation frames. Reset both circles and connections together on a viewport change. Reduced motion also freezes link flex and sheen. Use the shared all-teal outlined WellBe wordmark from the approved reference across page headers, navigation, and sign-in; do not approximate its letterforms with runtime font settings. Use the reference's fold-paper symbol, heavier note outline, filled result bars, microphone, and beveled hub tiles.

## Progressive Journey Behavior

Use "Progress Over Pages" and "Journey Funnel" everywhere.

Default views should start simple:

1. holistic status
2. active concern
3. next action
4. timeline/evidence
5. graph/source chain
6. investigation or packet depth

Reveal deeper detail only when the user expands, when relevance increases, or when the next action requires it.

The product should feel like one Health Thread journey moving forward, not disconnected pages.

## Relevance Candidate Cards

When WellBe suggests that a new log, document, metric, symptom, or note may connect to an existing thread, show it as a candidate.

Candidate cards should include:

- possible target thread
- why it might matter
- source inputs used
- confidence level
- what changes if accepted
- actions: accept, reject, ignore for now, remind later

Use language like:

- "may relate"
- "possibly connected"
- "same thread candidate"
- "similar timing"
- "could be useful context"

Do not use language like:

- "this caused"
- "this explains"
- "diagnosis"
- "confirmed"
- "you have"

## Evidence And Source UI

Create reusable primitives:

- Source chip
- Confidence marker
- Review marker
- Correction marker
- Evidence drawer
- Audit/reference marker where relevant

Every fact, summary, graph node, timeline event, packet claim, AI output, theory, and external evidence item should have a visible path to source or review context.

Mobile source access can use a bottom sheet. Desktop can use a side inspector.

## Visual Language

Use a calm, precise, humane healthcare style:

- minimal content-first layouts
- generous whitespace
- rounded but serious surfaces
- restrained cyan/teal base
- green for progress or agency
- warm amber for attention-needed states
- red only for Safety Gate-approved urgent guidance
- readable type, 16px+ body on mobile
- high contrast and visible focus states

Avoid:

- AI purple gradients
- neon health gamification
- dense EHR chrome
- alarmist banners
- diagnosis badges
- decorative motion
- emoji as primary icons

Motion should explain continuity: expanding timeline entries, revealing source paths, moving from raw capture to structured memory, previewing packet output. Respect reduced motion.

## Feature Sketches To Account For

MVP/core surfaces:

- Health Thread lifecycle
- Story Memory intake
- baseline change and function impact
- evidence traceability
- timeline
- normal-test safety net
- pending result tracker
- referral lifecycle tracker
- post-visit plan checker
- patient correction loop
- visit packet builder
- scoped share/export
- basic Memory hub
- safety-gated AI rendering

Near-term layers:

- repeat-visit and persistence view
- missing context checklist
- patient-held record import
- access and equity memory
- lab trend and personal baseline explorer
- medication/access clue capture
- note/document delta view
- deterioration check-in
- responsibility ledger
- safe research and explanation mode
- trend-over-noise PGHD summarizer
- care-team comment mode under grant
- low-resource/SMS mode where relevant
- relevance candidate review

Post-MVP and gated surfaces:

- Investigation workspace
- Theory evaluator / Myth Buster
- External Evidence Watch / Research Agent
- graph visualization
- environmental context
- wearable/cross-device intelligence
- health-adaptive UI tokens
- live metrics safety monitor
- clinician case investigation workspace
- shared Health Thread workspace
- full health context summary
- institution continuity intelligence only as aggregate, consented, deferred
- research sandbox only as explicit opt-in, governed, deferred

## Implementation Output Expected

When implementing or designing from this prompt, produce:

- screen inventory and route/component map
- key flows for Home, Thread Detail, Capture, Ledger, Packet, Memory
- component primitives for evidence, state, source, correction, grants, and candidate cards
- responsive behavior for mobile and desktop
- empty, loading, error, blocked, and permission-denied states
- accessibility notes: keyboard, focus, contrast, touch targets, text scaling, reduced motion
- safety copy rules and examples
- explicit list of what is MVP, near-term, post-MVP, deferred, or gated

If current code does not expose a frontend or API route yet, design the screen as a product target and clearly mark backend/API dependencies.

## Final Instruction

Before writing UI code or final mockups, check `docs/implementation/ui_vision.md` for the latest source of truth. If the UI vision changed, update this prompt before using it.
