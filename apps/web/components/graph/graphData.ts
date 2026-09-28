/*
 * Whole-person graph — full-vision data model (WEL-78, Approach C).
 * Spec: docs/implementation/ui/graph-view-system-design.md
 *
 * `GraphModel` is what the cockpit (GraphLive) renders. The live graph builds one
 * from the person's real records (liveGraphAdapter.ts); the SEED_* fixtures below
 * only feed the explicitly labelled design preview (/graph?preview=design).
 * Encodes every UI-surfaceable detail in the doc: 7 layers (XV.8), the full
 * relationship vocabulary (XV.3), investigation/theory + external context
 * (Part V.3/VIII), a Replay timeline (V.1), comparison suggestions (V.4), and
 * capture children for on-canvas expansion (III.5).
 */

import type { EvidenceSource } from "@wellbe/ui";

export type ClusterId = string;

export interface ClusterHue {
  hue: string;
  dark: string;
}

/** Concern palette: the original three cockpit hues first, then calm extensions. */
export const CLUSTER_PALETTE: ClusterHue[] = [
  { hue: "#0ea5a4", dark: "#0a5a59" },
  { hue: "#8b5cf6", dark: "#6d28d9" },
  { hue: "#f59e0b", dark: "#b45309" },
  { hue: "#0284c7", dark: "#075985" },
  { hue: "#db2777", dark: "#9d174d" },
  { hue: "#16a34a", dark: "#166534" },
];
export const NEUTRAL_HUE: ClusterHue = { hue: "#64748b", dark: "#334155" };
export const THEORY_HUE: ClusterHue = { hue: "#8b5cf6", dark: "#6d28d9" };

export interface Cluster extends ClusterHue {
  id: ClusterId;
  label: string;
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  status: "active" | "watch" | "resolved";
  /** Plain-language status shown on the card; defaults from `status`. */
  statusLabel?: string;
  /** Where the concern itself lives (thread page). */
  href?: string;
  /** Label anchor when the layout placed it; defaults to the top of the halo. */
  labelX?: number;
  labelY?: number;
}

export type NodeType =
  | "symptom"
  | "context"
  | "pending"
  | "lab"
  | "vital"
  | "visit"
  | "capture"
  | "theory"
  | "investigation"
  | "external";
// XV.8 layered model
export type LayerId = "observation" | "concept" | "thread" | "continuity" | "correction" | "investigation" | "external";
export type SourceType = "lab" | "note" | "doc" | "wearable" | "reported" | "research";

export interface Capture {
  source: SourceType;
  text: string;
  date: string;
}

export interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  ev: number;
  conf: number;
  act: number;
  primary: boolean;
  type: NodeType;
  /** Exact plain-language type (e.g. "Vital sign"); falls back to TYPE_LABEL. */
  typeLabel?: string;
  layer: LayerId;
  first: string;
  last: string;
  week: number; // Replay bucket: when it entered the records (V.1)
  relatedTotal: number;
  pinned?: boolean;
  sources: SourceType[];
  captures?: Capture[];
  /** Backing sources shown as SourceMarkers and in the EvidenceDrawer. */
  evidence?: EvidenceSource[];
  cluster?: ClusterId;
  bridge?: ClusterId[]; // a concept shared by ≥2 concerns — rendered as an N-wedge pie
  ghost?: boolean;
  /** Calm due-state line for an open loop ("Check back Oct 4"). */
  statusNote?: string;
  aggregate?: boolean; // comparison overlay suggestion (V.4)
  lensRole?: "theory"; // investigation/theory node (V.3)
  anchor?: string; // deferred child: revealed only when its anchor is expanded (III.5)
  deferred?: boolean;
}

// XV.3 relationship vocabulary — raw C6 edge types are never shown.
export type Family = "co" | "time" | "care" | "cand" | "user" | "conflict" | "source" | "hypothesis" | "relevance";

export interface GraphEdge {
  id?: string;
  a: string;
  b: string;
  s: number; // score_level 1..7 (evidence strength)
  f: Family;
  layer: LayerId;
  week: number;
  lens?: "for" | "against"; // investigation lens (V.3)
  disputed?: boolean; // IV.6
  /** Plain relation phrase ("appears with"), never the raw code. */
  phrase?: string;
  /** Server-composed caveat for this link (patterns). */
  note?: string;
  alternatives?: string[];
  confounder?: string;
  evidence?: EvidenceSource[];
}

export interface NodeAction {
  id: string;
  icon: string;
  label: string;
}

export interface GraphTimeline {
  /** Short tick labels, oldest first. The last bucket is "now". */
  labels: string[];
  /** Screen-reader value text per bucket. */
  valueTexts: string[];
}

export interface GraphModel {
  kind: "live" | "preview";
  clusters: Cluster[];
  nodes: GraphNode[];
  edges: GraphEdge[];
  timeline: GraphTimeline;
  /** Positions come from the auto layout rather than the model. */
  autoLayout: boolean;
  /** Opt-in aggregate comparison data exists. */
  comparisonAvailable: boolean;
  /** Links drawn on the map are kept (preview only — the live API has no user-edge write yet). */
  canAuthorLinks: boolean;
  actions: NodeAction[];
}

export const FAMILY: Record<Family, { label: string; note: string; tone: "tealmid" | "violet" | "neutral" | "amber" }> = {
  co: { label: "Recorded together", note: "These appeared in the same capture, document, or visit in your records.", tone: "tealmid" },
  time: { label: "Around the same time", note: "These were noted close together in time. This is chronology, not cause.", tone: "tealmid" },
  care: { label: "Part of the same care step", note: "These belong to the same lab, referral, result, or visit in your care.", tone: "tealmid" },
  cand: { label: "System candidate", note: "WellBe noticed these appeared together in your records. Hidden by default until you confirm.", tone: "neutral" },
  user: { label: "You linked these", note: "You added this connection yourself. It's kept separate from source evidence.", tone: "violet" },
  conflict: { label: "Conflicting information", note: "Two of your sources disagree here. WellBe keeps both — it doesn't pick a winner.", tone: "amber" },
  source: { label: "A source you uploaded says", note: "A document or note you uploaded states this relationship directly.", tone: "tealmid" },
  hypothesis: { label: "Investigation-only hypothesis", note: "A working idea inside an investigation. Visible only in the lens — never a conclusion.", tone: "violet" },
  relevance: { label: "Related external context", note: "External context linked for relevance only. Kept separate from your personal records.", tone: "neutral" },
};

export const TYPE_LABEL: Record<NodeType, string> = {
  symptom: "Symptom",
  context: "Personal context",
  pending: "Open loop",
  lab: "Lab result",
  vital: "Vital sign",
  visit: "Visit",
  capture: "Capture",
  theory: "Working theory",
  investigation: "Investigation",
  external: "External context",
};
export const TYPE_ICON: Record<NodeType, string> = {
  symptom: "activity",
  context: "circle-user",
  pending: "clock",
  lab: "flask-conical",
  vital: "heart-pulse",
  visit: "calendar",
  capture: "file-text",
  theory: "flask-conical",
  investigation: "search",
  external: "globe",
};

export const LAYERS: Array<{ id: LayerId; label: string; icon: string; defaultOn: boolean }> = [
  { id: "observation", label: "Observations", icon: "file-text", defaultOn: true },
  { id: "concept", label: "Concepts", icon: "git-fork", defaultOn: true },
  { id: "thread", label: "Concerns", icon: "circles", defaultOn: true },
  { id: "continuity", label: "Open loops", icon: "clock", defaultOn: true },
  { id: "correction", label: "Your links", icon: "pencil", defaultOn: false },
  { id: "investigation", label: "Investigation", icon: "flask-conical", defaultOn: false },
  { id: "external", label: "External", icon: "globe", defaultOn: false },
];

export const FLOOR_LABEL: Record<number, string> = {
  1: "Exploratory links",
  2: "Exploratory links",
  3: "More links",
  4: "More links",
  5: "Only source-backed",
  6: "Only strongest",
};

export const NODE_ACTIONS: NodeAction[] = [
  { id: "ask", icon: "message-circle", label: "Ask about this" },
  { id: "capture", icon: "plus", label: "Add a capture" },
  { id: "resolve", icon: "check-circle-2", label: "Mark resolved" },
  { id: "correct", icon: "pencil", label: "Correct this" },
  { id: "link", icon: "git-fork", label: "Link to…" },
  { id: "packet", icon: "folder", label: "Add to visit packet" },
  { id: "hide", icon: "eye", label: "Hide" },
];

/** Actions that do something real on the live graph (no local-only fakes). */
export const LIVE_NODE_ACTIONS: NodeAction[] = [
  { id: "ask", icon: "message-circle", label: "Ask about this" },
  { id: "open", icon: "arrow-right", label: "Open concern" },
  { id: "packet", icon: "folder", label: "Add to visit packet" },
  { id: "hide", icon: "eye", label: "Hide from map" },
];

export function sourceLabel(s: SourceType): string {
  return ({ lab: "lab result", note: "clinical note", doc: "document", wearable: "wearable reading", reported: "self-report", research: "reference" } as Record<SourceType, string>)[s];
}

/* ------------------------------------------------------------------------- */
/* Design-preview fixtures — sample data, never the person's records.          */
/* ------------------------------------------------------------------------- */

// Months → bucket index for the Replay timeline. Jan'26=0 … Jun'26=5.
export const WEEK_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"];

export const SEED_CLUSTERS: Cluster[] = [
  { id: "head", label: "Headaches", cx: 240, cy: 250, rx: 188, ry: 158, status: "active", ...CLUSTER_PALETTE[0]! },
  { id: "sleep", label: "Sleep", cx: 612, cy: 168, rx: 158, ry: 140, status: "active", ...CLUSTER_PALETTE[1]! },
  { id: "dig", label: "Digestive", cx: 452, cy: 470, rx: 170, ry: 104, status: "watch", ...CLUSTER_PALETTE[2]! },
];

export const SEED_NODES: GraphNode[] = [
  { id: "headache", label: "Headache", cluster: "head", x: 232, y: 244, ev: 14, conf: 5, act: 1, primary: true, pinned: true, type: "symptom", layer: "concept", first: "Feb 2026", last: "5 days ago", week: 1, relatedTotal: 31, sources: ["reported", "note", "doc"], captures: [
    { source: "reported", text: "“Throbbing headache again this afternoon, behind the eyes.”", date: "Jun 14" },
    { source: "note", text: "GP note: recurrent cephalalgia, review in 6 weeks.", date: "May 30" },
    { source: "doc", text: "Neurology triage form — headache diary attached.", date: "May 12" },
    { source: "reported", text: "“Headache worse on screen-heavy days.”", date: "Apr 28" },
    { source: "wearable", text: "Elevated heart-rate logged during reported headache.", date: "Apr 20" },
  ] },
  { id: "light", label: "Light sensitivity", cluster: "head", x: 80, y: 172, ev: 6, conf: 4, act: 0.8, primary: false, type: "symptom", layer: "concept", first: "Mar 2026", last: "3 wks ago", week: 2, relatedTotal: 9, sources: ["reported", "note"] },
  { id: "screen", label: "Screen time", cluster: "head", x: 96, y: 356, ev: 5, conf: 3, act: 0.7, primary: false, type: "context", layer: "concept", first: "Mar 2026", last: "2 wks ago", week: 2, relatedTotal: 7, sources: ["wearable", "reported"] },
  { id: "neck", label: "Neck tension", cluster: "head", x: 300, y: 120, ev: 4, conf: 3, act: 0.6, primary: false, type: "symptom", layer: "concept", first: "Apr 2026", last: "4 wks ago", week: 3, relatedTotal: 5, sources: ["reported"] },
  { id: "mri", label: "MRI referral", cluster: "head", x: 206, y: 402, ev: 1, conf: 2, act: 0.9, primary: true, ghost: true, type: "pending", layer: "continuity", first: "May 2026", last: "awaiting result", week: 4, relatedTotal: 2, sources: ["note"] },
  { id: "dizzy", label: "Dizziness", bridge: ["head", "sleep"], x: 452, y: 232, ev: 8, conf: 4, act: 0.95, primary: true, type: "symptom", layer: "concept", first: "Feb 2026", last: "1 wk ago", week: 1, relatedTotal: 18, sources: ["reported", "note"] },
  { id: "sleep", label: "Poor sleep", cluster: "sleep", x: 612, y: 160, ev: 11, conf: 5, act: 1, primary: true, type: "symptom", layer: "concept", first: "Jan 2026", last: "4 days ago", week: 0, relatedTotal: 24, sources: ["wearable", "reported", "note"], captures: [
    { source: "wearable", text: "Sleep tracker: 5h12m, 3 awakenings.", date: "Jun 15" },
    { source: "reported", text: "“Couldn't fall asleep again, mind racing.”", date: "Jun 10" },
    { source: "note", text: "GP note: sleep hygiene discussed.", date: "May 2" },
  ] },
  { id: "caffeine", label: "Late caffeine", cluster: "sleep", x: 728, y: 96, ev: 5, conf: 3, act: 0.6, primary: false, type: "context", layer: "concept", first: "Feb 2026", last: "3 wks ago", week: 1, relatedTotal: 6, sources: ["reported"] },
  { id: "fatigue", label: "Morning fatigue", cluster: "sleep", x: 692, y: 268, ev: 7, conf: 4, act: 0.85, primary: false, type: "symptom", layer: "concept", first: "Jan 2026", last: "6 days ago", week: 0, relatedTotal: 12, sources: ["wearable", "reported"] },
  { id: "sleepstudy", label: "Sleep study", cluster: "sleep", x: 556, y: 300, ev: 1, conf: 2, act: 0.8, primary: false, ghost: true, type: "pending", layer: "continuity", first: "May 2026", last: "not yet booked", week: 4, relatedTotal: 1, sources: ["note"] },
  { id: "nausea", label: "Nausea", cluster: "dig", x: 452, y: 462, ev: 5, conf: 3, act: 0.7, primary: true, type: "symptom", layer: "concept", first: "Mar 2026", last: "2 wks ago", week: 2, relatedTotal: 10, sources: ["reported", "note"] },
  { id: "diet", label: "Diet change", cluster: "dig", x: 332, y: 502, ev: 3, conf: 2, act: 0.5, primary: false, type: "context", layer: "concept", first: "Apr 2026", last: "5 wks ago", week: 3, relatedTotal: 4, sources: ["reported"] },
  { id: "bloods", label: "Blood panel", cluster: "dig", x: 562, y: 506, ev: 2, conf: 4, act: 0.55, primary: false, type: "lab", layer: "concept", first: "Apr 2026", last: "6 wks ago", week: 3, relatedTotal: 3, sources: ["lab"] },
  // investigation / theory (V.3) — investigation layer, off by default
  { id: "theory", label: "Tension-pattern theory", x: 360, y: 360, ev: 0, conf: 0, act: 0.9, primary: false, type: "theory", layer: "investigation", first: "May 2026", last: "exploring", week: 4, relatedTotal: 4, sources: ["note"], lensRole: "theory" },
  // external context (VIII / V) — external layer, off by default, relevance_link only
  { id: "airquality", label: "Air-quality alert", x: 40, y: 270, ev: 1, conf: 0, act: 0.5, primary: false, type: "external", layer: "external", first: "Apr 2026", last: "context", week: 3, relatedTotal: 1, sources: ["research"] },
  // comparison overlay suggestions (V.4) — aggregate, opt-in, off by default
  { id: "cmp-hydration", label: "Hydration", x: 150, y: 470, ev: 0, conf: 0, act: 0.4, primary: false, type: "context", layer: "concept", first: "—", last: "aggregate", week: 5, relatedTotal: 0, sources: [], aggregate: true },
  { id: "cmp-eyestrain", label: "Eye strain", x: 360, y: 60, ev: 0, conf: 0, act: 0.4, primary: false, type: "symptom", layer: "concept", first: "—", last: "aggregate", week: 5, relatedTotal: 0, sources: [], aggregate: true },
  // deferred child concepts (III.5) — hidden until their anchor node is expanded
  { id: "weightlog", label: "Weight log", anchor: "diet", x: 332, y: 502, ev: 4, conf: 3, act: 0.5, primary: false, deferred: true, type: "context", layer: "concept", first: "Apr 2026", last: "1 wk ago", week: 3, relatedTotal: 3, sources: ["wearable"] },
  { id: "triggerfoods", label: "Trigger foods", anchor: "diet", x: 332, y: 502, ev: 3, conf: 2, act: 0.45, primary: false, deferred: true, type: "context", layer: "concept", first: "Apr 2026", last: "3 wks ago", week: 3, relatedTotal: 2, sources: ["reported"] },
  { id: "elimination", label: "Elimination diet", anchor: "diet", x: 332, y: 502, ev: 2, conf: 2, act: 0.4, primary: false, deferred: true, type: "context", layer: "concept", first: "May 2026", last: "2 wks ago", week: 4, relatedTotal: 1, sources: ["reported"] },
  { id: "appetite", label: "Appetite change", anchor: "nausea", x: 452, y: 462, ev: 3, conf: 3, act: 0.5, primary: false, deferred: true, type: "symptom", layer: "concept", first: "Mar 2026", last: "2 wks ago", week: 2, relatedTotal: 2, sources: ["reported"] },
  { id: "energydips", label: "Energy dips", anchor: "fatigue", x: 692, y: 268, ev: 4, conf: 3, act: 0.55, primary: false, deferred: true, type: "symptom", layer: "concept", first: "Feb 2026", last: "1 wk ago", week: 1, relatedTotal: 3, sources: ["wearable", "reported"] },
  { id: "glare", label: "Glare sensitivity", anchor: "light", x: 80, y: 172, ev: 3, conf: 3, act: 0.5, primary: false, deferred: true, type: "symptom", layer: "concept", first: "Mar 2026", last: "4 wks ago", week: 2, relatedTotal: 2, sources: ["reported"] },
];

export const SEED_EDGES: GraphEdge[] = [
  { a: "headache", b: "light", s: 6, f: "co", layer: "concept", week: 2 },
  { a: "headache", b: "neck", s: 5, f: "time", layer: "concept", week: 3 },
  { a: "headache", b: "screen", s: 4, f: "cand", layer: "concept", week: 2 },
  { a: "headache", b: "dizzy", s: 5, f: "co", layer: "concept", week: 1 },
  { a: "headache", b: "mri", s: 7, f: "care", layer: "continuity", week: 4 },
  { a: "headache", b: "sleep", s: 3, f: "cand", layer: "concept", week: 2 },
  { a: "headache", b: "fatigue", s: 2, f: "cand", layer: "concept", week: 2 },
  { a: "light", b: "screen", s: 4, f: "source", layer: "concept", week: 2 }, // "a source you uploaded says"
  { a: "dizzy", b: "sleep", s: 4, f: "time", layer: "concept", week: 1 },
  { a: "dizzy", b: "nausea", s: 3, f: "cand", layer: "concept", week: 2 },
  { a: "sleep", b: "caffeine", s: 6, f: "co", layer: "concept", week: 1 },
  { a: "sleep", b: "fatigue", s: 6, f: "co", layer: "concept", week: 0 },
  { a: "sleep", b: "sleepstudy", s: 5, f: "care", layer: "continuity", week: 4 },
  { a: "caffeine", b: "fatigue", s: 3, f: "conflict", layer: "concept", week: 2 },
  { a: "nausea", b: "diet", s: 5, f: "user", layer: "correction", week: 3 },
  { a: "nausea", b: "bloods", s: 5, f: "care", layer: "concept", week: 3 },
  // investigation lens edges (V.3)
  { a: "theory", b: "neck", s: 4, f: "hypothesis", layer: "investigation", week: 4, lens: "for" },
  { a: "theory", b: "screen", s: 3, f: "hypothesis", layer: "investigation", week: 4, lens: "for" },
  { a: "theory", b: "light", s: 3, f: "hypothesis", layer: "investigation", week: 4, lens: "against" },
  { a: "theory", b: "headache", s: 4, f: "hypothesis", layer: "investigation", week: 4, lens: "for" },
  // external relevance (relevance_link only)
  { a: "airquality", b: "headache", s: 2, f: "relevance", layer: "external", week: 3 },
  // comparison suggestions (aggregate, opt-in)
  { a: "cmp-hydration", b: "headache", s: 2, f: "cand", layer: "concept", week: 5 },
  { a: "cmp-eyestrain", b: "headache", s: 2, f: "cand", layer: "concept", week: 5 },
  // deferred child edges (revealed with their anchor)
  { a: "diet", b: "weightlog", s: 5, f: "co", layer: "concept", week: 3 },
  { a: "diet", b: "triggerfoods", s: 4, f: "cand", layer: "concept", week: 3 },
  { a: "diet", b: "elimination", s: 4, f: "co", layer: "concept", week: 4 },
  { a: "nausea", b: "appetite", s: 5, f: "co", layer: "concept", week: 2 },
  { a: "fatigue", b: "energydips", s: 5, f: "co", layer: "concept", week: 1 },
  { a: "light", b: "glare", s: 5, f: "co", layer: "concept", week: 2 },
];

export const DESIGN_PREVIEW_MODEL: GraphModel = {
  kind: "preview",
  clusters: SEED_CLUSTERS,
  nodes: SEED_NODES,
  edges: SEED_EDGES,
  timeline: {
    labels: WEEK_LABELS,
    valueTexts: WEEK_LABELS.map((m, i) => (i === WEEK_LABELS.length - 1 ? "June 2026, all time" : `As of ${m} 2026`)),
  },
  autoLayout: false,
  comparisonAvailable: true,
  canAuthorLinks: true,
  actions: NODE_ACTIONS,
};
