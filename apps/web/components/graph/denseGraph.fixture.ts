/*
 * A dense graph shaped like the seeded demo patient's: six concerns, several
 * concepts each, many bridges shared by two or three concerns, open loops and
 * unassigned context, with links inside and across concerns.
 */

import type { Cluster, GraphEdge, GraphModel, GraphNode, NodeType } from "./graphData";
import { CLUSTER_PALETTE } from "./graphData";

const CONCERNS = ["Headaches", "Poor sleep", "Low energy", "Stomach upset", "Knee pain", "Blood pressure watch"];

const OWN: string[][] = [
  ["Migraine with aura", "Light sensitivity", "Neck tension", "Ibuprofen", "Neurology referral"],
  ["Night waking", "Late caffeine", "Melatonin trial", "Sleep study"],
  ["Afternoon crash", "Ferritin", "Vitamin B12", "Iron supplement", "Thyroid panel (TSH)"],
  ["Bloating after meals", "Lactose", "Reflux", "Omeprazole"],
  ["Right knee swelling", "Running", "Physio exercises", "Knee X-ray"],
  ["Home BP readings", "Salt intake", "Lisinopril", "Resting heart rate"],
];

const BRIDGES: Array<[string, number[]]> = [
  ["Stress at work", [0, 1, 2]],
  ["Screen time", [0, 1]],
  ["Dehydration", [0, 2]],
  ["Vitamin D (25-OH)", [2, 4]],
  ["Weight change", [3, 5]],
  ["Anxiety", [1, 5]],
  ["Ibuprofen use", [3, 4]],
  ["Morning headache", [0, 5]],
  ["Fatigue", [1, 2, 3]],
  ["Pain", [0, 4]],
];

const CONTEXT = ["Night shifts", "Commute", "Family history of hypertension", "Travel", "Hemoglobin A1c"];

export function denseModel(): GraphModel {
  const clusters: Cluster[] = CONCERNS.map((label, i) => ({
    id: `c${i}`,
    label,
    cx: 0,
    cy: 0,
    rx: 0,
    ry: 0,
    status: i === 4 ? "watch" : "active",
    href: `/threads/c${i}`,
    ...CLUSTER_PALETTE[i % CLUSTER_PALETTE.length]!,
  }));
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const node = (id: string, label: string, type: NodeType, extra: Partial<GraphNode> = {}): GraphNode => ({
    id,
    label,
    x: 0,
    y: 0,
    ev: (label.length * 7) % 9,
    conf: 3,
    act: 0.8,
    primary: true,
    type,
    layer: "concept",
    first: "Sep 1",
    last: "Sep 27",
    week: 0,
    relatedTotal: 3,
    sources: ["reported"],
    ...extra,
  });
  const link = (a: string, b: string, s = 4) => edges.push({ id: `e${edges.length}`, a, b, s, f: s >= 5 ? "co" : "time", layer: "concept", week: 0 });

  OWN.forEach((labels, ci) => {
    labels.forEach((label, j) => {
      nodes.push(node(`c${ci}n${j}`, label, j % 3 === 0 ? "symptom" : j % 3 === 1 ? "context" : "lab", { cluster: `c${ci}` }));
      if (j > 0) link(`c${ci}n0`, `c${ci}n${j}`, j === 1 ? 5 : 4);
      if (j > 1) link(`c${ci}n${j - 1}`, `c${ci}n${j}`, 3);
    });
    nodes.push(node(`c${ci}loop`, `Waiting for a result: ${CONCERNS[ci]}`, "pending", { cluster: `c${ci}`, ghost: true, statusNote: "Check back Oct 4", layer: "continuity" }));
    link(`c${ci}n0`, `c${ci}loop`, 4);
  });
  BRIDGES.forEach(([label, owners], bi) => {
    const id = `b${bi}`;
    nodes.push(node(id, label, bi % 2 ? "context" : "symptom", { cluster: `c${owners[0]}`, bridge: owners.map((o) => `c${o}`) }));
    owners.forEach((o, k) => link(id, `c${o}n${(bi + k) % OWN[o]!.length}`, 5));
  });
  CONTEXT.forEach((label, xi) => {
    const id = `x${xi}`;
    nodes.push(node(id, label, xi === 4 ? "lab" : "context"));
    link(id, `c${xi % 6}n1`, 4);
    link(id, `c${(xi + 3) % 6}n2`, 4);
  });
  // A few long cross-concern links.
  link("c0n0", "c3n0", 5);
  link("c1n0", "c4n0", 4);
  link("c2n0", "c5n0", 4);
  link("c0n2", "c5n3", 4);

  return {
    kind: "live",
    clusters,
    nodes,
    edges,
    timeline: { labels: ["now"], valueTexts: ["Everything so far"] },
    autoLayout: true,
    comparisonAvailable: false,
    canAuthorLinks: false,
    actions: [],
  };
}
