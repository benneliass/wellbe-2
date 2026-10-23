/** Source-group checks for same_record_group rows. A missing policy row is not invented. */

import type { LinkAdvertisement } from "../types.js";

export function assertStructuralLedger(
  ads: readonly LinkAdvertisement[],
  nodes: readonly { id: string; kind: string; memberEventIds: readonly string[] }[],
): void {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  for (const ad of ads) {
    if (!activeSameRecord(ad)) continue;
    if (!matchesHubMembership(ad, byId)) {
      throw new Error(`structural link ${ad.id} does not match source-group membership`);
    }
  }
  for (const node of nodes) {
    if (node.kind !== "pseudonode") continue;
    for (const memberId of node.memberEventIds) {
      if (!ads.some((ad) => policyRowFor(ad, node.id, memberId))) {
        throw new Error(`structural membership ${memberId} has no policy ledger row`);
      }
    }
  }
}

function activeSameRecord(ad: LinkAdvertisement): boolean {
  return ad.relation === "same_record_group" && ad.judgment === "link" && !ad.withdrawn;
}

function matchesHubMembership(
  ad: LinkAdvertisement,
  byId: ReadonlyMap<string, { kind: string; memberEventIds: readonly string[] }>,
): boolean {
  const from = byId.get(ad.fromId);
  const to = byId.get(ad.toId);
  if (from?.kind === "pseudonode" && to?.kind !== "pseudonode") {
    return from.memberEventIds.includes(ad.toId);
  }
  if (to?.kind === "pseudonode" && from?.kind !== "pseudonode") {
    return to.memberEventIds.includes(ad.fromId);
  }
  return false;
}

function policyRowFor(ad: LinkAdvertisement, hubId: string, memberId: string): boolean {
  if (ad.origin !== "policy" || !activeSameRecord(ad)) return false;
  const other = ad.fromId === hubId ? ad.toId : ad.toId === hubId ? ad.fromId : undefined;
  return other === memberId;
}
