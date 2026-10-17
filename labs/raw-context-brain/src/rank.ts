import type { Rankable } from "./types.js";

/** Higher values win, in this fixed order. The lab records the order; it does not settle it. */
const RANK_KEYS = [
  "authorized",
  "provenance",
  "relevance",
  "novelty",
  "inverseDegree",
  "inverseHop",
] as const;

export function compareRank(a: Rankable, b: Rankable): number {
  for (const key of RANK_KEYS) {
    const delta = b[key] - a[key];
    if (Math.abs(delta) > 1e-9) return delta;
  }
  if (a.id === b.id) return 0;
  return a.id < b.id ? -1 : 1;
}

export function degreeNormalized(similarity: number, degree: number): number {
  return similarity / Math.log2(2 + degree);
}

export function provenanceRank(origin: "model" | "user_correction" | "policy"): number {
  if (origin === "user_correction") return 2;
  if (origin === "model") return 1;
  return 0;
}

export function applyHysteresis<T extends { id: string; relevance: number }>(
  ranked: T[],
  previousId: string | undefined,
  epsilon = 0.05,
): T[] {
  if (!previousId || ranked.length < 2) return ranked;
  const previous = ranked.find((item) => item.id === previousId);
  if (!previous) return ranked;
  const top = ranked[0];
  if (!top || top.id === previous.id) return ranked;
  if (Math.abs(top.relevance - previous.relevance) <= epsilon) {
    return [previous, ...ranked.filter((item) => item.id !== previous.id)];
  }
  return ranked;
}
