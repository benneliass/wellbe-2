# WellBe UI Foundation Specs

These documents are the implementation-ready UI contracts that sit between the product-level `docs/implementation/ui_vision.md` and actual frontend code. They define the shared rules, primitives, and layout behavior that every WellBe screen must follow.

They are deliberately framework-neutral. They describe behavior, structure, states, and data bindings, not a specific component library. The paste-ready build brief lives at `docs/implementation/ui_vision_implementation_prompt.md`.

## Status

There is no product frontend yet (`apps/web` and `apps/mobile` are package shells). These specs are foundation work to be consumed by the screen-building stories. Each spec names the backend/API surface it binds to and flags any surface that does not exist yet.

## Specs

| Spec | Jira | Purpose |
|---|---|---|
| [Progressive disclosure contract](./progressive-disclosure-contract.md) | WEL-140 | Shared summary-first disclosure levels for every patient-facing surface |
| [Health-adaptive safety language](./health-adaptive-safety-language.md) | WEL-143 | Reconciles WEL-43 vs WEL-91 into one never-alarm interpretation |
| [Story Memory display lanes](./story-memory-display-lanes.md) | WEL-146 | Lanes that keep patient voice distinct from derived structure |
| [Evidence UI primitives](./evidence-ui-primitives.md) | WEL-144 | Source, confidence, review, correction markers + evidence drawer |
| [Progress Over Pages / Journey Rail](./progress-over-pages-journey-rail.md) | WEL-139 | One continuous Health Thread journey across Home and Thread Detail |
| [Home continuity alignment](./home-continuity-alignment.md) | WEL-145 | Home led by continuity, open loops, and what changed |

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
