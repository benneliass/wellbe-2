# WellBe UI/UX Implementation Prompt

Use this prompt when asking a UI/UX designer, frontend developer, or product designer to implement or extend the WellBe interface. Keep this file synchronized with `docs/implementation/ui_vision.md`.

## Prompt

You are designing and implementing the WellBe product UI.

Read `docs/implementation/ui_vision.md` first. Treat it as the product-facing UI source of truth. Your job is to translate that vision into usable screens, flows, components, interaction states, and implementation-ready UI details.

WellBe is not a generic health dashboard, medical portal, EHR, or clinician command center. It is a calm personal health memory workspace for an individual managing unresolved health concerns over time. The individual is always the primary user and data controller.

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
