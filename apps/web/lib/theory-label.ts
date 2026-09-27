/**
 * Theory labels are shown clean; the question framing is added once by the UI.
 * Older stored labels may still carry the frame (sometimes twice), so strip it.
 */

export const THEORY_QUESTION_FRAME = "Could my data be related to…";

const FRAME = /^(?:\s*could\s+my\s+data\s+be\s+related\s+to\b\s*:?\s*)+/i;

export function cleanTheoryLabel(label: string): string {
  const trimmed = label.trim();
  const core = trimmed.replace(FRAME, "");
  if (core === trimmed) return trimmed;
  return core.replace(/\?+$/, "").trim() || trimmed;
}
