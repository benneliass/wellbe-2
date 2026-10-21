---
name: ui-design-practice
description: Design or change WellBe screens using the product vision, @wellbe/ui, and a check of the running screen. Use when the user asks for UI, UX, a screen, a flow, a visual change, a layout or interaction edit, or implementation from Figma in apps/web, apps/mobile, or packages/ui.
---

# WellBe UI design practice

Scale the work to the task. A control, spacing, or copy fix does not need a brief or alternate concepts. A new screen or flow does.

## Before editing

1. Read the parts of `docs/implementation/ui_vision.md` that cover this surface: UI thesis, the relevant principle, Visual Language, and Accessibility and Safety.
2. Read the matching contract in `docs/implementation/ui/` when one exists (home, story lanes, evidence, journey rail, disclosure, safety language).
3. Inspect the current route, `@wellbe/ui`, and `packages/ui/src/tokens.css`. Reuse `Button`, `Card`, `StatePill`, `DisclosureRegion`, `SourceMarker`, `StoryLanes`, `JourneyRail`, and the evidence markers before adding markup.
4. For a new flow, fill `.cursor/skills/ui-design-practice/brief.md` in the reply before editing. Ask only for decisions the repo cannot answer. Do not invent interview participants or treat a simulated user as validation.

## Product constraints that bind every screen

- The Health Thread is the unit. Home shows open loops and what changed, not a vitals wall.
- The person's own words stay visually separate from extracted or summarized text (`StoryLanes`, evidence tokens).
- Every derived claim can open its source. Corrections stay visible.
- Amber is attention. Red is Safety Gate urgent guidance only. Do not recolor the whole screen from health status.
- No diagnosis badges, alarm banners, AI-purple gradients, or emoji icons.
- Summary first. Deeper layers open on purpose (`DisclosureRegion`).
- Action labels say what happens. Errors name the problem and the next step. Empty states help the person begin.

## Build

- Implement with the existing Next.js and `@wellbe/ui` patterns. A Figma file is a reference, not a reason to introduce Tailwind or another component kit.
- Cover the states the task can actually reach: loading, empty, error, success, disabled, permission, and long content.
- Motion explains a change, stays in the token motion range, and respects reduced motion. Do not delay a next action or safety content.

## Figma

When the user gives a frame link:

1. Name the target route or component.
2. Inspect the repo before fetching the frame.
3. Use the Figma design-to-code path for that node. If the frame is large, fetch smaller sections.
4. Map layers onto `@wellbe/ui` and real data. List missing states as assumptions.
5. Compare the running screen with the frame after the interaction works.

## Check the result

Web: open the screen and complete the primary task. Check a narrow and a wide layout. Exercise the states you added. Look for keyboard order, visible focus, labels on icon-only controls, and contrast against the vision bar (WCAG 2.1 AA, 44px targets). Fix material console errors and look again.

Native (`apps/mobile`, Expo): a phone-width browser does not count. Name iOS or Android, run the app, and check safe areas, keyboard avoidance, text scaling, back behavior, and 44pt targets.

Correction order: task blockers, then accessibility and interaction, then hierarchy and content, then decoration.

In the reply, state what you checked, what you could not run, and any assumption still open.
