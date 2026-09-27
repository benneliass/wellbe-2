import type { Observation } from "./records-hooks";

/** "3 Jun 2026" — day-first and unambiguous; empty for unparseable input. */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** Value with its unit exactly as the source gave them, e.g. "165 mg/dL". */
export function formatReading(obs: Pick<Observation, "value" | "unit">): string {
  return obs.unit ? `${obs.value} ${obs.unit}` : obs.value;
}

/**
 * Factual comparison with the previous reading — "higher", "lower" or "the same" —
 * only when both are single numbers in the same unit. Never a judgement.
 */
export function compareWithPrevious(latest: Observation, previous: Observation): string | null {
  if (latest.numeric_value == null || previous.numeric_value == null) return null;
  if ((latest.unit ?? "") !== (previous.unit ?? "")) return null;
  const prev = `${formatReading(previous)} on ${formatDate(previous.observed_at)}`;
  if (latest.numeric_value > previous.numeric_value) return `Higher than the previous reading (${prev})`;
  if (latest.numeric_value < previous.numeric_value) return `Lower than the previous reading (${prev})`;
  return `The same as the previous reading (${prev})`;
}
