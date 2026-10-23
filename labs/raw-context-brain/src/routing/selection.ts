/**
 * Bounded selection for one person's ranked candidates.
 * LAB_CAP of 2 is a lab stand-in for lineage, source type, facet, and route reason.
 * These caps are not the open product parameters.
 * A referral is an id already on a neighbor list. There is no second hop.
 * The caller judges. This module only proposes the next controller-checked ids.
 * Same-person checks stay with the caller.
 */

/** Lab stand-in. Not an open product parameter. */
export const LAB_CAP = 2;

export interface NeighborRef {
  id: string;
  relevance: number;
}

export interface RankedCandidate {
  id: string;
  lineage: string;
  sourceType: string;
  facet: string;
  reason: string;
  capturedAt: string;
  relevance: number;
  neighbors: readonly NeighborRef[];
}

export interface SelectionInput {
  /** Subject time. When present, reserve at most one earlier and one later candidate. */
  capturedAt?: string;
  /** Already ranked. Earlier array position is the higher rank. */
  candidates: readonly RankedCandidate[];
}

export interface PruneRow {
  id: string;
  reason: string;
}

export interface SelectionResult {
  kept: string[];
  pruned: PruneRow[];
  referrals: string[];
}

export type LinkJudgment = "no_link" | "uncertain" | "link";

export interface JudgedCandidate {
  id: string;
  judgment: LinkJudgment;
  relevance: number;
  neighbors: readonly NeighborRef[];
}

export interface ReferralRoundInput {
  judged: readonly JudgedCandidate[];
  tried: readonly string[];
}

export interface ReferralRound {
  referrals: string[];
}

const CAPS = [
  { name: "lineage", reason: "lineage_cap" },
  { name: "sourceType", reason: "source_type_cap" },
  { name: "facet", reason: "facet_cap" },
  { name: "reason", reason: "reason_cap" },
] as const;

type CapName = (typeof CAPS)[number]["name"];

interface ReferralSource {
  relevance: number;
  neighbors: readonly NeighborRef[];
}

export function applySelection(input: SelectionInput): SelectionResult {
  const counts = emptyCounts();
  const kept = new Set<string>();
  const keptOrder: string[] = [];
  if (input.capturedAt) {
    reserve(input.candidates, input.capturedAt, "earlier", kept, keptOrder, counts);
    reserve(input.candidates, input.capturedAt, "later", kept, keptOrder, counts);
  }

  const pruned: PruneRow[] = [];
  for (const candidate of input.candidates) {
    if (kept.has(candidate.id)) continue;
    const reason = capReason(candidate, counts);
    if (reason) {
      pruned.push({ id: candidate.id, reason });
      continue;
    }
    remember(candidate, kept, keptOrder, counts);
  }

  const prunedIds = new Set(pruned.map((row) => row.id));
  const sources = input.candidates.filter((candidate) => prunedIds.has(candidate.id));
  return {
    kept: keptOrder,
    pruned,
    referrals: proposeReferrals(sources, kept),
  };
}

/**
 * After judgment. Non-link judgments may propose untried neighbors.
 * Judged ids count as tried. A link judgment proposes nothing.
 */
export function applyReferralRound(input: ReferralRoundInput): ReferralRound {
  const tried = new Set(input.tried);
  for (const item of input.judged) tried.add(item.id);
  const sources = input.judged.filter((item) => item.judgment !== "link");
  return { referrals: proposeReferrals(sources, tried) };
}

function reserve(
  candidates: readonly RankedCandidate[],
  subject: string,
  direction: "earlier" | "later",
  kept: Set<string>,
  keptOrder: string[],
  counts: Record<CapName, Map<string, number>>,
): void {
  for (const candidate of candidates) {
    if (!candidate.capturedAt) continue;
    const earlier = candidate.capturedAt < subject;
    const later = candidate.capturedAt > subject;
    if (direction === "earlier" && !earlier) continue;
    if (direction === "later" && !later) continue;
    if (kept.has(candidate.id)) return;
    if (capReason(candidate, counts)) continue;
    remember(candidate, kept, keptOrder, counts);
    return;
  }
}

function proposeReferrals(sources: readonly ReferralSource[], blocked: ReadonlySet<string>): string[] {
  const referrals: string[] = [];
  const taken = new Set(blocked);
  for (const source of sources) {
    for (const neighbor of source.neighbors) {
      if (referrals.length >= LAB_CAP) return referrals;
      if (taken.has(neighbor.id)) continue;
      if (neighbor.relevance <= source.relevance) continue;
      referrals.push(neighbor.id);
      taken.add(neighbor.id);
    }
  }
  return referrals;
}

function remember(
  candidate: RankedCandidate,
  kept: Set<string>,
  keptOrder: string[],
  counts: Record<CapName, Map<string, number>>,
): void {
  kept.add(candidate.id);
  keptOrder.push(candidate.id);
  for (const cap of CAPS) {
    const value = candidate[cap.name];
    counts[cap.name].set(value, (counts[cap.name].get(value) ?? 0) + 1);
  }
}

function capReason(candidate: RankedCandidate, counts: Record<CapName, Map<string, number>>): string | null {
  for (const cap of CAPS) {
    if ((counts[cap.name].get(candidate[cap.name]) ?? 0) >= LAB_CAP) return cap.reason;
  }
  return null;
}

function emptyCounts(): Record<CapName, Map<string, number>> {
  return {
    lineage: new Map(),
    sourceType: new Map(),
    facet: new Map(),
    reason: new Map(),
  };
}
