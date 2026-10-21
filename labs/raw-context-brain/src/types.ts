/** Lab types for the Raw Context Brain theory prototype. Not a production contract. */

export type Judgment = "link" | "no_link" | "uncertain";

export type Origin = "model" | "user_correction" | "policy";

export type ControlTag =
  | "no-model"
  | "no-forward"
  | "summary-only"
  | "requires-confirmation";

export type TerminalReason =
  | "supported_leaf"
  | "approximate_frontier_exhausted"
  | "budget_exhausted"
  | "policy_blocked"
  | "authorization_changed"
  | "stale_snapshot"
  | "dependency_unavailable"
  | "insufficient_independent_evidence";

export type Exhaustion = "exact" | "approximate" | "not_yet_exhausted";

export type TopologyKind = "sparse" | "dense" | "cyclic" | "hub" | "varied";

export type Relation =
  | "explicitly_linked"
  | "same_record_group"
  | "derived_or_copied"
  | "near_in_time"
  | "possible_semantic_association"
  | "possible_inconsistency";

/** A known source family can support independence. Unknown must not. */
export type Independence = "source_family" | "unknown";

/** How this note entered the vault. Omitted on older fixtures. */
export type SourceArrival = "typed" | "copied" | "imported";

export interface VaultEvent {
  id: string;
  personId: string;
  capturedAt: string;
  sourceType: string;
  text: string;
  /** Short referral already in the note text. Omitted on a note typed in the lab. */
  keyword?: string;
  contentHash: string;
  lineageId: string;
  /** Omitted means source_family, so older fixtures keep a known family. */
  independence?: Independence;
  sourceArrival?: SourceArrival;
  /** Set when sourceArrival is copied. Does not create a link by itself. */
  copiedFromId?: string | null;
  documentId: string | null;
}

/** Pointer into the vault. Must not carry source text. */
export interface PointerNode {
  id: string;
  kind: "event" | "pseudonode";
  vaultEventId: string | null;
  memberEventIds: string[];
  personId: string;
}

export interface LinkAdvertisement {
  id: string;
  sequence: number;
  origin: Origin;
  digest: string;
  modelVersion: string | null;
  promptVersion: string | null;
  policyVersion: string;
  evidenceIds: string[];
  fromId: string;
  toId: string;
  judgment: Judgment;
  reasonCode: string;
  relation: Relation;
  proposedConfidence: number;
  confidence: number;
  createdAt: string;
  supersedesId: string | null;
  withdrawn: boolean;
}

export interface AcceptedEdge {
  adId: string;
  fromId: string;
  toId: string;
  confidence: number;
  reasonCode: string;
  relation: Relation;
  evidenceIds: string[];
  origin: Origin;
}

export interface ExportItem {
  handle: string;
  excerpt: string;
  sourceType: string;
  capturedAt: string;
  reason: string;
  requiresConfirmation: boolean;
}

export interface JudgeCandidate {
  handle: string;
  excerpt: string;
  sourceType: string;
  capturedAt: string;
}

export interface JudgeRequest {
  newHandle: string;
  excerpt: string;
  sourceType: string;
  capturedAt: string;
  candidates: JudgeCandidate[];
}

export interface JudgeDecision {
  handle: string;
  judgment: Judgment;
  reasonCode: string;
  confidence: number;
}

export interface LinkJudge {
  judge(input: JudgeRequest): Promise<JudgeDecision[]>;
}

export interface NextRoute {
  routeId: string;
  label: string;
  kind: "facet" | "temporal" | "neighbour" | "source" | "fallback";
}

export interface SemanticData {
  route: string;
  breadcrumb: string[];
  hopDepth: number;
  directLinkCount: number;
  cycleCount: number;
  exhaustion: Exhaustion;
  items: ExportItem[];
  alreadyExplored: string[];
  nextRoutes: NextRoute[];
  terminalReason: TerminalReason | null;
  detail: string;
  routeHandle: string | null;
  snapshotRevision: number;
  snapshotDigest: string;
}

export interface LocalCount {
  exploredCount: number;
  unexploredCount: number;
  reachableCount: number;
  /** Approximate when the walk was capped or seeded by the index. */
  countLabel: "exact" | "approximate";
}

export interface IngestInput {
  personId: string;
  text: string;
  sourceType: string;
  capturedAt: string;
  lineageId: string;
  independence?: "source_family" | "unknown";
  sourceArrival?: SourceArrival;
  copiedFromId?: string | null;
  idempotencyKey: string;
  documentId?: string;
}

export interface IngestResult {
  eventId: string;
  candidateCount: number;
  exportBytes: number;
  judgments: Array<{
    handle: string;
    judgment: Judgment;
    reasonCode: string;
    accepted: boolean;
  }>;
  terminalReason: TerminalReason | null;
  detail: string;
}

export interface Rankable {
  id: string;
  authorized: number;
  provenance: number;
  relevance: number;
  novelty: number;
  inverseDegree: number;
  inverseHop: number;
}

export const DETAILS = {
  authorization_changed: "authorization epoch changed; restart exploration",
  stale_snapshot: "topology snapshot changed; continuation handle is stale",
  dependency_unavailable:
    "topology is rebuilding or a dependency did not answer",
  policy_blocked: "local policy denied this route",
  budget_exhausted: "hop, size, or deadline budget is exhausted",
  supported_leaf: "accepted links from this snapshot are exhausted",
  approximate_frontier_exhausted:
    "approximate candidate frontier is exhausted; this is not proof that no related context exists",
  insufficient_independent_evidence:
    "not enough independent source evidence to add a link",
  handle_expired: "continuation handle expired",
  handle_use_limit: "continuation handle use limit reached",
  unknown_handle: "continuation handle is not recognized",
  unknown_anchor: "anchor is not in this person's map",
} as const;

export function assertSafeDetail(detail: string): void {
  if (/no relevant context/i.test(detail)) {
    throw new Error(
      "empty or failed results must not be phrased as no relevant context",
    );
  }
}
