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

export function degreeDivisor(degree: number): number {
  return Math.log2(2 + degree);
}

export function inverseDegree(degree: number): number {
  return 1 / degreeDivisor(degree);
}

export function provenanceRank(origin: "model" | "user_correction" | "policy"): number {
  if (origin === "user_correction") return 2;
  if (origin === "model") return 1;
  return 0;
}

type Holdable = { id: string; relevance: number; authorized?: number; provenance?: number };

/** Holds the previous top note only when relevance is close and no higher key is worse. */
export function applyHysteresis<T extends Holdable>(
  ranked: T[],
  previousId: string | undefined,
  epsilon = 0.05,
): { ranked: T[]; heldPrevious: boolean } {
  if (!previousId || ranked.length < 2) return { ranked, heldPrevious: false };
  const index = ranked.findIndex((item) => item.id === previousId);
  if (index <= 0) return { ranked, heldPrevious: false };
  const previous = ranked[index];
  const top = ranked[0];
  if (!previous || !top) return { ranked, heldPrevious: false };
  if ((previous.authorized ?? 0) < (top.authorized ?? 0)) return { ranked, heldPrevious: false };
  if ((previous.provenance ?? 0) < (top.provenance ?? 0)) return { ranked, heldPrevious: false };
  if (Math.abs(top.relevance - previous.relevance) <= epsilon) {
    return {
      ranked: [previous, ...ranked.filter((item) => item.id !== previous.id)],
      heldPrevious: true,
    };
  }
  return { ranked, heldPrevious: false };
}
