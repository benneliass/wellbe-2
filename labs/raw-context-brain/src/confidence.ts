import type { Judgment, Origin } from "./types.js";

/** Same pattern as the judge. A match is not a permitted link reason. */
const CLINICAL_REASON = /diagnos|severity|caused by|cancer|disease/i;

export interface SuggestionReading {
  kind: Judgment;
  /** False when the model abstains. An abstain adds nothing. */
  addsSuggestion: boolean;
}

/**
 * link and no_link are suggestions. uncertain abstains: it adds no suggestion
 * and it is not a no_link. Nothing here removes a kept link.
 */
export function readSuggestion(judgment: Judgment): SuggestionReading {
  if (judgment === "uncertain") {
    return { kind: "uncertain", addsSuggestion: false };
  }
  if (judgment === "no_link") {
    return { kind: "no_link", addsSuggestion: true };
  }
  return { kind: "link", addsSuggestion: true };
}

export interface NextConfidenceInput {
  origin: Origin;
  proposed: number;
  /** Null when no edge is kept yet. */
  existingConfidence: number | null;
  existingLineages: readonly string[];
  evidenceLineages: readonly string[];
}

/**
 * Model confidence cannot rise on an existing edge unless a lineage in the
 * new evidence sits outside the lineages already on that edge. A new lineage
 * may move confidence up or down. A user correction is returned as proposed.
 */
export function nextConfidence(input: NextConfidenceInput): number {
  const { origin, proposed, existingConfidence, existingLineages, evidenceLineages } = input;
  if (origin !== "model" || existingConfidence === null) return proposed;
  const known = new Set(existingLineages);
  const independent = evidenceLineages.some((lineage) => !known.has(lineage));
  if (!independent && proposed > existingConfidence) return existingConfidence;
  return proposed;
}

/** True when this reason code is clinical and not a permitted link reason. */
export function isClinicalReason(code: string): boolean {
  return CLINICAL_REASON.test(code);
}

/** Short conditional association. Not a diagnosis, cause, or severity claim. */
export function associationPhrase(): string {
  return "These notes may be associated.";
}
