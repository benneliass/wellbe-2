# WellBe UI Vision

This document synthesizes WellBe's product docs, research synthesis, and current Jira roadmap into a UI direction. It is not a pixel spec. It is a product-facing design vision for how WellBe should look, feel, and organize information as the interface matures.

## Source Basis

Primary inputs:

- `docs/system-design/platform_identity.md`
- `docs/system-design/system_design.md`
- `docs/system-design/core_objects.md`
- `docs/system-design/health_thread_state_machine.md`
- `docs/system-design/knowledge_graph.md`
- `docs/safety/safety_model.md`
- `docs/feature-backlog/feature_backlog.md`
- `docs/feature-backlog/mvp_plan.md`
- `docs/workflows/patient_workflow.md`
- `docs/workflows/pre_visit_workflow.md`
- `docs/workflows/post_visit_continuity_workflow.md`
- `docs/workflows/results_and_referrals_workflow.md`
- `archive/research/product_design_synthesis/03_product_synthesis/product_principles.md`
- Jira epics, stories, tasks, and spikes in WEL through `WEL-146`, especially the product feature stories `WEL-22`-`WEL-63`, implementation stories `WEL-64`-`WEL-91`, core expansion epics `WEL-105`-`WEL-111`, and UI alignment items `WEL-139`-`WEL-146`.
- Legacy `wellbe` docs: `docs/01-company/product-principles.md`, `docs/02-product/user-journeys.md`, `docs/05-mechanisms/active-cross-reference.md`, and `docs/05-mechanisms/adaptive-explanation.md`.
- Code inventory: backend package and contract scaffolds for C1-C17, C13 render validation, and worker/service apps; current `apps/web` and `apps/mobile` are package shells, so screen sketches below are product/UI intent rather than existing frontend implementation.

The strongest recurring product idea is that WellBe is not a generic health dashboard. It is a personal continuity surface for unresolved concerns: capture what happened, connect it into a Health Thread, clarify what is known or missing, close open loops, and let the user correct the memory.

The older `wellbe` repo had three useful product principles that should be adapted into this UI vision:

- **Progress Over Pages**: the product should feel like an active investigation moving forward, not a set of disconnected pages.
- **Journey Funnel**: the product starts simple and holistic, then reveals depth as the user engages.
- **Active Cross-Reference**: users can log context without knowing where it belongs; the system surfaces possible relevance with provenance, confidence, and user control.

## UI Thesis

WellBe should feel like a calm health memory workspace, not a medical command center.

The interface should help an individual answer:

- What concern am I carrying forward?
- What changed from my normal?
- What evidence do I have?
- What is still unresolved, pending, or missing?
- What should I ask, track, share, or correct next?

The visual model should make unresolved health context easier to hold without making the user feel watched, judged, diagnosed, or alarmed. Every screen should reinforce that the user controls the data, the sharing, and the meaning of their own story.

## Design Principles

### 1. Thread-First, Not Data-First

The primary unit of UI is the Health Thread, not a document, metric, lab, chat, or visit. Home should open onto active concerns and open loops, with documents and signals appearing as supporting evidence inside a thread.

### 2. Patient Voice Has a Protected Place

The user's own words, main fear, personal theory, daily impact, and baseline change should remain visually distinct from AI summaries and clinical documents. A strong WellBe screen always lets the user see "what I said" beside "what was extracted" and "where it came from."

### 3. Continuity Is the Main Dashboard Job

The dashboard should not be a wall of vitals. It should be a short list of what needs attention:

- overdue or upcoming pending items
- referrals that are stalled or unclear
- active unresolved threads
- normal results attached to persistent symptoms
- upcoming visit prep
- correction requests or unconfirmed suggestions

### 4. Evidence Is Always Close

Trust comes from visible provenance. Facts, summaries, graph nodes, timeline events, and visit packet claims should have a compact source marker with drill-down to the raw source, confidence, timestamp, correction history, and review state.

### 5. Adaptive State Should Be Calm

Jira contains two UI directions for health-adaptive state: one ticket describes state colors including red non-dismissable banners, while a later implementation story requires a never-alarm rule with subtle token shifts and no sudden anxiety-inducing visual language. The safer synthesis is:

- use health-adaptive UI as context and prioritization, not alarm decoration
- avoid full-surface red states for routine concern levels
- reserve urgent visual treatment for Safety Gate-approved urgent guidance
- pair every state with plain language, source, confidence, and next action
- respect reduced motion and accessibility from the start

### 6. Progress Over Pages

WellBe should not feel like a collection of independent destinations: dashboard, tracker, timeline, graph, packet, and settings. It should feel like one Health Thread journey moving forward. The UI should always answer:

- what changed since the user last interacted
- what is newly connected or newly relevant
- what is still open
- what the next useful action is
- where the user is needed, if anywhere

This principle is validated by `WEL-22` (Health Thread lifecycle), `WEL-67` (pending/referral/visit lifecycle), `WEL-75` (closure-oriented notifications), and `WEL-105` (future Investigation lifecycle).

### 7. Journey Funnel

WellBe should start holistic and low-density, then expand only as the user interacts or as the thread gains meaningful context. Every major surface should default to a scannable summary, with deeper layers available through intentional expansion:

1. holistic status
2. active concern
3. next action
4. timeline/evidence
5. graph/source chain
6. investigation or shareable packet

Depth should be earned by relevance and user intent, not imposed by the amount of data WellBe has.

### 8. Active Cross-Reference With Consentful Control

Users should not have to know the correct destination for every log, document, mood entry, metric, or note. They should be able to capture context neutrally. WellBe can then surface possible links:

> "This may relate to your recurring abdominal pain thread because it happened two days before the same symptom pattern. Add it to this thread?"

These suggestions must be shown as candidates, not facts. The user can accept, reject, ignore, or defer them. Each candidate needs a short reason, source links, confidence, and the effect it would have on the thread. This maps to `WEL-36`, `WEL-53`, `WEL-60`, `WEL-87`, and `WEL-89`.

## Information Architecture

### Primary Navigation

The top-level product should stay small:

- **Home**: active threads and open loops
- **Threads**: all Health Threads, grouped by state
- **Capture**: add symptom, mood/energy, document, result, referral, medication/access clue
- **Packets**: visit packets, share links, exports
- **Memory**: full personal health memory, sources, corrections, grants

On mobile, this maps naturally to bottom navigation with no more than five destinations. On larger screens, a left sidebar can expose the same structure with thread filters and grants.

### Home Screen

Home should begin as a holistic, calm landing surface and answer "what needs my attention today?" It should have:

- a short status headline in human language
- what changed since last visit
- an active Health Threads section
- a continuity ledger section for pending results, referrals, and follow-up tasks
- a "possibly relevant" section for user-reviewable cross-reference candidates
- one primary action: add/update a Health Thread
- secondary actions for import, visit prep, and share packet

The screen should avoid presenting every metric and graph at once. Trends and graph views belong inside a thread or an investigation context.

The first screen should not assume the user wants a graph, packet, or explanation. It should show the smallest truthful view of the current journey, then let the user expand into detail.

### Health Thread Screen

The Health Thread screen is the core product surface. It should have a stable, scannable structure:

1. **Thread header**: title, state, review markers, next action, share status.
2. **Patient story card**: user's own words, baseline change, daily impact, main fear/question.
3. **Clarify strip**: known, pending, missing, unresolved, changed from baseline.
4. **Timeline**: symptoms, visits, tests, referrals, pending items, corrections.
5. **Evidence panel**: source-linked facts and documents.
6. **Graph preview**: thread-scoped evidence graph, expandable post-MVP.
7. **Actions**: update, correct, prepare visit packet, add pending item, share.

The thread should feel like a living case notebook owned by the user, not a clinician chart.

### Journey Rail

Each active thread should expose a compact journey rail. This rail is not decorative progress; it is orientation:

- **Capture**: context is being added
- **Connect**: candidate links need review
- **Clarify**: known, missing, pending, and unresolved items are being separated
- **Prepare**: a visit packet or self-review plan is ready
- **After visit**: plan, results, referrals, and corrections need capture
- **Close loops**: pending items are being tracked
- **Monitor/Reopen**: thread is resolved, monitored, or active again

The rail should highlight the current stop and the next useful action. It should not force a linear path; health threads can wait, reopen, branch, or return to earlier states.

### Capture Flow

Capture should be adaptive and short. It should ask only what is needed for the current thread and avoid turning intake into an exhausting medical form.

High-value fields:

- what is happening in the user's own words
- what changed from normal
- when it started and how it changed
- daily-life impact
- main fear or question
- prior visits, tests, referrals
- current medication or access changes
- access, language, caregiver, or cost needs

The UI should preserve raw narrative verbatim, then show structured extraction separately for confirmation.

Capture should also support neutral logging: the user can add a mood entry, document, metric, note, or symptom without choosing the exact thread. WellBe may later propose a source-linked candidate relationship, but it should not block capture on perfect categorization.

### Relevance Candidate Surface

Active cross-reference needs a dedicated UI pattern. Candidate cards should appear in Home, Thread Detail, and Capture completion states when they change the journey. Each card should include:

- possible target thread
- why it might matter
- source inputs used
- confidence level
- what would change if accepted
- actions: accept, reject, ignore for now, remind later

Candidate cards should never say "this explains" or "this caused." They should use language like "may relate," "similar timing," "same thread candidate," or "could be useful context."

### Continuity Ledger

The pending-item and referral surfaces should look more like a personal action ledger than a task manager for clinicians.

Each row should show:

- what is pending
- status
- expected date or unknown date
- owner/contact if known
- next user action
- source
- linked Health Thread

Statuses should be readable without medical jargon. Overdue items should rise in priority, but the tone should remain steady and practical.

### Visit Packet and Sharing

The visit packet should be a preview-first flow. The user chooses thread scope, time window, included sections, recipient, duration, and whether comments/export are allowed.

Default packet sections:

- key concern in the user's words
- concise timeline
- baseline change and daily impact
- pending results and referrals
- normal-test context when relevant
- open questions
- corrections or important disagreements
- source links

The packet should default to one page with drill-down available. Sharing must always look scoped, revocable, and user-approved.

## Visual Language

### Personality

WellBe should be calm, precise, humane, and evidence-aware. It should look trustworthy without borrowing the coldness of an EHR.

Recommended direction:

- minimal, content-first layouts
- generous whitespace
- rounded but not playful surfaces
- restrained cyan/teal base with green as progress/agency accent
- warm amber only for attention-needed states
- danger/red only for Safety Gate-approved urgent guidance, never as ambient decoration

Avoid:

- "AI purple" gradients
- neon health gamification
- dense clinician dashboard chrome
- alarmist banners
- diagnosis-like badges
- decorative motion
- emoji as icons

### Typography

Use a highly readable healthcare-friendly pairing:

- headings: Figtree or similar humanist geometric sans
- body: Noto Sans or similar accessible sans
- data labels: tabular figures where dates, scores, or trends align

Body text should stay at 16px or above on mobile, with line-height around 1.5-1.7. Long explanations should be narrow enough to read comfortably.

### Color and State

Use semantic tokens rather than raw per-screen colors:

- `surface.default`
- `surface.thread`
- `surface.pending`
- `surface.shared`
- `text.primary`
- `text.secondary`
- `state.stable`
- `state.watch`
- `state.needs_attention`
- `state.urgent`
- `evidence.patient_entered`
- `evidence.ai_summarized`
- `evidence.clinician_reviewed`
- `evidence.corrected`

Adaptive state should change small elements first: left rail, pill, icon, panel tint, or next-action card. Do not recolor the whole app based on health status.

### Motion

Motion should explain continuity:

- timeline entries expand in place
- graph nodes reveal source paths progressively
- capture confirmation moves from raw story to structured memory
- packet preview transitions from thread to shareable summary

Keep micro-interactions in the 150-300ms range, respect reduced motion, and never delay access to safety or next-action content.

## Screen Concepts

### 1. Personal Home

Purpose: "Here is what is open, pending, or ready."

Key modules:

- Today panel: "2 threads active, 1 result expected, 1 referral waiting"
- Active threads list with state and next action
- Open loops ledger
- Visit prep shortcut
- Recent corrections or unconfirmed links

### 2. Thread Detail

Purpose: "Here is the living memory of this concern."

Key modules:

- thread state and next action
- patient story
- baseline change
- timeline
- pending/referral cards
- evidence source drawer
- correction entry point

### 3. Clarify View

Purpose: "Separate known, unknown, pending, missing, and changing."

This can be a tab or a persistent strip inside Thread Detail. It should be the user-facing expression of WellBe's intelligence without feeling like a diagnostic conclusion.

### 4. Timeline and Evidence Graph

Purpose: "Show sequence and relationships without losing source."

MVP can emphasize timeline. Post-MVP graph view can add:

- thread-scoped graph by default
- investigation landscape for broader exploration
- comparison overlay for time periods or threads
- click-to-source for every node and edge

Graph UI should use relationship labels such as "co-occurs with", "temporally precedes", "may explain", and "contradicts" carefully. It must never imply final diagnosis.

### 5. Visit Packet Builder

Purpose: "Help me share the right context, not everything."

The builder should be a three-step flow:

1. choose thread and time window
2. review/edit packet contents
3. set recipient, permissions, and expiration

The strongest visual element should be the preview, not the settings.

### 6. Future Investigation Workspace

Purpose: "Help me evaluate an unresolved concern over time."

This should not replace the Health Thread. It layers on top:

- primary question
- theories as questions, not diagnoses
- evidence for/against
- missing data
- review cadence
- readiness for visit or handoff

The UI should show uncertainty as a first-class object, not a failure state.

## Feature Functionality Sketches

This section keeps the vision synchronized with the feature backlog, Jira, and code. It describes what each feature should feel like functionally in the product. It is not a commitment that the frontend is already implemented.

### MVP And Core Personal Workspace

**Health Thread core and lifecycle** (`WB2-F001`, `WEL-22`, `WEL-64`)

- Sketch: a thread card and detail page with title, lifecycle state, next action, source-linked evidence count, unresolved marker, and share state.
- Functionality: create, update, monitor, close, and reopen one concern over time; state changes should feel like continuity, not task completion theater.
- UI constraint: the Health Thread is the anchor for symptoms, visits, tests, referrals, theories, memory, packets, and investigations.

**Story Memory intake** (`WB2-F002`, `WEL-24`, `WEL-70`, `WEL-146`)

- Sketch: a two-lane capture and review surface: "My words" beside "WellBe extracted structure."
- Functionality: preserve the user's concern, fear, timeline, daily impact, baseline change, and question before extraction or summarization.
- UI constraint: never collapse patient voice into a clinical-looking summary without a visible path back to the original words.

**Baseline change and function impact capture** (`WB2-F003`, `WEL-32`)

- Sketch: short comparative prompts such as "normal for me" versus "what changed," with daily-life impact chips.
- Functionality: capture personal baseline, functional change, onset, and persistence so future views can show deviation from the user's own normal.
- UI constraint: baseline belongs in the thread header, story card, and timeline context rather than in a separate vitals dashboard.

**Evidence traceability layer** (`WB2-F004`, `WEL-23`, `WEL-83`, `WEL-144`)

- Sketch: source chips, confidence markers, review markers, correction markers, and an evidence drawer that opens without leaving the current task.
- Functionality: every derived claim, timeline event, graph edge, packet statement, and AI output can show source, confidence, timestamp, review state, and correction history.
- UI constraint: source access must stay one tap away on mobile.

**Health Thread timeline and evidence graph** (`WB2-F005`, `WEL-35`, `WEL-60`, `WEL-77`, `WEL-78`)

- Sketch: MVP timeline first, with a compact graph preview; post-MVP graph expands into thread-scoped and investigation-scoped relationship views.
- Functionality: sequence symptoms, visits, tests, documents, referrals, pending items, corrections, and candidate links while preserving source drill-down.
- UI constraint: graph labels must be relationship language, not diagnosis language.

**Normal-test safety net** (`WB2-F006`, `WEL-25`, `WEL-69`)

- Sketch: a normal-result card that separates "result was normal" from "thread is resolved."
- Functionality: keep persistent symptoms, missing context, pending follow-up, and return precautions visible after normal results.
- UI constraint: normal results should calm the result state, not erase the unresolved concern.

**Pending result tracker** (`WB2-F007`, `WEL-26`, `WEL-67`, `WEL-145`)

- Sketch: ledger rows with expected date, status, owner/contact, linked thread, source, and next user action.
- Functionality: track what result is pending, what date is expected or unknown, who to contact, and when follow-up is reasonable.
- UI constraint: overdue treatment should be steady and practical, not alarmist.

**Referral lifecycle tracker** (`WB2-F008`, `WEL-27`, `WEL-67`, `WEL-145`)

- Sketch: referral state timeline: requested, sent, accepted, scheduled, completed, blocked, or unknown.
- Functionality: distinguish "referral placed" from "referral completed" and keep the next phone call/document/action visible.
- UI constraint: referral tracking serves the user; it is not a clinic referral management worklist.

**Post-visit plan checker** (`WB2-F009`, `WEL-28`, `WEL-67`, `WEL-145`)

- Sketch: after-visit checklist tied to the same thread: plan, medications, tests ordered, referrals, return precautions, unanswered questions.
- Functionality: convert a visit into open loops and updates, then carry them into Home and Thread Detail.
- UI constraint: use plain language and source links for any clinician instruction or user-entered plan.

**Patient correction loop** (`WB2-F010`, `WEL-29`, `WEL-71`, `WEL-138`, `WEL-146`)

- Sketch: "Correct this" action on facts, summaries, memory entries, timeline events, and packet claims.
- Functionality: capture corrections as source-linked overlays without mutating original evidence.
- UI constraint: corrected content should be visibly marked; old and corrected meaning should remain traceable.

**Visit Packet builder** (`WB2-F011`, `WEL-30`, `WEL-68`)

- Sketch: preview-first builder with thread scope, time window, included sections, recipient, expiry, and permissions.
- Functionality: produce a concise, source-linked packet for a clinician or caregiver that the user controls.
- UI constraint: sharing must look scoped, revocable, and user-approved before and after sending.

**Scoped share link and export** (`WB2-F024`, `WEL-34`, `WEL-118`, `WEL-127`)

- Sketch: permission sheet showing exactly what is shared, who can access it, what actions are allowed, and when it expires.
- Functionality: let the user share packets, selected sources, or workspace views with scoped grants and audit visibility.
- UI constraint: workspace membership or deployment context never implies data access.

### Near-Term Personal Continuity And Capture

**Repeat-visit and persistence view** (`WB2-F012`, `WEL-44`)

- Sketch: persistence ribbon in a thread showing repeated visits, unchanged symptoms, unresolved questions, and what has not worked.
- Functionality: make repeat encounters read as one continuing concern instead of disconnected visits.
- UI constraint: emphasize continuity and preparation, not blame.

**Missing context checklist** (`WB2-F013`, `WEL-45`)

- Sketch: lightweight checklist inside Clarify: family history, prior tests, outside records, medications, access barriers, patient theory, and missing dates.
- Functionality: turn missing context into optional prompts and next actions.
- UI constraint: never block progress because the user cannot fill every medical field.

**Patient-held record import** (`WB2-F014`, `WEL-46`, `WEL-80`, `WEL-81`, `WEL-82`)

- Sketch: import tray for PDFs, photos, old records, portal exports, SMS, and notes, with processing status and extracted preview.
- Functionality: ingest records into raw context, show extraction confidence, and ask the user to confirm or correct structured facts.
- UI constraint: imported content should land as evidence first, not as unquestioned truth.

**Access and equity memory** (`WB2-F015`, `WEL-33`, `WEL-70`)

- Sketch: private context cards for language, transport, cost, disability, caregiver support, trust, geography, or access barriers.
- Functionality: carry access context into visit prep, follow-up planning, and safety guidance when relevant.
- UI constraint: treat equity context as user-owned support context, never as a label or stereotype.

**Lab trend and personal baseline explorer** (`WB2-F016`, `WEL-50`)

- Sketch: trend view that compares current values to personal baseline and source history, with plain-language "changed from your usual" markers.
- Functionality: show slow changes and personal deviations without forcing diagnostic interpretation.
- UI constraint: keep trend claims tied to source, range, date, and confidence.

**Medication and access clue capture** (`WB2-F017`, `WEL-51`)

- Sketch: quick capture module for medication changes, missed doses, affordability, stock issues, side effects, and access interruptions.
- Functionality: attach medication/access clues to relevant threads and open loops.
- UI constraint: avoid suggesting medication changes; surface context for discussion and tracking.

**Note and document delta view** (`WB2-F018`, `WEL-56`)

- Sketch: side-by-side or highlighted diff between document versions, notes, or repeated summaries.
- Functionality: reveal copied-forward text, changed plans, unresolved symptoms, or new instructions.
- UI constraint: delta views should explain what changed and why it matters, with source links.

**Deterioration check-in and escalation guidance** (`WB2-F019`, `WEL-47`, `WEL-74`)

- Sketch: calm check-in that asks what worsened, when, baseline difference, red-flag symptoms, and current access to care.
- Functionality: route concerning changes through the Safety Gate and produce plain next steps only when authorized.
- UI constraint: urgent styling requires Safety Gate-approved routing.

**Personal Responsibility Memory ledger** (`WB2-F020`, `WEL-31`, `WEL-67`, `WEL-145`)

- Sketch: "who does what next" ledger tied to pending results, referrals, visit plans, and user-owned follow-up.
- Functionality: remember owner, expected date, contact, last attempt, and next action.
- UI constraint: this is a personal continuity ledger, not a staff assignment board.

**Safe research and explanation mode** (`WB2-F021`, `WEL-48`, `WEL-116`, `WEL-117`)

- Sketch: explanation drawer with source-quality tiers, context-only labels, "not personal medical evidence" markers, and adjustable depth.
- Functionality: help users understand external evidence related to their thread without diagnosing.
- UI constraint: external evidence must stay separate from personal evidence unless explicitly linked as context.

**Personal experiment guardrails** (`WB2-F022`, `WEL-52`)

- Sketch: cautious planning card for user theories or lifestyle observations: question, planned change, risk check, duration, stop criteria, and notes.
- Functionality: structure self-observation without encouraging unsafe treatment changes.
- UI constraint: defer or gate until safety rules are explicit.

**Trend-over-noise PGHD summarizer** (`WB2-F023`, `WEL-53`, `WEL-89`, `WEL-141`, `WEL-142`)

- Sketch: summarized personal signal card showing trend, noise, baseline, source devices, confidence, and possible thread relevance.
- Functionality: turn wearable/self-tracking data into reviewable thread context or candidate links.
- UI constraint: candidate relevance must be accepted, rejected, deferred, or ignored by the user.

**Care-team comment mode** (`WB2-F025`, `WEL-57`, `WEL-118`, `WEL-120`)

- Sketch: scoped comment lane inside a shared thread or packet, clearly separate from the user's own memory.
- Functionality: allow grant-scoped contributors to comment or request correction without controlling the thread.
- UI constraint: the individual remains controller and can revoke access.

**Low-resource, CHW, and SMS access mode** (`WB2-F026`, `WEL-54`)

- Sketch: printable thread card, SMS-friendly follow-up prompts, offline-safe packet, and simple referral status codes.
- Functionality: adapt continuity workflows for low-resource settings while preserving user control.
- UI constraint: do not turn WellBe into a provider operations system.

**Bias and misattribution reflection** (`WB2-F027`, `WEL-55`)

- Sketch: optional reflection prompt around dismissed symptoms, language barriers, weight/age/gender assumptions, or mental-health attribution.
- Functionality: help the user preserve context that may affect care conversations.
- UI constraint: keep cautious and user-authored; defer until safety review defines language.

### Post-MVP, Gated, And Expansion Surfaces

**Workload-aware alert mode** (`WB2-F028`, `WEL-61`)

- Sketch: not a default WellBe surface; if ever used, it must be grant-scoped and user-benefiting.
- Functionality: defer clinician alert/worklist framing unless it directly serves the individual and passes governance review.
- UI constraint: no institution-controlled default access.

**Cross-specialty pattern map** (`WB2-F029`, `WEL-58`)

- Sketch: thread relationship map showing specialists, visits, unresolved questions, and cross-domain patterns.
- Functionality: help the user see patterns across specialty silos.
- UI constraint: use "possible relationship" and "needs review" language.

**Decision and uncertainty memory** (`WB2-F030`, `WEL-59`, `WEL-70`)

- Sketch: uncertainty panel: considered, ruled out, still open, watch conditions, reassessment triggers.
- Functionality: remember what was discussed, why it remains uncertain, and what should cause follow-up.
- UI constraint: uncertainty is an object, not a failure or diagnosis.

**Doctor discovery as pathway support** (`WB2-F031`, `WEL-62`)

- Sketch: pathway support card suggesting specialty type, prep context, and questions, not individual clinician ranking by default.
- Functionality: help users navigate referral gaps or wrong-specialty loops.
- UI constraint: keep deferred until governance and user-benefit framing are clear.

**Cross-patient comparison sandbox** (`WB2-F032`, `WEL-63`, `WEL-73`, `WEL-133`)

- Sketch: opt-in research/comparison entry point with explicit consent, cohort description, privacy explanation, and exit controls.
- Functionality: compare only when the individual actively chooses it and governance permits it.
- UI constraint: never default, never institution-enabled on behalf of users.

**Knowledge graph and visualization** (`WB2-F033`, `WEL-35`, `WEL-77`, `WEL-78`, `WEL-98`, `WEL-135`)

- Sketch: graph starts as an "Explore connections" layer from a thread; post-MVP expands to investigation landscapes and source inspectors.
- Functionality: show symptoms, facts, tests, visits, referrals, theories, evidence, and external context as source-linked nodes and edges.
- UI constraint: graph edges must not look like clinical conclusions.

**Mood and energy logging** (`WB2-F034`, `WEL-36`, `WEL-85`)

- Sketch: low-friction check-in with mood, energy, sleep/context note, optional body symptom, and "do not assign yet" capture.
- Functionality: feed longitudinal signals into threads or candidate relevance without making mood the explanation for physical symptoms.
- UI constraint: protect against dismissive framing.

**Myth Buster / personal theory evaluator** (`WB2-F035`, `WEL-38`, `WEL-87`, `WEL-114`, `WEL-115`, `WEL-129`)

- Sketch: theory card phrased as a question with evidence for, evidence against, missing data, safety level, and "not a diagnosis" marker.
- Functionality: evaluate user theories against personal data and external context through safety routing.
- UI constraint: never present theories as diagnoses or treatment instructions.

**Research Agent and external evidence lookup** (`WB2-F036`, `WEL-39`, `WEL-86`, `WEL-116`, `WEL-117`, `WEL-130`)

- Sketch: research watch panel with source-quality tiers, why relevant, context-only labels, and user-controlled explanation depth.
- Functionality: bring trusted external context into a thread or investigation without merging it into personal evidence.
- UI constraint: external evidence is educational/contextual unless explicitly and safely linked.

**Environmental context ingestion** (`WB2-F037`, `WEL-40`, `WEL-88`)

- Sketch: opt-in context layer for weather, air quality, pollen, UV, public-health events, or other environment signals.
- Functionality: show environmental context near relevant symptom timelines and candidate links.
- UI constraint: sensitive or location-heavy context requires explicit opt-in and clear privacy language.

**Cross-device intelligence and wearable integration** (`WB2-F038`, `WB2-F039`, `WEL-41`, `WEL-42`, `WEL-89`)

- Sketch: device signal panel with source device, baseline, drift, asymmetry, confidence, and linked thread candidates.
- Functionality: connect wearable/device data to personal baseline and thread context.
- UI constraint: avoid raw metric walls; summarize relevance and let users expand.

**Health-adaptive UI** (`WB2-F040`, `WEL-43`, `WEL-91`, `WEL-143`)

- Sketch: subtle state tokens on rails, pills, next-action cards, or panel tints.
- Functionality: reflect current thread state, review state, or attention-needed status without changing product identity.
- UI constraint: no broad alarm styling; urgent treatment only for Safety Gate-approved guidance.

**Medical institution integration / user-pull FHIR** (`WB2-F041`, `WEL-49`, `WEL-90`)

- Sketch: user-initiated import connector with scope preview, source label, processing status, and revoke/delete guidance.
- Functionality: let users pull their own records into the personal health memory.
- UI constraint: deferred and compliance-gated; institution does not gain default access.

**Intelligence engines core** (`WB2-F042`, `WEL-37`, `WEL-79`, `WEL-141`)

- Sketch: user-facing output appears as clarify prompts, missing-context cards, candidate links, contradictions, and trend summaries.
- Functionality: pattern, temporal, confounder, contradiction, and missing-data engines support the user's journey.
- UI constraint: engines should surface explainable candidates, not invisible conclusions.

**Live Metrics Safety Monitor** (`WB2-F043`, `WEL-109`, `WEL-121`, `WEL-132`)

- Sketch: gated monitor card that combines baseline deviation, symptom context, source device, safety threshold, and next step.
- Functionality: route concerning live metrics through Safety Gate thresholds before display or escalation.
- UI constraint: low-alarm by default; no continuous surveillance feeling.

**Clinician Case Investigation Workspace** (`WB2-F044`, `WEL-108`, `WEL-119`, `WEL-131`)

- Sketch: grant-scoped case view with thread summary, evidence board, theories, timeline, and comments.
- Functionality: let a clinician investigate with the user's scoped grant while improving the user's care preparation.
- UI constraint: clinician is a workspace participant, not data controller.

**Shared Health Thread workspace** (`WB2-F045`, `WEL-108`, `WEL-120`, `WEL-131`)

- Sketch: shared thread with participant list, grant scope, contribution permissions, comment lanes, and audit visibility.
- Functionality: support patient-controlled collaboration around one thread.
- UI constraint: sharing state must always be visible and revocable.

**Institution Continuity Intelligence** (`WB2-F046`, `WEL-110`, `WEL-122`)

- Sketch: deferred aggregate-only dashboard concept, not a patient-level default surface.
- Functionality: only consented, privacy-preserving continuity patterns if governance permits.
- UI constraint: no individual-level access by default and no institution-controlled activation.

**Research sandbox / cohort comparison** (`WB2-F047`, `WEL-111`, `WEL-123`, `WEL-133`)

- Sketch: governed opt-in workspace with protocol, cohort definition, data-use explanation, consent state, and withdrawal controls.
- Functionality: enable research/cohort comparison only under explicit consent.
- UI constraint: separate from normal Home and Thread flows.

**Full Health Context Summary** (`WB2-F048`, `WEL-113`)

- Sketch: expandable all-data summary that starts with a compact personal story, timeline, open loops, evidence, corrections, and share controls.
- Functionality: extend the visit packet into a full user-owned health context summary.
- UI constraint: default summary must remain source-linked and editable through corrections.

### Cross-Cutting UI Alignment Items

**Progress Over Pages alignment** (`WEL-139`)

- Sketch: journey rail, changed-since-last-visit module, and next-action continuity across Home and Thread Detail.
- Functionality: keep the app feeling like one journey around health threads rather than disconnected destinations.

**Progressive disclosure contract** (`WEL-140`)

- Sketch: shared disclosure levels from holistic status to evidence, graph, packet, and investigation depth.
- Functionality: reveal complexity by relevance and user intent.

**Active cross-reference candidate model and review UX** (`WEL-141`, `WEL-142`)

- Sketch: candidate card with target thread, why it may matter, sources, confidence, effect if accepted, and accept/reject/defer controls.
- Functionality: let WellBe suggest possible relevance without declaring facts.

**Evidence UI primitives** (`WEL-144`)

- Sketch: reusable source, confidence, review, correction, and evidence-drawer components across every surface.
- Functionality: make trust and provenance visible by default.

**Home continuity alignment** (`WEL-145`)

- Sketch: Home leads with active threads, open loops, what changed, and next action.
- Functionality: make the landing page holistic and continuity-oriented rather than a metric dashboard.

## Responsive Model

### Mobile

Mobile is the primary design constraint. Screens should prioritize:

- one major task per screen
- bottom navigation
- sticky next action when appropriate
- readable timeline cards
- simple capture flows
- packet preview that can be edited section by section

### Desktop and Tablet

Large screens can introduce split views:

- thread list + selected thread
- timeline + evidence drawer
- graph + source inspector
- packet preview + inclusion controls

Avoid making desktop the only place where graph or source drill-down is usable.

## Accessibility and Safety Requirements

Baseline requirements:

- WCAG 2.1 AA contrast
- visible focus states
- keyboard navigation for web
- touch targets at least 44px
- labels for all icon-only controls
- no color-only state meaning
- reduced-motion support
- Dynamic Type / text scaling support
- plain-language safety copy with next action

Safety-specific UI requirements:

- every AI-generated output shows review state
- every derived claim can open source evidence
- urgent guidance comes from Safety Gate-approved routing
- normal-test reassurance must show what remains unexplained
- user corrections are visible, not hidden
- sharing scope and expiry are visible before and after share

## Product Phasing

### MVP UI

Build first:

- Personal Home
- Health Thread Detail
- Story Memory capture
- baseline change capture
- timeline
- pending result tracker
- referral tracker
- post-visit checker
- correction loop
- visit packet builder
- scoped share/export controls

### Near-Term UI

Layer in:

- repeat-visit and persistence view
- missing context checklist
- patient-held record import
- access and equity memory
- lab trend and personal baseline explorer
- medication and access clue capture
- deterioration check-in with safety routing
- trend-over-noise PGHD summarizer
- relevance candidate review from active cross-reference
- user-controlled explanation depth and expand/collapse behavior

### Post-MVP UI

Add cautiously:

- graph visualization
- Health-adaptive UI tokens
- safe research and explanation mode
- theory evaluator
- external evidence watch
- wearable integration
- live metrics safety monitor
- clinician/shared workspaces under explicit grant
- full progressive Investigation workspace
- cross-thread journey map

### Deferred or Governance-Gated UI

Do not design as default product surfaces:

- cross-patient comparison
- institution continuity intelligence
- research sandbox
- clinician worklist/workload views

These can exist only under explicit opt-in, governance, and user benefit framing.

## Visual Metaphor

The product should feel like a map of open health threads:

- the thread is the path
- the timeline is the route already traveled
- pending items are open bridges
- evidence is the trail marker
- corrections are annotations in the user's hand
- sharing is handing someone a selected map segment, not giving them the whole atlas

This metaphor keeps the UI personal, longitudinal, source-linked, and agency-preserving.

## Open Design Questions

- Should the MVP Home lead with open loops or active Health Threads when both exist?
- How should WellBe visually distinguish "urgent guidance" from "attention needed" without creating alarm fatigue?
- What is the minimum evidence marker that remains understandable on mobile?
- Should graph visualization be hidden behind "Explore connections" until enough data exists?
- How much packet editing should be manual versus suggested by the system?
- Should visit preparation and post-visit follow-up be two separate flows or one continuous thread state transition?
- What is the right first-run landing state before the user has enough data for a meaningful Health Thread?
- When should a candidate relevance card interrupt the user versus wait quietly in a review queue?
- Should explanation depth be an explicit preference, an interaction-learned behavior, or both?

