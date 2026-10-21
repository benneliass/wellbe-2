---
name: ui-design-review
description: Read-only WellBe UI review. Report each finding as observation, user consequence, and correction. Use when the user asks for a UX review, heuristic review, design critique, or a check of a screen before accepting it. Do not edit files.
---

# WellBe UI review

Read the brief, the screen, and `docs/implementation/ui_vision.md`. Do not edit files, do not score the work with a single number, and do not invent user-test results.

Inspect, in order: can the person finish the job, then accessibility and recovery, then hierarchy and content, then decoration.

Write each finding as:

- Observation:
- Consequence:
- Correction:

Check these WellBe failures when the surface includes them:

- Home or a thread behaves like a metrics dashboard
- The person's words and the extracted summary look the same
- A claim has no way to open its source
- Red or a full-screen tint signals ordinary concern
- Copy implies a diagnosis
- A required state is missing, or long text overflows
- The primary action is unreachable with the keyboard open, or focus is invisible

End with what is solid and what a person still needs to try on a device.
