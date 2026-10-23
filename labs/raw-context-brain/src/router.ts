import { assertStructuralLedger } from "./integrity/structural.js";
import { heuristicJudge, sanitizeDecision } from "./judge.js";
import { MemorySessionStore, type SessionJson, type SessionStore } from "./persist/session-store.js";
import type { DurableSnapshot, GraphStore, LinkAcknowledgement } from "./persist/graph-store.js";
import { applyHysteresis, compareRank, inverseDegree, provenanceRank } from "./rank.js";
import { mapRelation, sourceName } from "./relation.js";
import { createPendingInterestTable, type PendingInterestTable, type SemanticInterest } from "./routing/interest.js";
import { createRouteSets, type DiscoverySource, type RouteProvenance, type RouteSetLog } from "./routing/route-sets.js";
import { scheduleAttempt } from "./routing/retry.js";
import { applyReferralRound, applySelection, LAB_CAP, type RankedCandidate } from "./routing/selection.js";
import { forwardItems as forwardFromTip, retainsSession, selectIssuedActions, truncatePath } from "./routing/session-policy.js";
import { AdvertisementLog, Projection, Vault, emptyPointer, type AdvertisementDraft } from "./store.js";
import { HnswIndex } from "./hnsw.js";
import { edgeKey, jaccard, sha256, tokenVector, tokenize } from "./text.js";
import {
  DETAILS,
  assertSafeDetail,
  type ControlTag,
  type Exhaustion,
  type ExportItem,
  type IngestInput,
  type IngestResult,
  type JudgeDecision,
  type JudgeRequest,
  type LinkAdvertisement,
  type LinkJudge,
  type LocalCount,
  type NextRoute,
  type PointerNode,
  type Rankable,
  type Relation,
  type SemanticData,
  type TerminalReason,
  type VaultEvent,
} from "./types.js";

/** 128 bits. The prefix is not entropy. The walk stays in the server record this id names. */
function routeToken(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let hex = "";
  for (const byte of bytes) hex += byte.toString(16).padStart(2, "0");
  return `rh_${hex}`;
}

interface FrontierItem {
  nodeId: string;
  fromId: string;
  edgeKey: string;
  reason: string;
  rank: Rankable;
}

interface HandleRecord {
  token: string;
  personId: string;
  session: "exploration";
  purpose: string;
  authorizationEpoch: number;
  snapshotRevision: number;
  snapshotDigest: string;
  frontier: FrontierItem[];
  visitedNodes: string[];
  visitedEdges: string[];
  breadcrumb: string[];
  hopDepth: number;
  cycleCount: number;
  expansions: number;
  anchorId: string;
  approximateSeed: boolean;
  expiresAt: number;
  useCount: number;
  maxUses: number;
  routeBindings: Map<string, string[]>;
  advertised: LocalRoute[];
  lineagePruned: boolean;
  invalidated: boolean;
  invalidReason: TerminalReason | null;
}

export interface LabOptions {
  judge?: LinkJudge;
  seed?: number;
  pageSize?: number;
  maxCandidates?: number;
  hopLimit?: number;
  frontierCap?: number;
  expansionBudget?: number;
  handleTtlMs?: number;
  maxHandleUses?: number;
  now?: () => number;
  policyVersion?: string;
  retryBaseMs?: number;
  judgeDeadlineMs?: number;
  maxInFlight?: number;
  sleep?: (ms: number) => Promise<void>;
  /** Durable notes, ledger, nodes, and acknowledgements. Sessions stay in sessionStore. */
  graphStore?: GraphStore;
  /** Opaque handle records. clear() is how a reload expires a walk. */
  sessionStore?: SessionStore;
}

export interface RouteSets {
  candidateIds: string[];
  selectedIds: string[];
  exportedHandles: string[];
  pruned: Array<{ id: string; reason: string }>;
}

export interface ExploreInput {
  personId: string;
  purpose: string;
  anchorId?: string;
  query?: string;
  routeHandle?: string;
  routeId?: string;
  operation?: "continue" | "rewind" | "assess_link";
  rewindToId?: string;
  /** One advertised note on routeId. Any other id is refused. */
  focusId?: string;
  /** Same id returns the saved page. A new id advances the frontier. */
  requestId?: string;
  /** Stay on the chosen note. The next request is what opens a related note. */
  holdAtAnchor?: boolean;
}

export interface CandidateSplit {
  hnsw: string[];
  exact: string[];
}

export interface LocalAssessment {
  judgment: "no_link" | "uncertain";
  relation: Relation;
  activeEdge: boolean;
  excerpt: string;
  otherExcerpt: string;
}

export interface TrailLook {
  page: SemanticData;
  counts: LocalCount;
}

export interface LocalRoute {
  routeId: string;
  label: string;
  kind: NextRoute["kind"];
  nodeIds: string[];
}

export interface LocalOverlay {
  visited: string[];
  frontier: string[];
  anchorId: string;
  counts: LocalCount;
  nodes: Array<{
    id: string;
    sourceType: string;
    capturedAt: string;
    excerpt: string;
    relation: Relation | null;
    onRoute: boolean;
  }>;
}

export interface ViewNode {
  id: string;
  kind: PointerNode["kind"];
  sourceType: string;
  degree: number;
}

export interface ViewModel {
  nodes: ViewNode[];
  links: Array<{ source: number; target: number; reason: string }>;
}

const POLICY_VERSION = "lab-policy-1";
const MODEL_VERSION = "lab-heuristic-1";

export class RawContextLab {
  readonly vault = new Vault();
  readonly log = new AdvertisementLog();
  readonly projection = new Projection();
  readonly metrics = {
    crossPersonCandidates: 0,
    unissuedHandles: 0,
    judgeAttempts: 0,
    cacheClears: 0,
    pruned: [] as Array<{ reason: string; count: number }>,
    pruneRecords: [] as Array<{ id: string; reason: string }>,
  };

  authorizationEpoch = 1;
  private readonly judge: LinkJudge;
  private readonly pageSize: number;
  private readonly maxCandidates: number;
  private readonly hopLimit: number;
  private readonly frontierCap: number;
  private readonly expansionBudget: number;
  private readonly handleTtlMs: number;
  private readonly maxHandleUses: number;
  private readonly now: () => number;
  private readonly retryBaseMs: number;
  private readonly judgeDeadlineMs: number;
  private readonly maxInFlight: number;
  private readonly sleep: (ms: number) => Promise<void>;
  private inFlight = 0;
  private readonly policyVersion: string;
  private readonly seed: number;
  private readonly nodes = new Map<string, PointerNode>();
  private readonly indexes = new Map<string, HnswIndex>();
  private readonly controls = new Map<string, Set<ControlTag>>();
  private readonly handles = new Map<string, HandleRecord>();
  private lookToken: string | null = null;
  private readonly pit: PendingInterestTable = createPendingInterestTable();
  private readonly interestLog = new Map<string, { nonce: string; purpose: string; operation: string; state: "satisfied" }>();
  private readonly routeLog: RouteSetLog = createRouteSets();
  private readonly graphStore: GraphStore | undefined;
  private readonly sessionStore: SessionStore;
  private readonly acknowledgements: LinkAcknowledgement[] = [];
  private hydrating = false;
  private readonly idempotency = new Map<string, IngestResult>();
  private readonly lastPrimary = new Map<string, string>();
  private readonly exportCache = new Map<string, string>();
  private itemCounter = 0;
  private selectionDraft: {
    personId: string;
    candidateIds: string[];
    selectedIds: string[];
    provenance: Record<string, RouteProvenance>;
    pruned: Array<{ id: string; reason: string }>;
    candidates: RankedCandidate[];
  } | null = null;

  constructor(options: LabOptions = {}) {
    this.judge = options.judge ?? heuristicJudge();
    this.seed = options.seed ?? 1;
    this.pageSize = options.pageSize ?? 5;
    this.maxCandidates = options.maxCandidates ?? 8;
    this.hopLimit = options.hopLimit ?? 4;
    this.frontierCap = options.frontierCap ?? 32;
    this.expansionBudget = options.expansionBudget ?? 64;
    this.handleTtlMs = options.handleTtlMs ?? 60_000;
    this.maxHandleUses = options.maxHandleUses ?? 8;
    this.now = options.now ?? Date.now;
    this.retryBaseMs = options.retryBaseMs ?? 0;
    this.judgeDeadlineMs = options.judgeDeadlineMs ?? Number.POSITIVE_INFINITY;
    this.maxInFlight = options.maxInFlight ?? Number.POSITIVE_INFINITY;
    this.sleep = options.sleep ?? (async () => {});
    this.policyVersion = options.policyVersion ?? POLICY_VERSION;
    this.graphStore = options.graphStore;
    this.sessionStore = options.sessionStore ?? new MemorySessionStore();
    this.hydrate();
  }

  routeSets(personId: string): RouteSets | undefined {
    const latest = this.routeLog.latest(personId);
    if (!latest) return undefined;
    return {
      candidateIds: [...latest.sets.candidate],
      selectedIds: [...latest.sets.selected],
      exportedHandles: [...latest.sets.export],
      pruned: this.routeLog.pruneAudit(latest.revision),
    };
  }

  routeHistory(personId: string): number[] {
    return this.routeLog.history(personId).map((revision) => revision.revision);
  }

  interest(personId: string, requestId: string): { nonce: string; purpose: string; operation: string; state: "satisfied" } | undefined {
    return this.interestLog.get(this.pageKey(personId, requestId));
  }

  get hnswSearchCount(): number {
    let count = 0;
    for (const index of this.indexes.values()) count += index.searchCount;
    return count;
  }

  pointer(id: string): PointerNode | undefined {
    const node = this.nodes.get(id);
    return node
      ? { ...node, memberEventIds: [...node.memberEventIds] }
      : undefined;
  }

  controlsFor(eventId: string): ControlTag[] {
    return [...(this.controls.get(eventId) ?? [])];
  }

  mintControl(eventId: string, tag: ControlTag): void {
    if (!this.vault.has(eventId)) throw new Error("unknown event");
    const tags = this.controls.get(eventId) ?? new Set<ControlTag>();
    tags.add(tag);
    this.controls.set(eventId, tags);
  }

  setAuthorizationEpoch(epoch: number): void {
    if (epoch === this.authorizationEpoch) return;
    this.authorizationEpoch = epoch;
    this.clearExportCache();
    for (const handle of this.handles.values()) {
      if (handle.authorizationEpoch !== epoch) {
        handle.invalidated = true;
        handle.invalidReason = "authorization_changed";
      }
    }
  }

  beginRebuild(): void {
    this.projection.status = "rebuilding";
  }

  finishRebuild(): void {
    this.log.verifyDigests();
    assertStructuralLedger(this.log.ads, [...this.nodes.values()]);
    this.projection.rebuild(this.log.ads);
    this.saveDurable();
  }

  addFixture(event: VaultEvent): void {
    this.vault.append(event);
    this.nodes.set(event.id, emptyPointer(event));
    this.indexFor(event.personId).add(event.id, tokenVector(event.text));
    this.saveDurable();
  }

  linkStructural(fromId: string, toId: string, reasonCode = "recorded_association"): LinkAdvertisement {
    const ad = this.appendAd({
      personId: this.personFor(fromId, toId),
      origin: "policy",
      modelVersion: null,
      promptVersion: null,
      policyVersion: this.policyVersion,
      evidenceIds: [fromId, toId].filter((id) => this.vault.has(id)),
      fromId,
      toId,
      judgment: "link",
      reasonCode,
      relation: mapRelation("policy", reasonCode),
      proposedConfidence: 0.4,
      confidence: 0.4,
      createdAt: new Date(this.now()).toISOString(),
      supersedesId: null,
      withdrawn: false,
    });
    this.projection.apply(ad);
    this.saveDurable();
    return ad;
  }

  recordModelJudgment(input: {
    fromId: string;
    toId: string;
    judgment: LinkAdvertisement["judgment"];
    reasonCode: string;
    proposedConfidence: number;
    evidenceIds: string[];
  }): LinkAdvertisement {
    const clean = sanitizeDecision({
      handle: "local",
      judgment: input.judgment,
      reasonCode: input.reasonCode,
      confidence: input.proposedConfidence,
    });
    const confidence = this.capConfidence(
      input.fromId,
      input.toId,
      clamp(clean.confidence),
      input.evidenceIds,
      "model",
    );
    const ad = this.appendAd({
      personId: this.personFor(input.fromId, input.toId),
      origin: "model",
      modelVersion: MODEL_VERSION,
      promptVersion: "lab-prompt-1",
      policyVersion: this.policyVersion,
      evidenceIds: input.evidenceIds,
      fromId: input.fromId,
      toId: input.toId,
      judgment: clean.judgment,
      reasonCode: clean.reasonCode,
      relation: mapRelation("model", clean.reasonCode),
      proposedConfidence: input.proposedConfidence,
      confidence,
      createdAt: new Date(this.now()).toISOString(),
      supersedesId: this.projection.edgeBetween(input.fromId, input.toId)?.adId ?? null,
      withdrawn: false,
    });
    if (this.projection.apply(ad)) this.invalidateForSnapshot();
    this.saveDurable();
    return ad;
  }

  correct(input: {
    fromId: string;
    toId: string;
    judgment: LinkAdvertisement["judgment"];
    confidence: number;
    evidenceIds: string[];
  }): LinkAdvertisement {
    const ad = this.appendAd({
      personId: this.personFor(input.fromId, input.toId),
      origin: "user_correction",
      modelVersion: null,
      promptVersion: null,
      policyVersion: this.policyVersion,
      evidenceIds: input.evidenceIds,
      fromId: input.fromId,
      toId: input.toId,
      judgment: input.judgment,
      reasonCode: "user_correction",
      relation: mapRelation("user_correction", "user_correction"),
      proposedConfidence: input.confidence,
      confidence: input.confidence,
      createdAt: new Date(this.now()).toISOString(),
      supersedesId: this.projection.edgeBetween(input.fromId, input.toId)?.adId ?? null,
      withdrawn: false,
    });
    this.projection.apply(ad);
    this.invalidateForSnapshot();
    this.saveDurable();
    return ad;
  }

  withdraw(adId: string): LinkAdvertisement {
    const previous = this.log.get(adId);
    if (!previous) throw new Error("unknown advertisement");
    const ad = this.appendAd({
      personId: previous.personId,
      origin: "user_correction",
      modelVersion: null,
      promptVersion: null,
      policyVersion: this.policyVersion,
      evidenceIds: previous.evidenceIds,
      fromId: previous.fromId,
      toId: previous.toId,
      judgment: previous.judgment,
      reasonCode: "withdrawal",
      relation: mapRelation("user_correction", "withdrawal"),
      proposedConfidence: 0,
      confidence: 0,
      createdAt: new Date(this.now()).toISOString(),
      supersedesId: adId,
      withdrawn: true,
    });
    this.projection.apply(ad);
    this.dropAcknowledgement(previous.personId, previous.fromId, previous.toId);
    this.invalidateForSnapshot();
    this.clearExportCache();
    this.saveDurable();
    return ad;
  }

  async ingest(input: IngestInput): Promise<IngestResult> {
    const cached = this.idempotency.get(`${input.personId}|${input.idempotencyKey}`);
    if (cached) return cached;

    const eventId = `evt_${sha256(`${input.personId}|${input.idempotencyKey}`).slice(0, 16)}`;
    if (!this.vault.has(eventId)) {
      const event: VaultEvent = {
        id: eventId,
        personId: input.personId,
        capturedAt: input.capturedAt,
        sourceType: input.sourceType,
        text: input.text,
        contentHash: sha256(input.text),
        lineageId: input.lineageId,
        independence: input.independence,
        sourceArrival: input.sourceArrival,
        copiedFromId: input.copiedFromId ?? null,
        documentId: input.documentId ?? null,
      };
      this.vault.append(event);
      this.nodes.set(event.id, emptyPointer(event));
      this.indexFor(input.personId).add(event.id, tokenVector(event.text));
      if (input.documentId) this.attachHub(event);
    }

    if (this.projection.status === "rebuilding") {
      return this.remember(input, {
        eventId,
        candidateCount: 0,
        exportBytes: 0,
        judgments: [],
        terminalReason: "dependency_unavailable",
        detail: DETAILS.dependency_unavailable,
        routeRevision: null,
        pruned: [],
      });
    }

    const candidateIds = this.selectCandidates(input.personId, input.text, eventId, input.capturedAt);
    const issued = new Map<string, string>();
    const candidates: JudgeRequest["candidates"] = [];
    for (const id of candidateIds) {
      const exported = this.exportNode(id, "candidate");
      if (!exported) continue;
      issued.set(exported.handle, id);
      candidates.push({
        handle: exported.handle,
        excerpt: exported.excerpt,
        sourceType: exported.sourceType,
        capturedAt: exported.capturedAt,
      });
    }
    const published = this.publishSelection(input.personId, issued);
    const request: JudgeRequest = {
      newHandle: "ch_new",
      excerpt: input.text.slice(0, 180),
      sourceType: input.sourceType,
      capturedAt: input.capturedAt,
      candidates,
    };
    const exportBytes = new TextEncoder().encode(JSON.stringify(request)).length;
    let decisions: JudgeDecision[];
    try {
      decisions = await this.judgeWithRetry(request);
    } catch {
      return this.remember(input, {
        eventId,
        candidateCount: candidates.length,
        exportBytes,
        judgments: [],
        terminalReason: "dependency_unavailable",
        detail: DETAILS.dependency_unavailable,
        routeRevision: published.revision,
        pruned: published.pruned,
      });
    }

    const judgments: IngestResult["judgments"] = [];
    for (const raw of decisions) {
      const decision = sanitizeDecision(raw);
      const otherId = issued.get(decision.handle);
      if (!otherId) {
        this.metrics.unissuedHandles += 1;
        judgments.push({
          handle: decision.handle,
          judgment: decision.judgment,
          reasonCode: decision.reasonCode,
          accepted: false,
        });
        continue;
      }
      const other = this.nodes.get(otherId);
      if (!other || other.personId !== input.personId) {
        this.metrics.crossPersonCandidates += 1;
        judgments.push({
          handle: decision.handle,
          judgment: decision.judgment,
          reasonCode: decision.reasonCode,
          accepted: false,
        });
        continue;
      }
      const evidenceIds = [eventId, otherId];
      const confidence = this.capConfidence(
        eventId,
        otherId,
        clamp(decision.confidence),
        evidenceIds,
        "model",
      );
      const ad = this.appendAd({
        personId: input.personId,
        origin: "model",
        modelVersion: MODEL_VERSION,
        promptVersion: "lab-prompt-1",
        policyVersion: this.policyVersion,
        evidenceIds,
        fromId: eventId,
        toId: otherId,
        judgment: decision.judgment,
        reasonCode: decision.reasonCode,
        relation: mapRelation("model", decision.reasonCode),
        proposedConfidence: clamp(decision.confidence),
        confidence,
        createdAt: input.capturedAt,
        supersedesId: this.projection.edgeBetween(eventId, otherId)?.adId ?? null,
        withdrawn: false,
      });
      this.projection.apply(ad);
      judgments.push({
        handle: decision.handle,
        judgment: decision.judgment,
        reasonCode: decision.reasonCode,
        accepted: true,
      });
    }

    await this.judgeReferralRound(input, eventId, issued, judgments);

    return this.remember(input, {
      eventId,
      candidateCount: candidates.length,
      exportBytes,
      judgments,
      terminalReason: null,
      detail: "",
      routeRevision: published.revision,
      pruned: published.pruned,
    });
  }

  explore(input: ExploreInput): SemanticData {
    const operation = input.routeHandle ? input.operation ?? "continue" : "open";
    let nonce: string | undefined;
    if (input.requestId) {
      const began = this.pit.begin(this.semanticInterest(input, operation), input.routeHandle ?? input.anchorId ?? input.query ?? "open");
      if (began.state === "rejected") return this.stopped("policy_blocked", DETAILS.wrong_purpose);
      if (began.state === "satisfied") return this.replay(began.result as SemanticData);
      if (began.joined) return this.stopped("dependency_unavailable");
      nonce = began.nonce;
    }
    const data = input.routeHandle ? this.continueHandle(input) : this.openRoute(input);
    if (nonce) {
      this.pit.satisfy(nonce, data);
      this.interestLog.set(this.pageKey(input.personId, nonce), {
        nonce,
        purpose: input.purpose,
        operation,
        state: "satisfied",
      });
    }
    return data;
  }

  private openRoute(input: ExploreInput): SemanticData {
    if (this.projection.status === "rebuilding") {
      return this.stopped("dependency_unavailable");
    }
    if (input.anchorId) {
      const node = this.nodes.get(input.anchorId);
      if (!node || node.personId !== input.personId) {
        return this.stopped("policy_blocked", DETAILS.unknown_anchor);
      }
    } else if (!input.query && this.personCount(input.personId) === 0) {
      return this.stopped("supported_leaf");
    } else if (!input.query) {
      return this.stopped("policy_blocked", DETAILS.unknown_anchor);
    }

    const record = this.blankHandle(input);
    if (input.anchorId) {
      record.anchorId = input.anchorId;
      record.approximateSeed = false;
      record.visitedNodes.push(input.anchorId);
      record.breadcrumb.push(this.breadcrumbLabel(input.anchorId));
      this.expand(record, input.anchorId);
      if (input.holdAtAnchor) return this.finish(record, [], [], null);
    } else if (input.query) {
      record.approximateSeed = true;
      const seeds = this.selectCandidates(input.personId, input.query, "", "");
      for (const id of seeds) record.frontier.push(this.frontierFrom(id, "semantic_candidate"));
      if (seeds.length === 0) {
        const reason: TerminalReason =
          this.personCount(input.personId) === 0
            ? "supported_leaf"
            : "approximate_frontier_exhausted";
        return this.stopped(reason);
      }
      record.anchorId = seeds[0] ?? "";
    }
    return this.step(record);
  }

  private pageKey(personId: string, requestId: string): string {
    return `${personId}|${requestId}`;
  }

  private replay(saved: SemanticData): SemanticData {
    const record = this.loadHandle(saved.route);
    if (record && record.authorizationEpoch !== this.authorizationEpoch) {
      return this.stopped("authorization_changed");
    }
    if (
      saved.snapshotRevision !== this.projection.revision ||
      saved.snapshotDigest !== this.projection.digest
    ) {
      return this.stopped("stale_snapshot");
    }
    return saved;
  }

  localRoutes(routeHandle: string): LocalRoute[] {
    const record = this.handles.get(routeHandle);
    if (!record || record.invalidated) return [];
    return record.advertised.map((route) => ({ ...route, nodeIds: [...route.nodeIds] }));
  }

  localOverlay(routeHandle: string): LocalOverlay | undefined {
    const record = this.handles.get(routeHandle);
    if (!record) return undefined;
    const reach = record.anchorId
      ? this.reachable(record.anchorId)
      : { count: record.visitedNodes.length, capped: false };
    const ids = [
      ...new Set([...record.visitedNodes, ...record.frontier.map((item) => item.nodeId)]),
    ];
    return {
      visited: [...record.visitedNodes],
      frontier: record.frontier.map((item) => item.nodeId),
      anchorId: record.anchorId,
      counts: {
        exploredCount: record.visitedNodes.length,
        unexploredCount: Math.max(
          0,
          reach.count - record.visitedNodes.length,
          record.frontier.length,
        ),
        reachableCount: reach.count,
        countLabel: reach.capped || record.approximateSeed ? "approximate" : "exact",
      },
      nodes: ids.map((id) => this.localNode(id, record)),
    };
  }

  describeTrail(personId: string, trail: readonly string[]): TrailLook {
    if (this.lookToken) {
      this.handles.delete(this.lookToken);
      this.lookToken = null;
    }
    const ids = trail.filter((id) => this.nodes.get(id)?.personId === personId);
    if (ids.length === 0) {
      const page = this.stopped("supported_leaf");
      return {
        page,
        counts: { exploredCount: 0, unexploredCount: 0, reachableCount: 0, countLabel: "exact" },
      };
    }
    const anchor = ids[0] ?? "";
    const record = this.blankHandle({ personId, purpose: "look", anchorId: anchor });
    this.lookToken = record.token;
    record.anchorId = anchor;
    record.visitedNodes.push(anchor);
    record.breadcrumb.push(this.breadcrumbLabel(anchor));
    this.expand(record, anchor);
    for (const id of ids.slice(1)) {
      const previous = record.visitedNodes[record.visitedNodes.length - 1];
      if (!previous || !this.projection.neighbors(previous).includes(id)) break;
      if (record.visitedNodes.includes(id)) {
        record.cycleCount += 1;
        continue;
      }
      const key = edgeKey(previous, id);
      record.frontier = record.frontier.filter((item) => item.nodeId !== id);
      record.visitedNodes.push(id);
      record.visitedEdges.push(key);
      record.hopDepth += 1;
      record.breadcrumb.push(this.breadcrumbLabel(id));
      this.expand(record, id);
    }
    const page = this.finish(record, [], [], null);
    const counts = this.localOverlay(record.token)?.counts ?? {
      exploredCount: record.visitedNodes.length,
      unexploredCount: 0,
      reachableCount: record.visitedNodes.length,
      countLabel: "exact" as const,
    };
    return { page, counts };
  }

  localAssessments(personId: string): LocalAssessment[] {
    const rows: LocalAssessment[] = [];
    for (const ad of this.log.ads) {
      if (ad.withdrawn || ad.judgment === "link") continue;
      const from = this.nodes.get(ad.fromId);
      if (!from || from.personId !== personId) continue;
      rows.push({
        judgment: ad.judgment,
        relation: ad.relation,
        activeEdge: Boolean(this.projection.edgeBetween(ad.fromId, ad.toId)),
        excerpt: this.vault.get(ad.fromId)?.text.slice(0, 80) ?? ad.fromId,
        otherExcerpt: this.vault.get(ad.toId)?.text.slice(0, 80) ?? ad.toId,
      });
    }
    return rows.slice(-12);
  }

  candidateSplit(personId: string, text: string, selfId: string): CandidateSplit {
    const exact = this.exactCandidates(personId, text, selfId);
    const index = this.indexes.get(personId);
    const hnsw = index
      ? index
          .search(tokenVector(text), 16)
          .map((hit) => hit.id)
          .filter((id) => id !== selfId)
      : [];
    return { hnsw, exact };
  }

  view(personId: string): ViewModel {
    const nodes = [...this.nodes.values()].filter((node) => node.personId === personId);
    const index = new Map(nodes.map((node, position) => [node.id, position]));
    const links: ViewModel["links"] = [];
    for (const edge of this.projection.accepted()) {
      const source = index.get(edge.fromId);
      const target = index.get(edge.toId);
      if (source === undefined || target === undefined) continue;
      links.push({ source, target, reason: edge.reasonCode });
    }
    return {
      nodes: nodes.map((node) => ({
        id: node.id,
        kind: node.kind,
        sourceType: this.vault.get(node.id)?.sourceType ?? "hub",
        degree: this.projection.degree(node.id),
      })),
      links,
    };
  }

  private remember(input: IngestInput, result: IngestResult): IngestResult {
    assertSafeDetail(result.detail);
    this.idempotency.set(`${input.personId}|${input.idempotencyKey}`, result);
    this.saveDurable();
    return result;
  }

  private async judgeWithRetry(request: JudgeRequest): Promise<JudgeDecision[]> {
    const startedAt = this.now();
    let lastError: unknown = new Error("dependency_unavailable");
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const decision = scheduleAttempt({
        attempt,
        now: this.now(),
        startedAt,
        deadlineMs: this.judgeDeadlineMs,
        baseMs: this.retryBaseMs,
        inFlight: this.inFlight,
        maxInFlight: this.maxInFlight,
        seed: this.seed,
      });
      if (decision.action === "stop") throw new Error(decision.reason);
      if (attempt > 0 && decision.delayMs > 0) await this.sleep(decision.delayMs);
      this.metrics.judgeAttempts += 1;
      this.inFlight += 1;
      try {
        return await this.judge.judge(request);
      } catch (error) {
        lastError = error;
      } finally {
        this.inFlight -= 1;
      }
    }
    throw lastError;
  }

  private selectCandidates(personId: string, text: string, selfId: string, capturedAt: string): string[] {
    const exact = this.exactCandidates(personId, text, selfId);
    const index = this.indexes.get(personId);
    const hits = index ? index.search(tokenVector(text), 16) : [];
    const distances = new Map(hits.map((hit) => [hit.id, hit.distance]));
    const union = new Set<string>([...exact, ...hits.map((hit) => hit.id)]);
    const ranked: Array<Rankable & { lineage: string; sourceType: string; capturedAt: string }> = [];
    for (const id of union) {
      if (id === selfId) continue;
      const node = this.nodes.get(id);
      if (!node || node.personId !== personId) {
        this.metrics.crossPersonCandidates += 1;
        continue;
      }
      const tags = this.controls.get(id);
      if (tags?.has("no-model") || tags?.has("no-forward")) continue;
      const event = this.vault.get(id);
      const degree = this.projection.degree(id);
      const distance = distances.get(id);
      const similarity =
        distance === undefined ? jaccard(text, event?.text ?? "") : 1 - distance;
      ranked.push({
        id,
        authorized: 1,
        provenance: 1,
        relevance: similarity,
        novelty: 1,
        inverseDegree: inverseDegree(degree),
        inverseHop: 1,
        lineage: event?.lineageId ?? id,
        sourceType: event?.sourceType ?? "hub",
        capturedAt: event?.capturedAt ?? "",
      });
    }
    ranked.sort(compareRank);
    const held = applyHysteresis(ranked, this.lastPrimary.get(personId));
    if (held.heldPrevious) {
      this.metrics.pruned.push({ reason: "hysteresis_hold", count: 1 });
      const heldId = held.ranked[0]?.id;
      if (heldId) this.metrics.pruneRecords.push({ id: heldId, reason: "hysteresis_hold" });
    }
    const ordered = held.ranked;
    const tokenIds = this.tokenMatches(personId, text, selfId);
    const hnswIds = new Set(hits.map((hit) => hit.id));
    const neighborIds = new Set(exact.filter((id) => !tokenIds.has(id)));
    const candidates: RankedCandidate[] = ordered.map((item) => ({
      id: item.id,
      lineage: item.lineage,
      sourceType: item.sourceType,
      facet: item.sourceType,
      reason: this.discoveryOf(item.id, tokenIds, neighborIds, hnswIds),
      capturedAt: item.capturedAt,
      relevance: item.relevance,
      neighbors: this.candidateNeighbors(personId, text, item.id, selfId),
    }));
    const selection = applySelection({ capturedAt: capturedAt || undefined, candidates });
    const kept = selection.kept.slice(0, this.maxCandidates);
    const pruned = [
      ...selection.pruned,
      ...selection.kept.slice(this.maxCandidates).map((id) => ({ id, reason: "candidate_cap" })),
    ];
    for (const row of pruned) {
      this.metrics.pruned.push({ reason: row.reason, count: 1 });
      this.metrics.pruneRecords.push(row);
    }
    const provenance: Record<string, RouteProvenance> = {};
    ordered.forEach((item, rank) => {
      const prune = pruned.find((row) => row.id === item.id);
      provenance[item.id] = {
        discovery: this.discoveryOf(item.id, tokenIds, neighborIds, hnswIds),
        rank,
        pruneReason: prune?.reason ?? (kept.includes(item.id) ? null : "candidate_cap"),
        exportHandle: null,
      };
    });
    this.selectionDraft = { personId, candidateIds: ordered.map((item) => item.id), selectedIds: kept, provenance, pruned, candidates };
    if (kept[0]) this.lastPrimary.set(personId, kept[0]);
    return kept;
  }

  private exactCandidates(personId: string, text: string, selfId: string): string[] {
    const tokens = new Set(tokenize(text));
    const matched: string[] = [];
    for (const event of this.vault.list()) {
      if (event.personId !== personId || event.id === selfId) continue;
      if (tokenize(event.text).some((word) => tokens.has(word))) matched.push(event.id);
    }
    const ids = new Set(matched);
    const seeds = selfId ? [selfId, ...matched] : matched;
    for (const id of seeds) {
      for (const other of this.projection.neighbors(id)) {
        if (other === selfId) continue;
        const node = this.nodes.get(other);
        if (node?.personId === personId) ids.add(other);
      }
    }
    return [...ids];
  }

  private capConfidence(
    fromId: string,
    toId: string,
    proposed: number,
    evidenceIds: string[],
    origin: LinkAdvertisement["origin"],
  ): number {
    if (origin !== "model") return proposed;
    const existing = this.projection.edgeBetween(fromId, toId);
    if (!existing) return proposed;
    const previous = new Set(
      existing.evidenceIds
        .map((id) => this.knownFamily(id))
        .filter((lineage): lineage is string => lineage !== undefined),
    );
    const independent = evidenceIds
      .map((id) => this.knownFamily(id))
      .filter((lineage): lineage is string => lineage !== undefined && !previous.has(lineage));
    if (independent.length === 0 && proposed > existing.confidence) return existing.confidence;
    return proposed;
  }

  private knownFamily(id: string): string | undefined {
    const event = this.vault.get(id);
    if (!event || event.independence === "unknown") return undefined;
    return event.lineageId;
  }

  private localNode(
    id: string,
    record: HandleRecord,
  ): LocalOverlay["nodes"][number] {
    const event = this.vault.get(id);
    let relation: Relation | null = null;
    for (const other of this.projection.neighbors(id)) {
      if (!record.visitedNodes.includes(other)) continue;
      const edge = this.projection.edgeBetween(id, other);
      if (edge) {
        relation = edge.relation;
        break;
      }
    }
    return {
      id,
      sourceType: event?.sourceType ?? "hub",
      capturedAt: event?.capturedAt.slice(0, 10) ?? "",
      excerpt: event ? event.text.slice(0, 80) : "document hub",
      relation,
      onRoute: record.visitedNodes.includes(id),
    };
  }

  private continueHandle(input: ExploreInput): SemanticData {
    const record = input.routeHandle ? this.loadHandle(input.routeHandle) : undefined;
    if (!record) return this.stopped("policy_blocked", DETAILS.unknown_handle);
    if (record.personId !== input.personId) return this.stopped("policy_blocked");
    if (record.purpose !== input.purpose) return this.stopped("policy_blocked", DETAILS.wrong_purpose);
    if (input.operation === "assess_link") return this.stopped("policy_blocked", DETAILS.wrong_operation);
    if (record.authorizationEpoch !== this.authorizationEpoch || record.invalidReason === "authorization_changed") {
      return this.stopped("authorization_changed");
    }
    if (
      record.invalidated ||
      record.invalidReason === "stale_snapshot" ||
      record.snapshotRevision !== this.projection.revision ||
      record.snapshotDigest !== this.projection.digest
    ) {
      return this.stopped("stale_snapshot");
    }
    if (input.focusId && !input.routeId) return this.stopped("policy_blocked");
    if (input.routeId && input.focusId) {
      const bound = record.routeBindings.get(input.routeId) ?? [];
      if (!bound.includes(input.focusId)) return this.stopped("policy_blocked");
    }
    if (this.now() > record.expiresAt) return this.stopped("policy_blocked", DETAILS.handle_expired);
    if (record.useCount >= record.maxUses) return this.stopped("policy_blocked", DETAILS.handle_use_limit);
    if (input.operation === "rewind") {
      if (!input.rewindToId) return this.stopped("policy_blocked", DETAILS.rewind_target);
      record.useCount += 1;
      return this.rewind(record, input.rewindToId);
    }
    const searches = this.hnswSearchCount;
    record.useCount += 1;
    let aside: FrontierItem[] = [];
    if (input.routeId) {
      const bound = record.routeBindings.get(input.routeId) ?? [];
      if (bound.length === 0) return this.stopped("supported_leaf");
      const chosen = record.advertised.find((route) => route.routeId === input.routeId);
      const retrieves = chosen?.kind === "facet" || chosen?.kind === "temporal" || chosen?.kind === "source";
      if (retrieves) {
        record.frontier = record.frontier.filter((item) => bound.includes(item.nodeId));
        return this.finish(record, [], [], null);
      }
      if (input.focusId) {
        aside = record.frontier.filter((item) => item.nodeId !== input.focusId);
        record.frontier = record.frontier.filter((item) => item.nodeId === input.focusId);
      } else {
        record.frontier = record.frontier.filter((item) => bound.includes(item.nodeId));
      }
    }
    const data = this.step(record, aside, Boolean(input.focusId));
    if (this.hnswSearchCount !== searches) {
      throw new Error("continuation must not rerun candidate search");
    }
    return data;
  }

  private tip(record: HandleRecord): string {
    return record.visitedNodes[record.visitedNodes.length - 1] ?? "";
  }

  private forwardItems(record: HandleRecord): FrontierItem[] {
    return forwardFromTip(record.frontier, this.tip(record));
  }

  private rewind(record: HandleRecord, targetId: string): SemanticData {
    const cut = truncatePath(record.visitedNodes, targetId);
    if ("error" in cut) return this.stopped("policy_blocked", DETAILS.rewind_target);
    const index = cut.visited.length - 1;
    record.visitedNodes = cut.visited;
    record.breadcrumb = record.breadcrumb.slice(0, cut.visited.length);
    record.hopDepth = Math.max(0, index);
    const edges: string[] = [];
    for (let position = 1; position < record.visitedNodes.length; position += 1) {
      edges.push(edgeKey(record.visitedNodes[position - 1] ?? "", record.visitedNodes[position] ?? ""));
    }
    record.visitedEdges = edges;
    record.frontier = record.frontier.filter(
      (item) => record.visitedNodes.includes(item.fromId) && !record.visitedNodes.includes(item.nodeId),
    );
    this.expand(record, targetId);
    return this.finish(record, [], [], null);
  }

  private step(record: HandleRecord, aside: FrontierItem[] = [], one = false): SemanticData {
    const limit = one ? 1 : this.pageSize;
    const items: ExportItem[] = [];
    const already: string[] = [];
    const done = (terminal: TerminalReason | null): SemanticData => {
      this.restoreFrontier(record, aside);
      return this.finish(record, items, already, terminal);
    };
    while (items.length < limit) {
      if (record.expansions >= this.expansionBudget || record.hopDepth >= this.hopLimit) {
        return done("budget_exhausted");
      }
      const forward = this.forwardItems(record).sort((a, b) => compareRank(a.rank, b.rank));
      const next = forward[0];
      if (!next) break;
      record.frontier = record.frontier.filter((item) => item !== next);
      if (record.visitedNodes.includes(next.nodeId) || record.visitedEdges.includes(next.edgeKey)) {
        record.cycleCount += 1;
        already.push("already_explored");
        continue;
      }
      record.visitedNodes.push(next.nodeId);
      record.visitedEdges.push(next.edgeKey);
      record.hopDepth += 1;
      record.breadcrumb.push(this.breadcrumbLabel(next.nodeId));
      const exported = this.exportNode(next.nodeId, next.reason);
      if (exported) items.push(exported);
      this.expand(record, next.nodeId);
    }
    return done(null);
  }

  private restoreFrontier(record: HandleRecord, aside: FrontierItem[]): void {
    for (const item of aside) {
      if (record.visitedNodes.includes(item.nodeId)) continue;
      if (record.frontier.some((saved) => saved.nodeId === item.nodeId)) continue;
      record.frontier.push(item);
    }
  }

  private finish(
    record: HandleRecord,
    items: ExportItem[],
    already: string[],
    terminal: TerminalReason | null,
  ): SemanticData {
    let terminalReason = terminal;
    let exhaustion: Exhaustion = "not_yet_exhausted";
    if (!terminalReason && this.forwardItems(record).length === 0) {
      if (record.lineagePruned && !this.componentCovered(record)) {
        terminalReason = "insufficient_independent_evidence";
        exhaustion = "exact";
      } else if (items.length === 0 && already.length === 0) {
        terminalReason = record.approximateSeed && !this.componentCovered(record)
          ? "approximate_frontier_exhausted"
          : "supported_leaf";
        exhaustion = terminalReason === "approximate_frontier_exhausted" ? "approximate" : "exact";
      }
    } else if (terminalReason === "budget_exhausted") {
      exhaustion = "not_yet_exhausted";
    } else if (terminalReason) {
      exhaustion = "exact";
    }

    const detail = terminalReason
      ? DETAILS[terminalReason]
      : "exploration can continue from the saved frontier";
    assertSafeDetail(detail);

    let nextRoutes: NextRoute[] = [];
    if (!terminalReason) {
      const advertised = this.advertise(record);
      record.advertised = advertised;
      record.routeBindings = new Map(advertised.map((route) => [route.routeId, route.nodeIds]));
      nextRoutes = advertised.map(({ routeId, label, kind }) => ({ routeId, label, kind }));
    } else if (!retainsSession(terminalReason)) {
      record.invalidated = true;
      record.invalidReason = terminalReason;
    }
    this.persistSession(record);

    const current = record.visitedNodes[record.visitedNodes.length - 1] ?? record.anchorId;
    return {
      route: record.token,
      breadcrumb: record.breadcrumb.slice(-8),
      hopDepth: record.hopDepth,
      directLinkCount: current ? this.projection.degree(current) : 0,
      cycleCount: record.cycleCount,
      exhaustion,
      items,
      alreadyExplored: already,
      nextRoutes,
      terminalReason,
      detail,
      routeHandle: retainsSession(terminalReason) ? record.token : null,
      snapshotRevision: this.projection.revision,
      snapshotDigest: this.projection.digest,
    };
  }

  private expand(record: HandleRecord, nodeId: string): void {
    const lineageCounts = new Map<string, number>();
    for (const item of record.frontier) {
      const lineage = this.vault.get(item.nodeId)?.lineageId ?? item.nodeId;
      lineageCounts.set(lineage, (lineageCounts.get(lineage) ?? 0) + 1);
    }
    const ranked: FrontierItem[] = [];
    for (const other of this.projection.neighbors(nodeId)) {
      record.expansions += 1;
      if (record.expansions > this.expansionBudget) {
        this.metrics.pruned.push({ reason: "expansion_budget", count: 1 });
        break;
      }
      const key = edgeKey(nodeId, other);
      if (record.visitedNodes.includes(other) || record.visitedEdges.includes(key)) {
        record.cycleCount += 1;
        continue;
      }
      if (record.frontier.some((item) => item.nodeId === other && item.fromId === nodeId)) continue;
      const lineage = this.vault.get(other)?.lineageId ?? other;
      const seen = lineageCounts.get(lineage) ?? 0;
      if (seen >= LAB_CAP) {
        record.lineagePruned = true;
        this.metrics.pruned.push({ reason: "lineage_cap", count: 1 });
        continue;
      }
      lineageCounts.set(lineage, seen + 1);
      const edge = this.projection.edgeBetween(nodeId, other);
      ranked.push(
        this.frontierFrom(
          other,
          edge?.reasonCode ?? "recorded_association",
          key,
          record.hopDepth,
          edge?.confidence ?? 0.4,
          nodeId,
        ),
      );
    }
    ranked.sort((a, b) => compareRank(a.rank, b.rank));
    const room = this.frontierCap - record.frontier.length;
    if (ranked.length > Math.max(0, room)) {
      const overflow = ranked.slice(Math.max(0, room));
      this.metrics.pruned.push({ reason: "frontier_cap", count: overflow.length });
      for (const item of overflow) this.metrics.pruneRecords.push({ id: item.nodeId, reason: "frontier_cap" });
    }
    if (room > 0) record.frontier.push(...ranked.slice(0, room));
  }

  private frontierFrom(
    nodeId: string,
    reason: string,
    key = `seed|${nodeId}`,
    hop = 0,
    confidence = 0.4,
    fromId = "",
  ): FrontierItem {
    const degree = this.projection.degree(nodeId);
    return {
      nodeId,
      fromId,
      edgeKey: key,
      reason,
      rank: {
        id: nodeId,
        authorized: 1,
        provenance: provenanceRank("policy"),
        relevance: confidence,
        novelty: 1,
        inverseDegree: inverseDegree(degree),
        inverseHop: 1 / (1 + hop),
      },
    };
  }

  private advertise(record: HandleRecord): LocalRoute[] {
    const routes: LocalRoute[] = [];
    const anchor = this.vault.get(record.anchorId);
    const currentId = record.visitedNodes[record.visitedNodes.length - 1] ?? record.anchorId;
    const current = this.vault.get(currentId);
    const frontierIds = this.forwardItems(record).map((item) => item.nodeId);
    let serial = 0;
    const push = (kind: NextRoute["kind"], label: string, nodeIds: string[]) => {
      const limit = kind === "fallback" ? 7 : 6;
      if (routes.length >= limit) return;
      if (kind !== "fallback" && nodeIds.length === 0) return;
      serial += 1;
      const routeId = `nr_${serial}`;
      routes.push({ routeId, label, kind, nodeIds: [...nodeIds] });
    };
    for (const id of frontierIds.slice(0, 3)) {
      push("neighbour", `Open ${id}`, [id]);
    }
    const byType = new Map<string, string[]>();
    const earlier: string[] = [];
    const later: string[] = [];
    for (const id of frontierIds) {
      const event = this.vault.get(id);
      if (!event) continue;
      const group = byType.get(event.sourceType) ?? [];
      group.push(id);
      byType.set(event.sourceType, group);
      if (anchor && event.capturedAt < anchor.capturedAt) earlier.push(id);
      if (anchor && event.capturedAt > anchor.capturedAt) later.push(id);
    }
    const firstType = [...byType.entries()][0];
    if (firstType) push("facet", `Only ${sourceName(firstType[0]).toLowerCase()}s`, firstType[1]);
    if (earlier.length > 0) push("temporal", "Earlier context", earlier);
    if (later.length > 0) push("temporal", "Later context", later);
    const sourceIds = frontierIds.filter((id) => {
      if (current?.copiedFromId === id) return true;
      const node = this.nodes.get(id);
      return node?.kind === "pseudonode" && node.memberEventIds.includes(currentId);
    });
    if (sourceIds.length > 0) push("source", "Original record", sourceIds);
    push("fallback", "Stop here", []);
    return selectIssuedActions(routes);
  }

  private componentCovered(record: HandleRecord): boolean {
    const start = record.anchorId || record.visitedNodes[0];
    if (!start) return true;
    const seen = new Set<string>();
    const queue = [start];
    while (queue.length > 0) {
      const id = queue.shift();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      if (!record.visitedNodes.includes(id)) return false;
      for (const neighbor of this.projection.neighbors(id)) {
        if (!seen.has(neighbor)) queue.push(neighbor);
      }
    }
    return true;
  }

  private reachable(anchorId: string): { count: number; capped: boolean } {
    const seen = new Set<string>();
    const queue = [anchorId];
    while (queue.length > 0 && seen.size < 200) {
      const id = queue.shift();
      if (!id || seen.has(id)) continue;
      seen.add(id);
      for (const neighbor of this.projection.neighbors(id)) {
        if (!seen.has(neighbor)) queue.push(neighbor);
      }
    }
    return { count: seen.size, capped: queue.some((id) => !seen.has(id)) };
  }

  private blankHandle(input: ExploreInput): HandleRecord {
    const token = routeToken();
    const record: HandleRecord = {
      token,
      personId: input.personId,
      session: "exploration",
      purpose: input.purpose,
      authorizationEpoch: this.authorizationEpoch,
      snapshotRevision: this.projection.revision,
      snapshotDigest: this.projection.digest,
      frontier: [],
      visitedNodes: [],
      visitedEdges: [],
      breadcrumb: [],
      hopDepth: 0,
      cycleCount: 0,
      expansions: 0,
      anchorId: "",
      approximateSeed: false,
      expiresAt: this.now() + this.handleTtlMs,
      useCount: 0,
      maxUses: this.maxHandleUses,
      routeBindings: new Map(),
      advertised: [],
      lineagePruned: false,
      invalidated: false,
      invalidReason: null,
    };
    this.handles.set(token, record);
    this.persistSession(record);
    return record;
  }

  private exportNode(id: string, reason: string): ExportItem | null {
    const cacheId = `${this.authorizationEpoch}|${this.projection.revision}|${id}|${reason}`;
    const node = this.nodes.get(id);
    if (!node || node.personId === undefined) return null;
    const tags = this.controls.get(id);
    if (tags?.has("no-model") || tags?.has("no-forward")) return null;
    const event = this.vault.get(id);
    this.itemCounter += 1;
    const handle = `ih_${this.itemCounter.toString(36)}`;
    const excerpt = !event
      ? `document hub with ${node.memberEventIds.length} source members`
      : tags?.has("summary-only")
        ? `${event.sourceType} ${event.capturedAt}`
        : event.text.slice(0, 180);
    this.exportCache.set(cacheId, handle);
    return {
      handle,
      excerpt,
      sourceType: event?.sourceType ?? "hub",
      capturedAt: event?.capturedAt ?? "",
      reason,
      requiresConfirmation: tags?.has("requires-confirmation") ?? false,
    };
  }

  private breadcrumbLabel(id: string): string {
    const event = this.vault.get(id);
    if (!event) return "Record";
    return `${sourceName(event.sourceType)} ${event.capturedAt.slice(0, 10)}`;
  }

  private stopped(reason: TerminalReason, detail?: string): SemanticData {
    const text = detail ?? DETAILS[reason];
    assertSafeDetail(text);
    const exhaustion: Exhaustion =
      reason === "approximate_frontier_exhausted"
        ? "approximate"
        : reason === "budget_exhausted"
          ? "not_yet_exhausted"
          : "exact";
    return {
      route: "stopped",
      breadcrumb: [],
      hopDepth: 0,
      directLinkCount: 0,
      cycleCount: 0,
      exhaustion,
      items: [],
      alreadyExplored: [],
      nextRoutes: [],
      terminalReason: reason,
      detail: text,
      routeHandle: null,
      snapshotRevision: this.projection.revision,
      snapshotDigest: this.projection.digest,
    };
  }

  private invalidateForSnapshot(): void {
    for (const handle of this.handles.values()) {
      if (handle.snapshotRevision !== this.projection.revision) {
        handle.invalidated = true;
        handle.invalidReason = handle.invalidReason ?? "stale_snapshot";
      }
    }
  }

  private clearExportCache(): void {
    if (this.exportCache.size > 0) this.metrics.cacheClears += 1;
    this.exportCache.clear();
  }

  private attachHub(event: VaultEvent): void {
    if (!event.documentId) return;
    const hubId = `hub_${event.personId}_${event.documentId}`;
    let hub = this.nodes.get(hubId);
    if (!hub) {
      hub = {
        id: hubId,
        kind: "pseudonode",
        vaultEventId: null,
        memberEventIds: [],
        personId: event.personId,
      };
      this.nodes.set(hubId, hub);
    }
    hub.memberEventIds.push(event.id);
    this.linkStructural(event.id, hubId, "membership");
  }

  expireExploration(): void {
    this.handles.clear();
    this.sessionStore.clear();
    this.pit.clear();
    this.interestLog.clear();
  }

  acknowledge(personId: string, fromId: string, toId: string): void {
    const endpointIds: [string, string] = fromId <= toId ? [fromId, toId] : [toId, fromId];
    const next = { personId, endpointIds, acknowledged: true, updatedAt: new Date(this.now()).toISOString() };
    const index = this.acknowledgements.findIndex(
      (row) => row.personId === personId && row.endpointIds[0] === endpointIds[0] && row.endpointIds[1] === endpointIds[1],
    );
    if (index >= 0) this.acknowledgements[index] = next;
    else this.acknowledgements.push(next);
    this.saveDurable();
  }

  private dropAcknowledgement(personId: string, fromId: string, toId: string): void {
    const endpointIds: [string, string] = fromId <= toId ? [fromId, toId] : [toId, fromId];
    const index = this.acknowledgements.findIndex(
      (row) => row.personId === personId && row.endpointIds[0] === endpointIds[0] && row.endpointIds[1] === endpointIds[1],
    );
    if (index >= 0) this.acknowledgements.splice(index, 1);
  }

  private semanticInterest(input: ExploreInput, operation: string): SemanticInterest {
    return {
      personId: input.personId,
      purpose: input.purpose,
      authorizationEpoch: this.authorizationEpoch,
      snapshotRevision: this.projection.revision,
      snapshotDigest: this.projection.digest,
      budgets: { deadlineMs: this.judgeDeadlineMs, maxInFlight: this.maxInFlight },
      operation,
      nonce: input.requestId ?? "",
    };
  }

  private publishSelection(personId: string, issued: ReadonlyMap<string, string>): { revision: number; pruned: Array<{ id: string; reason: string }> } {
    const draft = this.selectionDraft;
    if (!draft || draft.personId !== personId) return { revision: 0, pruned: [] };
    const provenance = { ...draft.provenance };
    const exportHandles: string[] = [];
    for (const [handle, id] of issued) {
      exportHandles.push(handle);
      const row = provenance[id];
      if (row) provenance[id] = { ...row, exportHandle: handle };
    }
    const published = this.routeLog.publish({
      personId,
      sets: { candidate: draft.candidateIds, selected: draft.selectedIds, export: exportHandles },
      provenance,
    });
    return { revision: published.revision, pruned: draft.pruned };
  }

  private async judgeReferralRound(
    input: IngestInput,
    eventId: string,
    issued: Map<string, string>,
    judgments: IngestResult["judgments"],
  ): Promise<void> {
    const draft = this.selectionDraft;
    if (!draft) return;
    const judged = [];
    for (const [handle, id] of issued) {
      const row = judgments.find((item) => item.handle === handle);
      const candidate = draft.candidates.find((item) => item.id === id);
      if (!row || !candidate) continue;
      if (row.judgment !== "link" && row.judgment !== "no_link" && row.judgment !== "uncertain") continue;
      judged.push({ id, judgment: row.judgment, relevance: candidate.relevance, neighbors: candidate.neighbors });
    }
    const round = applyReferralRound({ judged, tried: [...issued.values()] });
    if (round.referrals.length === 0) return;
    const extra: JudgeRequest["candidates"] = [];
    const extraIssued = new Map<string, string>();
    for (const id of round.referrals) {
      const exported = this.exportNode(id, "referral");
      if (!exported) continue;
      extraIssued.set(exported.handle, id);
      extra.push({
        handle: exported.handle,
        excerpt: exported.excerpt,
        sourceType: exported.sourceType,
        capturedAt: exported.capturedAt,
      });
    }
    if (extra.length === 0) return;
    let decisions: JudgeDecision[];
    try {
      decisions = await this.judgeWithRetry({
        newHandle: "ch_new",
        excerpt: input.text.slice(0, 180),
        sourceType: input.sourceType,
        capturedAt: input.capturedAt,
        candidates: extra,
      });
    } catch {
      return;
    }
    for (const raw of decisions) {
      const decision = sanitizeDecision(raw);
      const otherId = extraIssued.get(decision.handle);
      if (!otherId) continue;
      const evidenceIds = [eventId, otherId];
      const confidence = this.capConfidence(eventId, otherId, clamp(decision.confidence), evidenceIds, "model");
      const ad = this.appendAd({
        personId: input.personId,
        origin: "model",
        modelVersion: MODEL_VERSION,
        promptVersion: "lab-prompt-1",
        policyVersion: this.policyVersion,
        evidenceIds,
        fromId: eventId,
        toId: otherId,
        judgment: decision.judgment,
        reasonCode: decision.reasonCode,
        relation: mapRelation("model", decision.reasonCode),
        proposedConfidence: clamp(decision.confidence),
        confidence,
        createdAt: input.capturedAt,
        supersedesId: this.projection.edgeBetween(eventId, otherId)?.adId ?? null,
        withdrawn: false,
      });
      this.projection.apply(ad);
      issued.set(decision.handle, otherId);
      judgments.push({ handle: decision.handle, judgment: decision.judgment, reasonCode: decision.reasonCode, accepted: true });
    }
  }

  private tokenMatches(personId: string, text: string, selfId: string): Set<string> {
    const tokens = new Set(tokenize(text));
    const matched = new Set<string>();
    for (const event of this.vault.list()) {
      if (event.personId !== personId || event.id === selfId) continue;
      if (tokenize(event.text).some((word) => tokens.has(word))) matched.add(event.id);
    }
    return matched;
  }

  private candidateNeighbors(personId: string, text: string, id: string, selfId: string): RankedCandidate["neighbors"] {
    const neighbors: Array<{ id: string; relevance: number }> = [];
    for (const neighbor of this.projection.neighbors(id)) {
      if (neighbor === selfId) continue;
      const node = this.nodes.get(neighbor);
      if (!node || node.personId !== personId) continue;
      const tags = this.controls.get(neighbor);
      if (tags?.has("no-model") || tags?.has("no-forward")) continue;
      neighbors.push({ id: neighbor, relevance: jaccard(text, this.vault.get(neighbor)?.text ?? "") });
    }
    return neighbors;
  }

  private discoveryOf(
    id: string,
    tokenIds: ReadonlySet<string>,
    neighborIds: ReadonlySet<string>,
    hnswIds: ReadonlySet<string>,
  ): DiscoverySource {
    if (tokenIds.has(id)) return "exact";
    if (hnswIds.has(id)) return "hnsw";
    if (neighborIds.has(id)) return "neighbor";
    return "exact";
  }

  private hydrate(): void {
    if (!this.graphStore) return;
    const snapshot = this.graphStore.load();
    if (snapshot.events.length === 0 && snapshot.advertisements.length === 0 && snapshot.nodes.length === 0) return;
    this.hydrating = true;
    try {
      for (const event of snapshot.events) {
        this.vault.append(event);
        this.indexFor(event.personId).add(event.id, tokenVector(event.text));
      }
      for (const node of snapshot.nodes) {
        this.nodes.set(node.id, { ...node, memberEventIds: [...node.memberEventIds] });
      }
      for (const event of snapshot.events) {
        if (!this.nodes.has(event.id)) this.nodes.set(event.id, emptyPointer(event));
      }
      this.log.restore(snapshot.advertisements);
      assertStructuralLedger(this.log.ads, [...this.nodes.values()]);
      this.projection.rebuild(this.log.ads);
      if (snapshot.projectionDigest && snapshot.projectionDigest !== this.projection.digest) {
        throw new Error("graph store snapshot is unreadable");
      }
      if (snapshot.projectionRevision !== undefined) this.projection.revision = snapshot.projectionRevision;
      this.acknowledgements.push(...snapshot.acknowledgements.map((row) => ({ ...row, endpointIds: [row.endpointIds[0], row.endpointIds[1]] as [string, string] })));
    } finally {
      this.hydrating = false;
    }
  }

  private saveDurable(): void {
    if (!this.graphStore || this.hydrating) return;
    const snapshot: DurableSnapshot = {
      events: this.vault.list(),
      advertisements: this.log.ads.map((ad) => ({ ...ad, evidenceIds: [...ad.evidenceIds] })),
      nodes: [...this.nodes.values()].map((node) => ({ ...node, memberEventIds: [...node.memberEventIds] })),
      acknowledgements: this.acknowledgements.map((row) => ({ ...row, endpointIds: [...row.endpointIds] })),
      projectionRevision: this.projection.revision,
      projectionDigest: this.projection.digest,
    };
    this.graphStore.save(snapshot);
  }

  private persistSession(record: HandleRecord): void {
    const body = { ...record, routeBindings: [...record.routeBindings.entries()] };
    this.sessionStore.put(record.token, JSON.parse(JSON.stringify(body)) as SessionJson);
  }

  private loadHandle(token: string): HandleRecord | undefined {
    const live = this.handles.get(token);
    if (live) return live;
    const stored = this.sessionStore.get(token);
    if (!stored) return undefined;
    const raw = stored as unknown as HandleRecord & { routeBindings?: [string, string[]][] };
    const record: HandleRecord = {
      ...raw,
      routeBindings: new Map(raw.routeBindings ?? []),
      frontier: raw.frontier ?? [],
      advertised: raw.advertised ?? [],
      visitedNodes: raw.visitedNodes ?? [],
      visitedEdges: raw.visitedEdges ?? [],
      breadcrumb: raw.breadcrumb ?? [],
    };
    this.handles.set(token, record);
    return record;
  }

  private personFor(fromId: string, toId: string): string {
    const personId = this.nodes.get(fromId)?.personId ?? this.nodes.get(toId)?.personId;
    if (!personId) throw new Error("advertisement endpoints have no person");
    return personId;
  }

  private appendAd(draft: AdvertisementDraft): LinkAdvertisement {
    return this.log.append(draft);
  }

  private indexFor(personId: string): HnswIndex {
    let index = this.indexes.get(personId);
    if (!index) {
      index = new HnswIndex(this.seed);
      this.indexes.set(personId, index);
    }
    return index;
  }

  private personCount(personId: string): number {
    let count = 0;
    for (const node of this.nodes.values()) {
      if (node.personId === personId && node.kind === "event") count += 1;
    }
    return count;
  }
}

function clamp(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.min(1, Math.max(0, value));
}
