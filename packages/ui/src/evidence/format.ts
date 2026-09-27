import type { SourceComponent } from "./types";

export const SOURCE_COMPONENT_LABEL: Record<SourceComponent, string> = {
  c2: "your record",
  c5: "from your data",
  c16: "external reference",
};

export const SOURCE_COMPONENT_ICON: Record<SourceComponent, string> = {
  c2: "file-text",
  c5: "line-chart",
  c16: "globe",
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ULID = /^[0-9A-HJKMNP-TV-Z]{26}$/;
const PREFIXED_ID = /^[a-z][a-z0-9]*_(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{8,}$/;

/** True when a string looks like a machine identifier rather than a human label. */
export function looksLikeRawId(value: string): boolean {
  const v = value.trim();
  return UUID.test(v) || ULID.test(v) || PREFIXED_ID.test(v);
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

/**
 * The label a source may show. Falls back to the plain component label when the
 * display label is blank or is actually a raw id, so ids never reach the screen.
 */
export function resolveDisplayLabel(displayLabel: string | undefined, component: SourceComponent): string {
  const label = displayLabel?.trim() ?? "";
  if (!label || looksLikeRawId(label)) return capitalize(SOURCE_COMPONENT_LABEL[component]);
  return label;
}

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export interface FormattedDate {
  iso: string;
  label: string;
}

export function formatEvidenceDate(value: string | Date | undefined): FormattedDate | null {
  if (value === undefined || value === "") return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return { iso: date.toISOString(), label: DATE_FORMAT.format(date) };
}

export function cx(...names: Array<string | false | null | undefined>): string {
  return names.filter(Boolean).join(" ");
}

/**
 * Phrasing WellBe must never render in relevance/candidate copy
 * (ui_vision_implementation_prompt.md, "Relevance Candidate Cards").
 */
export const BANNED_CANDIDATE_PHRASES: readonly RegExp[] = [
  /\bthis caused\b/i,
  /\bcaused by\b/i,
  /\bexplains?\b/i,
  /\bdiagnos(?:is|es|ed|e)\b/i,
  /\bconfirmed\b/i,
  /\byou have\b/i,
];

export function containsBannedPhrasing(text: string): boolean {
  return BANNED_CANDIDATE_PHRASES.some((re) => re.test(text));
}
