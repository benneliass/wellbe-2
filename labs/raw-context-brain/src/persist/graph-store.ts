/** Durable graph snapshot. Sessions and idempotency results are not stored here. */

const UNREADABLE = "graph store snapshot is unreadable";

/** Browser storage key for the one durable snapshot. */
export const GRAPH_STORE_KEY = "wellbe.rcb.graph";

export interface DurableEvent {
  id: string;
  personId: string;
  capturedAt: string;
  sourceType: string;
  text: string;
  keyword?: string;
  contentHash: string;
  lineageId: string;
  independence?: "source_family" | "unknown";
  sourceArrival?: "typed" | "copied" | "imported";
  copiedFromId?: string | null;
  documentId: string | null;
}

/** Link-ledger row. personId is stored with the advertisement. */
export interface DurableAdvertisement {
  id: string;
  personId: string;
  sequence: number;
  origin: "model" | "user_correction" | "policy";
  digest: string;
  modelVersion: string | null;
  promptVersion: string | null;
  policyVersion: string;
  evidenceIds: string[];
  fromId: string;
  toId: string;
  judgment: "link" | "no_link" | "uncertain";
  reasonCode: string;
  relation:
    | "explicitly_linked"
    | "same_record_group"
    | "derived_or_copied"
    | "near_in_time"
    | "possible_semantic_association"
    | "possible_inconsistency";
  proposedConfidence: number;
  confidence: number;
  createdAt: string;
  supersedesId: string | null;
  withdrawn: boolean;
}

export interface DurableNode {
  id: string;
  kind: "event" | "pseudonode";
  vaultEventId: string | null;
  memberEventIds: string[];
  personId: string;
}

export interface LinkAcknowledgement {
  personId: string;
  endpointIds: [string, string];
  acknowledged: boolean;
  updatedAt: string;
}

export interface DurableSnapshot {
  events: DurableEvent[];
  advertisements: DurableAdvertisement[];
  nodes: DurableNode[];
  acknowledgements: LinkAcknowledgement[];
  /** Pinned projection counter. A restored lab keeps it so an opaque handle can resolve. */
  projectionRevision?: number;
  projectionDigest?: string;
}

export interface GraphStore {
  load(): DurableSnapshot;
  save(snapshot: DurableSnapshot): void;
}

/** Storage port. The browser passes localStorage; tests pass a Map adapter. */
export interface GraphStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function emptyDurableSnapshot(): DurableSnapshot {
  return { events: [], advertisements: [], nodes: [], acknowledgements: [] };
}

function jsonClone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function canonicalAcknowledgement(value: LinkAcknowledgement): LinkAcknowledgement {
  const personId = value?.personId;
  const acknowledged = value?.acknowledged;
  const updatedAt = value?.updatedAt;
  const ids = value?.endpointIds;
  const left = ids?.[0];
  const right = ids?.[1];
  if (
    typeof personId !== "string" ||
    typeof acknowledged !== "boolean" ||
    typeof updatedAt !== "string" ||
    !Array.isArray(ids) ||
    ids.length !== 2 ||
    typeof left !== "string" ||
    typeof right !== "string"
  ) {
    throw new Error(UNREADABLE);
  }
  return {
    personId,
    endpointIds: left <= right ? [left, right] : [right, left],
    acknowledged,
    updatedAt,
  };
}

/** Copy the four durable arrays. Acknowledgement endpoint ids are stored in canonical order. */
export function normalizeDurableSnapshot(snapshot: DurableSnapshot): DurableSnapshot {
  return {
    events: jsonClone(snapshot.events),
    advertisements: jsonClone(snapshot.advertisements),
    nodes: jsonClone(snapshot.nodes),
    acknowledgements: snapshot.acknowledgements.map(canonicalAcknowledgement),
    projectionRevision: snapshot.projectionRevision,
    projectionDigest: snapshot.projectionDigest,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseStoredSnapshot(raw: string): DurableSnapshot {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(UNREADABLE);
  }
  if (!isRecord(parsed)) throw new Error(UNREADABLE);
  const events = parsed.events;
  const advertisements = parsed.advertisements;
  const nodes = parsed.nodes;
  const acknowledgements = parsed.acknowledgements;
  if (
    !Array.isArray(events) ||
    !Array.isArray(advertisements) ||
    !Array.isArray(nodes) ||
    !Array.isArray(acknowledgements)
  ) {
    throw new Error(UNREADABLE);
  }
  return {
    events,
    advertisements,
    nodes,
    acknowledgements,
    projectionRevision: typeof parsed.projectionRevision === "number" ? parsed.projectionRevision : undefined,
    projectionDigest: typeof parsed.projectionDigest === "string" ? parsed.projectionDigest : undefined,
  };
}

export class BrowserGraphStore implements GraphStore {
  constructor(private readonly storage: GraphStorage) {}

  load(): DurableSnapshot {
    const raw = this.storage.getItem(GRAPH_STORE_KEY);
    if (raw == null || raw.trim() === "") return emptyDurableSnapshot();
    return normalizeDurableSnapshot(parseStoredSnapshot(raw));
  }

  save(snapshot: DurableSnapshot): void {
    this.storage.setItem(GRAPH_STORE_KEY, JSON.stringify(normalizeDurableSnapshot(snapshot)));
  }
}
