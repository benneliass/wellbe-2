/** Canonical hash of one complete ledger row. Excludes id and digest. */

import { sha256 } from "../text.js";
import type { LinkAdvertisement } from "../types.js";

export type RowHashInput = Omit<LinkAdvertisement, "id" | "digest">;

export function rowHash(row: RowHashInput): string {
  const canonical: RowHashInput = {
    personId: row.personId,
    sequence: row.sequence,
    origin: row.origin,
    modelVersion: row.modelVersion,
    promptVersion: row.promptVersion,
    policyVersion: row.policyVersion,
    evidenceIds: [...row.evidenceIds].sort(),
    fromId: row.fromId,
    toId: row.toId,
    judgment: row.judgment,
    reasonCode: row.reasonCode,
    relation: row.relation,
    proposedConfidence: row.proposedConfidence,
    confidence: row.confidence,
    createdAt: row.createdAt,
    supersedesId: row.supersedesId,
    withdrawn: row.withdrawn,
  };
  return sha256(JSON.stringify(canonical));
}

export function assertAdvertisementDigests(ads: readonly LinkAdvertisement[]): void {
  for (const ad of ads) {
    if (rowHash(ad) !== ad.digest) {
      throw new Error(`advertisement digest mismatch at ${ad.id}`);
    }
  }
}
