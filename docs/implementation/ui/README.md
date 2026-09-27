# WellBe UI Foundation Specs

These documents are the implementation-ready UI contracts that sit between the product-level `docs/implementation/ui_vision.md` and actual frontend code. They define the shared rules, primitives, and layout behavior that every WellBe screen must follow.

They describe behavior, structure, states, and data bindings rather than a specific component library. The paste-ready build brief lives at `docs/implementation/ui_vision_implementation_prompt.md`.

## Status

There is a working product frontend. `apps/mobile` is still an Expo package shell.

- **`apps/web`** — Next.js 15 (App Router) workspace, deployed as the `wellbe-web` image (`apps/web/Dockerfile`, `.github/workflows/build-images.yml`). It reads the live API through `@wellbe/api-client` + TanStack Query (`apps/web/lib/hooks.ts`, `lib/records-hooks.ts`), authenticates via the dev-headers adapter or OIDC (`lib/auth-config.ts`, `lib/session.ts`), and self-hosts its fonts (`apps/web/app/fonts/`) so builds need no network.
- **`packages/ui` (`@wellbe/ui`)** — the design system: tokens (`src/tokens.css`, `src/tokens.ts`), base primitives (`src/primitives/`), calm state components (`src/components/`), and the evidence primitives from these specs (`src/evidence/`). Component tests live in `apps/web/components/__primitives__/`.

Routes (`apps/web/app/(workspace)/`): `workspace` (Home), `threads/[id]` (Thread Detail), `memory` (Memory hub), `graph`, `results`, `documents`, `appointments` (open loops), `patterns`, `prepare` (visit packets; shared view at `app/shared/[token]`), `triage` (check-in), `ask`, `delta`. Capture is a modal owned by the app shell (`components/shell/AppShell.tsx`, `components/capture/`).

## Specs and where they are implemented

| Spec | Jira | Purpose | Implemented in |
|---|---|---|---|
| [Progressive disclosure contract](./progressive-disclosure-contract.md) | WEL-140 | Shared summary-first disclosure levels for every patient-facing surface | `@wellbe/ui` `DisclosureRegion` + `DisclosureLevel` token; evidence drawer is the L3–L4 surface |
| [Health-adaptive safety language](./health-adaptive-safety-language.md) | WEL-143 | Reconciles WEL-43 vs WEL-91 into one never-alarm interpretation | `@wellbe/ui` `STATE_TOKENS` / `StatePill`; `ReviewMarker` downgrades urgent markers without Safety Gate approval; check-in copy in `components/triage/` |
| [Story Memory display lanes](./story-memory-display-lanes.md) | WEL-146 | Lanes that keep patient voice distinct from derived structure | `@wellbe/ui` `StoryLanes`; used by the Memory hub (`components/records/MemoryLive.tsx`, adapters in `memoryHub.ts`) |
| [Evidence UI primitives](./evidence-ui-primitives.md) | WEL-144 | Source, confidence, review, correction markers + evidence drawer | `@wellbe/ui` `src/evidence/` (`SourceMarker`, `ConfidenceMeter`, `ReviewMarker`, `CorrectionMarker`, `EvidenceDrawer`, `RelevanceCandidateCard`); used by the Memory hub; thread evidence uses `SourceChip` (`components/thread/EvidenceList.tsx`) |
| [Progress Over Pages / Journey Rail](./progress-over-pages-journey-rail.md) | WEL-139 | One continuous Health Thread journey across Home and Thread Detail | `@wellbe/ui` `JourneyRail` (+ `mapThreadStatusToStage`); the demo thread detail's `components/thread/StatusRail.tsx` is the earlier per-screen version — live Thread Detail (`ThreadDetailLive.tsx`) has no rail yet |
| [Home continuity alignment](./home-continuity-alignment.md) | WEL-145 | Home led by continuity, open loops, and what changed | `components/workspace/` (`WorkspaceLive`, `ThreadCard`, `OpenLoops`, `ThingsNoticed`, `SummaryStrip`) and the front door in `components/launcher/` |
| [Graph view system design](./graph-view-system-design.md) / [Graph visualization spec](./graph-visualization-spec.md) | — | Whole-person graph: scoping, layout, disclosure, motion | `apps/web/components/graph/` and the `/graph` route (`app/(workspace)/graph/`), reading `/v2/graph/threads/{id}`; sample fixtures (`graphData.ts`) are for design previews only, never a person's graph |

Where a primitive exists in `@wellbe/ui` but a screen does not use it yet, the spec is implemented at the component level and awaits adoption by that screen.

## Known contract gaps

- `MemoryEntryV2` (`/v2/threads/{id}/memories`) does not expose C8 `authorship_mode`, so the Memory hub cannot place an entry in the Voice lane from API data yet. Entries without explicit authorship render in the Derived lane (never inferred from memory type), and the hub reads `authorship_mode` as soon as the API sends it.
- Memory source refs are pointers only; the evidence drawer shows plain source kinds ("Fact from what you added", "Linked concept"), not excerpts.

## Shared grounding

All specs inherit the WellBe guardrails:

- The individual is the controller. The Health Thread is the primary UI object.
- Patient voice stays distinct from AI-summarized and clinical-source content.
- Every derived claim has a path to source, confidence, review state, and correction history.
- Safety language is calm and non-diagnostic; urgent treatment only for Safety Gate-approved guidance.
- Cross-patient, institution, and research surfaces are opt-in, grant-scoped, never default.

## Backend/contract anchors referenced by these specs

- C7 Health Thread: `HealthThreadStatus`, `/v1/threads`, `/v1/threads/{id}/transition`
- C8 Six Memories: `MemoryType`, `AuthorshipMode`, `/v2/threads/{id}/memories`
- C9 Continuity: `PendingItemType`, `PendingItemStatus`, `next_action_code`, `/v2/pending-items`
- C10 Safety Gate: `ReviewMarker`, render decisions, obligations
- C11 Correction: correction status/overlay model, `/v2/corrections`
- C13 API: `SourceRefV2`, `RenderApprovalV2`, `C10ObligationV2`
