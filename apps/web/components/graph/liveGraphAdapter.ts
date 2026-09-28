/*
 * Maps the person's real records onto the cockpit's GraphModel.
 *
 * Sources: /v1/threads (concerns), /v2/graph/threads/{id} (concepts, theories,
 * investigations and their links), /v2/threads/{id}/memories (facts backing a
 * concept via c6_kg_node refs), /v2/results (lab / vital observations),
 * /v2/patterns (plain-language caveats keyed by edge id), /v2/pending-items
 * (open loops) and /v2/investigations (external context refs).
 *
 * Nothing is invented: every node and edge comes from one of those payloads, and
 * a layer with no real data simply stays empty.
 */

import type { components } from "@wellbe/api-client";
import type { EvidenceSource, ReviewMarkerValue, SourceKind } from "@wellbe/ui";
import { formatShortDate } from "@/lib/adapters";
import { nodeTypeLabel, relationPhrase } from "@/lib/graph-labels";
import { describePendingItem, openPendingItems } from "@/lib/pending";
import type { ThreadSummary } from "@/lib/types";
import {
  CLUSTER_PALETTE,
  type Capture,
  type Cluster,
  type Family,
  type GraphEdge,
  type GraphModel,
  type GraphNode,
  type GraphTimeline,
  type LayerId,
  LIVE_NODE_ACTIONS,
  type NodeType,
  type SourceType,
} from "./graphData";

type Schemas = components["schemas"];
type ThreadSubgraphV2 = Schemas["ThreadSubgraphV2"];
type GraphNodeV2 = Schemas["GraphNodeV2"];
type GraphEdgeV2 = Schemas["GraphEdgeV2"];
type MemoryEntryV2 = Schemas["MemoryEntryV2"];
type PendingItemV2 = Schemas["PendingItemV2"];
type PatternCandidateV2 = Schemas["PatternCandidateV2"];
type InvestigationV2 = Schemas["InvestigationV2"];

/** The slice of /v2/results the graph needs (records-hooks normalizes the rest). */
export interface ResultAnalyte {
  display_label: string;
  kind: string;
  latest: ResultObservation;
  history?: ResultObservation[];
}
interface ResultObservation {
  value: string;
  unit?: string | null;
  range_note?: string;
  observed_at: string;
  source: { kind: string; display_label: string; capture_id?: string; document_id?: string | null; review_marker?: string };
}

export interface LiveGraphInput {
  threads: ThreadSummary[];
  /** Subgraphs aligned with `threads`; undefined when a thread's graph failed. */
  graphs: (ThreadSubgraphV2 | undefined)[];
  /** Memories aligned with `threads`. */
  memories?: (MemoryEntryV2[] | undefined)[];
  pending?: PendingItemV2[];
  patterns?: PatternCandidateV2[];
  results?: ResultAnalyte[];
  investigations?: InvestigationV2[];
}

const RAW_STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  active_unresolved: "Active",
  reopened: "Reopened",
  waiting_for_result: "Waiting for a result",
  referred: "Referred",
  watchful_waiting: "Watching",
  chronic_monitoring: "Monitoring",
  escalated: "Worth reviewing",
  explained: "Explained",
  closed: "Closed",
  archived: "Archived",
};

function clusterStatus(t: ThreadSummary): Cluster["status"] {
  if (t.status === "resolved" || t.status === "closed") return "resolved";
  if (t.status === "monitoring" || t.status === "paused") return "watch";
  return "active";
}

const NODE_KIND: Record<string, { type: NodeType; layer: LayerId }> = {
  Symptom: { type: "symptom", layer: "concept" },
  LabResult: { type: "lab", layer: "concept" },
  Lab: { type: "lab", layer: "concept" },
  Observation: { type: "lab", layer: "concept" },
  VitalSign: { type: "vital", layer: "concept" },
  Vital: { type: "vital", layer: "concept" },
  Encounter: { type: "visit", layer: "concept" },
  Document: { type: "capture", layer: "observation" },
  Theory: { type: "theory", layer: "investigation" },
  Investigation: { type: "investigation", layer: "investigation" },
  ExternalContext: { type: "external", layer: "external" },
  ExternalReference: { type: "external", layer: "external" },
};

function nodeKind(rawType: string): { type: NodeType; layer: LayerId } {
  return NODE_KIND[rawType] ?? { type: "context", layer: "concept" };
}

/** Display label: sentence-case the first letter ("cough" → "Cough"). */
export function displayLabel(label: string): string {
  const t = label.trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : "Unnamed item";
}

function attr(n: { attributes?: Record<string, unknown> }, key: string): unknown {
  return n.attributes?.[key];
}

function iso(v: unknown): string | undefined {
  return typeof v === "string" && !Number.isNaN(new Date(v).getTime()) ? v : undefined;
}

/**
 * Link strength on the cockpit's 1..7 score scale. evidence_weight is 0..1:
 * 0.9 → 6 (strong), 0.6 → 4, 0.3 → 2 (candidate, below the default floor).
 */
export function weightToScore(weight: number): number {
  if (!Number.isFinite(weight)) return 1;
  return Math.min(7, Math.max(1, Math.round(weight * 7)));
}

const TIME_RELATIONS = new Set(["temporally_near", "precedes", "follows", "temporal"]);
const CARE_RELATIONS = new Set(["part_of", "measured_by", "ordered_for", "result_of", "treated_with", "referred_for"]);
const SOURCE_RELATIONS = new Set(["documented_as", "stated_in", "source_states"]);

function isUserAuthored(e: GraphEdgeV2): boolean {
  const a = e.attributes ?? {};
  return a.origin === "user" || a.authored_by === "user" || a.user_confirmed === true;
}

function edgeFamily(
  e: GraphEdgeV2,
  score: number,
  pattern: PatternCandidateV2 | undefined,
  kinds: [NodeType, NodeType],
): { f: Family; layer: LayerId } {
  if (kinds.includes("external")) return { f: "relevance", layer: "external" };
  if (e.relation === "contradicts" || pattern?.is_contradiction) return { f: "conflict", layer: "concept" };
  if (isUserAuthored(e)) return { f: "user", layer: "correction" };
  if (e.relation === "investigates" || kinds.includes("theory") || kinds.includes("investigation")) {
    return { f: "hypothesis", layer: "investigation" };
  }
  if (TIME_RELATIONS.has(e.relation)) return { f: "time", layer: "concept" };
  if (CARE_RELATIONS.has(e.relation)) return { f: "care", layer: "concept" };
  if (SOURCE_RELATIONS.has(e.relation)) return { f: "source", layer: "concept" };
  const early = pattern ? pattern.evidence_tier === "early_signal" : score <= 3;
  return { f: early ? "cand" : "co", layer: "concept" };
}

function recordSourceKind(kind: string): SourceKind {
  if (kind === "document" || kind === "uploaded_document") return "doc";
  if (kind === "wearable" || kind === "device") return "wearable";
  if (kind === "clinician" || kind === "clinical_note") return "note";
  return "reported";
}

const REVIEW_VALUES = new Set<ReviewMarkerValue>([
  "patient-entered",
  "AI-summarized",
  "not-clinician-reviewed",
  "clinician-reviewed",
  "clinician-annotated",
  "ready-for-visit",
]);

function toCapture(s: EvidenceSource): Capture {
  const d = s.date ? formatShortDate(String(s.date)) : "";
  return { source: (s.kind ?? "reported") as SourceType, text: s.excerpt ?? s.displayLabel, date: d };
}

/**
 * Replay buckets over the real first-noted dates. One bucket when everything was
 * first noted the same day (the slider then collapses to a calm single-date note).
 */
export function buildTimeline(dates: string[]): GraphTimeline & { bucketOf: (d: string | undefined) => number } {
  const times = dates.map((d) => new Date(d).getTime()).filter((t) => Number.isFinite(t));
  const dayKey = (t: number) => new Date(t).toISOString().slice(0, 10);
  const days = new Set(times.map(dayKey));
  const long = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric", timeZone: "UTC" });
  if (days.size <= 1) {
    const only = times[0];
    const label = only === undefined ? "Now" : formatShortDate(new Date(only).toISOString());
    return {
      labels: [label],
      valueTexts: [only === undefined ? "Everything so far" : `Everything, first noted ${long.format(only)}`],
      bucketOf: () => 0,
    };
  }
  const min = Math.min(...times);
  const max = Math.max(...times);
  const span = max - min;
  const n = Math.min(6, days.size);
  const DAY = 86_400_000;
  const tick = new Intl.DateTimeFormat("en-US", span > 180 * DAY
    ? { month: "short", year: "2-digit", timeZone: "UTC" }
    : { month: "short", day: "numeric", timeZone: "UTC" });
  const labels: string[] = [];
  const valueTexts: string[] = [];
  for (let i = 0; i < n; i++) {
    const end = min + (span * (i + 1)) / n;
    labels.push(tick.format(end));
    valueTexts.push(i === n - 1 ? "Now, everything so far" : `As of ${long.format(end)}`);
  }
  return {
    labels,
    valueTexts,
    bucketOf: (d) => {
      const t = d ? new Date(d).getTime() : NaN;
      if (!Number.isFinite(t)) return 0;
      return Math.min(n - 1, Math.max(0, Math.floor(((t - min) / span) * n)));
    },
  };
}

function dedupeSources(list: EvidenceSource[]): EvidenceSource[] {
  const seen = new Set<string>();
  return list.filter((s) => (seen.has(s.id) ? false : (seen.add(s.id), true)));
}

export function buildLiveGraph(input: LiveGraphInput): GraphModel {
  const { threads, graphs } = input;
  const threadIds = new Set(threads.map((t) => t.id));
  const threadTitle = new Map(threads.map((t) => [t.id, t.title]));

  const clusters: Cluster[] = threads.map((t, i) => ({
    id: t.id,
    label: t.title,
    cx: 0,
    cy: 0,
    rx: 0,
    ry: 0,
    status: clusterStatus(t),
    statusLabel: RAW_STATUS_LABEL[t.rawStatus] ?? RAW_STATUS_LABEL[t.status] ?? "Active",
    href: `/threads/${t.id}`,
    ...CLUSTER_PALETTE[i % CLUSTER_PALETTE.length]!,
  }));

  // Deduplicate nodes across thread subgraphs; `in_thread` is the real membership.
  const raw = new Map<string, { node: GraphNodeV2; inThreads: string[] }>();
  const rawEdges = new Map<string, GraphEdgeV2>();
  graphs.forEach((g, i) => {
    const tid = threads[i]?.id;
    if (!g || !tid) return;
    for (const n of g.nodes ?? []) {
      const entry = raw.get(n.id) ?? { node: n, inThreads: [] };
      const inThread = attr(n, "in_thread");
      if (inThread !== false && !entry.inThreads.includes(tid)) entry.inThreads.push(tid);
      raw.set(n.id, entry);
    }
    for (const e of g.edges ?? []) rawEdges.set(e.id, e);
  });

  // Evidence per concept: C4 facts behind memories that cite the node, and
  // result observations whose analyte matches a lab / vital node.
  const factsByNode = new Map<string, EvidenceSource[]>();
  (input.memories ?? []).forEach((list, i) => {
    const tid = threads[i]?.id;
    for (const m of list ?? []) {
      const refs = (m.source_refs ?? []) as { source_ref_type?: unknown; source_ref_id?: unknown }[];
      const nodeIds = refs.filter((r) => r.source_ref_type === "c6_kg_node").map((r) => String(r.source_ref_id));
      if (!nodeIds.length) continue;
      const facts: EvidenceSource[] = refs
        .filter((r) => r.source_ref_type === "c4_extracted_fact" && typeof r.source_ref_id === "string")
        .map((r) => ({
          id: `fact:${String(r.source_ref_id)}`,
          displayLabel: "Fact from what you added",
          component: "c5",
          kind: "reported",
          date: m.created_at ?? undefined,
          excerpt: tid ? `Kept in your “${threadTitle.get(tid) ?? m.title}” memory.` : undefined,
        }));
      for (const nid of nodeIds) factsByNode.set(nid, [...(factsByNode.get(nid) ?? []), ...facts]);
    }
  });
  const resultsByLabel = new Map<string, EvidenceSource[]>();
  for (const a of input.results ?? []) {
    const obs = a.history?.length ? a.history : [a.latest];
    resultsByLabel.set(
      a.display_label.trim().toLowerCase(),
      obs.map((o, i) => ({
        id: `result:${o.source.capture_id ?? o.source.document_id ?? `${a.display_label}-${i}`}:${o.observed_at}`,
        displayLabel: o.source.display_label,
        component: "c2",
        kind: a.kind === "lab" ? "lab" : recordSourceKind(o.source.kind),
        date: o.observed_at,
        excerpt: [`${a.display_label}: ${o.value}${o.unit ? ` ${o.unit}` : ""}`, o.range_note].filter(Boolean).join(" · "),
        reviewMarkers: REVIEW_VALUES.has(o.source.review_marker as ReviewMarkerValue)
          ? [o.source.review_marker as ReviewMarkerValue]
          : undefined,
      })),
    );
  }

  const pending = openPendingItems(input.pending ?? []);
  const timeline = buildTimeline([
    ...Array.from(raw.values()).map(({ node }) => iso(attr(node, "first_seen_at"))).filter((d): d is string => Boolean(d)),
    ...pending.map((p) => p.created_at),
  ]);

  const lastTimes = Array.from(raw.values())
    .map(({ node }) => new Date(iso(attr(node, "last_seen_at")) ?? "").getTime())
    .filter(Number.isFinite);
  const newest = lastTimes.length ? Math.max(...lastTimes) : 0;
  const oldest = lastTimes.length ? Math.min(...lastTimes) : 0;

  const nodes: GraphNode[] = [];
  for (const { node, inThreads } of raw.values()) {
    const { type, layer } = nodeKind(node.type);
    const members = inThreads.filter((t) => threadIds.has(t));
    const first = iso(attr(node, "first_seen_at"));
    const last = iso(attr(node, "last_seen_at")) ?? first;
    const lastT = last ? new Date(last).getTime() : oldest;
    const evidence = dedupeSources([
      ...(factsByNode.get(node.id) ?? []),
      ...(type === "lab" || type === "vital" ? resultsByLabel.get(node.label.trim().toLowerCase()) ?? [] : []),
    ]);
    const investigative = type === "theory" || type === "investigation";
    nodes.push({
      id: node.id,
      label: displayLabel(node.label),
      x: 0,
      y: 0,
      ev: evidence.length,
      conf: Math.min(5, evidence.length),
      act: newest > oldest ? 0.6 + (0.4 * (lastT - oldest)) / (newest - oldest) : 1,
      primary: members.length > 0,
      type,
      typeLabel: nodeTypeLabel(node.type),
      layer,
      first: first ? formatShortDate(first) : "—",
      last: last ? formatShortDate(last) : "—",
      week: timeline.bucketOf(first),
      relatedTotal: 0,
      sources: Array.from(new Set(evidence.map((s) => (s.kind ?? "reported") as SourceType))),
      evidence,
      captures: evidence.length ? evidence.map(toCapture) : undefined,
      cluster: members[0],
      bridge: members.length >= 2 ? members : undefined,
      lensRole: investigative ? "theory" : undefined,
    });
  }

  for (const p of pending) {
    const tid = p.primary_thread_id && threadIds.has(p.primary_thread_id) ? p.primary_thread_id : undefined;
    const due = describePendingItem(p);
    nodes.push({
      id: `pending:${p.pending_item_id}`,
      label: p.title,
      x: 0,
      y: 0,
      ev: 0,
      conf: 0,
      act: 1,
      primary: true,
      type: "pending",
      typeLabel: "Open loop",
      layer: "continuity",
      first: formatShortDate(p.created_at) || "—",
      last: due.label,
      week: timeline.bucketOf(p.created_at),
      relatedTotal: 0,
      sources: [],
      evidence: [],
      cluster: tid,
      ghost: true,
      statusNote: due.label,
    });
  }

  // External context: only real refs on investigations, attached to the
  // investigation node that asks the same question.
  const edges: GraphEdge[] = [];
  const byId = new Map(nodes.map((n) => [n.id, n]));
  for (const inv of input.investigations ?? []) {
    const refs = inv.external_context_refs ?? [];
    if (!refs.length) continue;
    const anchor = nodes.find((n) => n.type === "investigation" && n.label === displayLabel(inv.primary_question));
    const members = inv.health_thread_ids.filter((t) => threadIds.has(t));
    const evidence: EvidenceSource[] = refs.map((r) => ({ id: `ext:${r}`, displayLabel: "", component: "c16", kind: "research" }));
    const ext: GraphNode = {
      id: `external:${inv.investigation_id}`,
      label: refs.length === 1 ? "External context" : `External context (${refs.length})`,
      x: 0,
      y: 0,
      ev: refs.length,
      conf: 0,
      act: 0.6,
      primary: false,
      type: "external",
      typeLabel: "External context",
      layer: "external",
      first: formatShortDate(inv.created_at) || "—",
      last: formatShortDate(inv.updated_at) || "—",
      week: timeline.bucketOf(inv.created_at),
      relatedTotal: anchor ? 1 : 0,
      sources: ["research"],
      evidence,
      cluster: members[0],
    };
    nodes.push(ext);
    byId.set(ext.id, ext);
    if (anchor) edges.push({ id: `rel:${inv.investigation_id}`, a: ext.id, b: anchor.id, s: 2, f: "relevance", layer: "external", week: ext.week, phrase: "gives context for" });
  }

  const patternById = new Map((input.patterns ?? []).map((p) => [p.id, p]));
  for (const e of rawEdges.values()) {
    const a = byId.get(e.source);
    const b = byId.get(e.target);
    if (!a || !b || a.id === b.id) continue;
    const pattern = patternById.get(e.id);
    const s = weightToScore(e.evidence_weight);
    const { f, layer } = edgeFamily(e, s, pattern, [a.type, b.type]);
    const refId = e.attributes?.source_ref_id;
    edges.push({
      id: e.id,
      a: a.id,
      b: b.id,
      s,
      f,
      layer,
      week: Math.max(a.week, b.week),
      phrase: pattern?.relation_phrase ?? relationPhrase(e.relation),
      note: pattern?.caveat,
      alternatives: pattern?.alternative_explanations?.length ? pattern.alternative_explanations : undefined,
      confounder: pattern?.confounder_note ?? undefined,
      evidence: dedupeSources([
        ...(typeof refId === "string" ? [{ id: `edge-src:${refId}`, displayLabel: "Linked source", component: "c5" as const }] : []),
        ...(a.evidence ?? []),
        ...(b.evidence ?? []),
      ]),
    });
  }

  const degree = new Map<string, number>();
  for (const e of edges) {
    degree.set(e.a, (degree.get(e.a) ?? 0) + 1);
    degree.set(e.b, (degree.get(e.b) ?? 0) + 1);
  }
  for (const n of nodes) n.relatedTotal = degree.get(n.id) ?? 0;

  return {
    kind: "live",
    clusters,
    nodes,
    edges,
    timeline: { labels: timeline.labels, valueTexts: timeline.valueTexts },
    autoLayout: true,
    comparisonAvailable: false,
    canAuthorLinks: false,
    actions: LIVE_NODE_ACTIONS,
  };
}

/** Which layers actually carry data — empty ones get a calm note, not fixtures. */
export function layersWithData(model: GraphModel): Record<LayerId, boolean> {
  const has = (l: LayerId) => model.nodes.some((n) => n.layer === l) || model.edges.some((e) => e.layer === l);
  return {
    observation: model.nodes.some((n) => (n.captures?.length ?? 0) > 0) || has("observation"),
    concept: has("concept"),
    thread: model.clusters.length > 0,
    continuity: has("continuity"),
    correction: has("correction"),
    investigation: has("investigation"),
    external: has("external"),
  };
}
