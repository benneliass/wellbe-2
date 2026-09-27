import type { components } from "@wellbe/api-client";

export type CaptureContext = components["schemas"]["CaptureContextV1"];
export type CaptureContextField = keyof CaptureContext;

/**
 * Optional follow-up prompts from the capture vision (ui_vision.md "Capture Flow").
 * Each one is asked in plain words and answered in the person's own words; none is
 * ever required. Order matches the backend's fixed narrative order.
 */
export const CONTEXT_PROMPTS: ReadonlyArray<{
  field: CaptureContextField;
  label: string;
  placeholder: string;
}> = [
  {
    field: "change_from_normal",
    label: "What's different from your normal?",
    placeholder: "e.g. I usually walk to work, now I need to stop halfway",
  },
  {
    field: "onset",
    label: "When did it start, and how has it changed?",
    placeholder: "e.g. About two weeks ago, a bit worse each morning",
  },
  {
    field: "daily_impact",
    label: "How is it affecting your day-to-day?",
    placeholder: "Sleep, work, family, getting around…",
  },
  {
    field: "main_concern",
    label: "What worries you most, or what do you want to know?",
    placeholder: "Your main question or fear, in your words",
  },
  {
    field: "prior_care",
    label: "Any visits, tests or referrals about this so far?",
    placeholder: "e.g. Saw my GP in May, blood test ordered",
  },
  {
    field: "medications_access",
    label: "Any medicine changes, or trouble getting care?",
    placeholder: "New or missed medicines, cost, language, getting appointments…",
  },
];

/** Trimmed, non-empty answers only; `undefined` when nothing was added. */
export function buildCaptureContext(
  answers: Partial<Record<CaptureContextField, string>>,
): CaptureContext | undefined {
  const context: CaptureContext = {};
  let any = false;
  for (const { field } of CONTEXT_PROMPTS) {
    const value = answers[field]?.trim();
    if (value) {
      context[field] = value;
      any = true;
    }
  }
  return any ? context : undefined;
}
