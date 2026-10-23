import { assertAdvertisementDigests, rowHash } from "./integrity/row-hash.js";
import { edgeKey, sha256 } from "./text.js";
import type {
  AcceptedEdge,
  LinkAdvertisement,
  Origin,
  PointerNode,
  VaultEvent,
} from "./types.js";

export class Vault {
  private readonly events = new Map<string, VaultEvent>();

  get size(): number {
    return this.events.size;
  }

  has(id: string): boolean {
    return this.events.has(id);
  }

  append(event: VaultEvent): void {
    if (this.events.has(event.id)) {
      throw new Error("vault is append-only");
    }
    this.events.set(event.id, Object.freeze({ ...event }));
  }

  get(id: string): VaultEvent | undefined {
    const event = this.events.get(id);
    return event ? { ...event } : undefined;
  }

  list(): VaultEvent[] {
    return [...this.events.values()].map((event) => ({ ...event }));
  }
}

export interface AdvertisementDraft {
  personId: string;
  origin: Origin;
  modelVersion: string | null;
  promptVersion: string | null;
  policyVersion: string;
  evidenceIds: string[];
  fromId: string;
  toId: string;
  judgment: LinkAdvertisement["judgment"];
  reasonCode: string;
  relation: LinkAdvertisement["relation"];
  proposedConfidence: number;
  confidence: number;
  createdAt: string;
  supersedesId: string | null;
  withdrawn: boolean;
}

export class AdvertisementLog {
  private sequence = 0;
  readonly ads: LinkAdvertisement[] = [];
  private readonly byId = new Map<string, LinkAdvertisement>();

  append(draft: AdvertisementDraft): LinkAdvertisement {
    this.sequence += 1;
    const digest = rowHash({ ...draft, sequence: this.sequence });
    const ad: LinkAdvertisement = Object.freeze({
      ...draft,
      evidenceIds: [...draft.evidenceIds],
      id: `ad-${this.sequence}`,
      sequence: this.sequence,
      digest,
    });
    this.ads.push(ad);
    this.byId.set(ad.id, ad);
    return ad;
  }

  get(id: string): LinkAdvertisement | undefined {
    return this.byId.get(id);
  }

  verifyDigests(): void {
    assertAdvertisementDigests(this.ads);
  }

  /** Replace the ledger with rows whose digests already match. Sequence continues after the last row. */
  restore(ads: readonly LinkAdvertisement[]): void {
    assertAdvertisementDigests(ads);
    this.ads.length = 0;
    this.byId.clear();
    this.sequence = 0;
    for (const ad of ads) {
      const row = Object.freeze({ ...ad, evidenceIds: [...ad.evidenceIds] });
      this.ads.push(row);
      this.byId.set(row.id, row);
      if (row.sequence > this.sequence) this.sequence = row.sequence;
    }
  }
}

function canonicalDigest(edges: Map<string, AcceptedEdge>): string {
  const lines = [...edges.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([key, edge]) => `${key}|${edge.adId}|${edge.confidence}|${edge.relation}`);
  return sha256(lines.join("\n") || "empty");
}

function dropsAcceptedEdge(ad: LinkAdvertisement): boolean {
  return ad.withdrawn || (ad.origin === "user_correction" && ad.judgment !== "link");
}

function acceptedEdge(ad: LinkAdvertisement): AcceptedEdge {
  return {
    adId: ad.id,
    fromId: ad.fromId,
    toId: ad.toId,
    confidence: ad.confidence,
    reasonCode: ad.reasonCode,
    relation: ad.relation,
    evidenceIds: [...ad.evidenceIds],
    origin: ad.origin,
  };
}

export class Projection {
  revision = 0;
  status: "ready" | "rebuilding" = "ready";
  digest = sha256("empty");
  private readonly edges = new Map<string, AcceptedEdge>();
  private readonly adjacency = new Map<string, Set<string>>();

  get edgeCount(): number {
    return this.edges.size;
  }

  accepted(): AcceptedEdge[] {
    return [...this.edges.values()].map((edge) => ({
      ...edge,
      evidenceIds: [...edge.evidenceIds],
    }));
  }

  edgeBetween(a: string, b: string): AcceptedEdge | undefined {
    const edge = this.edges.get(edgeKey(a, b));
    return edge ? { ...edge, evidenceIds: [...edge.evidenceIds] } : undefined;
  }

  neighbors(id: string): string[] {
    return [...(this.adjacency.get(id) ?? [])].sort();
  }

  degree(id: string): number {
    return this.adjacency.get(id)?.size ?? 0;
  }

  apply(ad: LinkAdvertisement): boolean {
    const key = edgeKey(ad.fromId, ad.toId);
    if (dropsAcceptedEdge(ad)) {
      if (!this.edges.has(key)) return false;
      this.edges.delete(key);
      this.unlink(ad.fromId, ad.toId);
      this.bump();
      return true;
    }
    if (ad.judgment !== "link") return false;
    const next = acceptedEdge(ad);
    const previous = this.edges.get(key);
    this.edges.set(key, next);
    this.link(ad.fromId, ad.toId);
    if (
      previous &&
      previous.adId === next.adId &&
      previous.confidence === next.confidence
    ) {
      return false;
    }
    this.bump();
    return true;
  }

  rebuild(ads: readonly LinkAdvertisement[]): void {
    assertAdvertisementDigests(ads);
    this.status = "rebuilding";
    this.edges.clear();
    this.adjacency.clear();
    for (const ad of ads) {
      const key = edgeKey(ad.fromId, ad.toId);
      if (dropsAcceptedEdge(ad)) {
        if (this.edges.has(key)) {
          this.edges.delete(key);
          this.unlink(ad.fromId, ad.toId);
        }
        continue;
      }
      if (ad.judgment !== "link") continue;
      this.edges.set(key, acceptedEdge(ad));
      this.link(ad.fromId, ad.toId);
    }
    this.digest = canonicalDigest(this.edges);
    this.revision += 1;
    this.status = "ready";
  }

  private bump(): void {
    this.revision += 1;
    this.digest = canonicalDigest(this.edges);
  }

  private link(a: string, b: string): void {
    if (!this.adjacency.has(a)) this.adjacency.set(a, new Set());
    if (!this.adjacency.has(b)) this.adjacency.set(b, new Set());
    this.adjacency.get(a)?.add(b);
    this.adjacency.get(b)?.add(a);
  }

  private unlink(a: string, b: string): void {
    this.adjacency.get(a)?.delete(b);
    this.adjacency.get(b)?.delete(a);
  }
}

export function emptyPointer(event: VaultEvent): PointerNode {
  return {
    id: event.id,
    kind: "event",
    vaultEventId: event.id,
    memberEventIds: [],
    personId: event.personId,
  };
}
