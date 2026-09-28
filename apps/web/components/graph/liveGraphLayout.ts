/*
 * Deterministic layout for the live cockpit. Concerns sit on an ellipse; their
 * concepts gather around them, bridges between the concerns they share, and
 * unassigned context near whatever it links to. A relaxation pass then pushes
 * node+label boxes (and concern titles) apart so no two labels overlap.
 */

import type { Cluster, GraphModel, GraphNode } from "./graphData";

export interface ViewBox {
  width: number;
  height: number;
  /** Bottom band reserved for the in-canvas Replay dock. */
  gutter: number;
}

export const WIDE_VIEW: ViewBox = { width: 860, height: 686, gutter: 92 };
export const COMPACT_VIEW: ViewBox = { width: 480, height: 760, gutter: 96 };

const NODE_LABEL_PX = 12.5;
const CLUSTER_LABEL_PX = 14;
const LABEL_MAX = 28;
const MARGIN = 8;
const CONTROLS_W = 58;

export function nodeRadius(n: Pick<GraphNode, "ev" | "lensRole">): number {
  return (n.lensRole === "theory" ? 17 : 14) + Math.min(n.ev, 14) * 0.42;
}

/** The label drawn on the canvas; the full label lives in the tooltip and inspector. */
export function canvasLabel(label: string, max = LABEL_MAX): string {
  return label.length > max ? `${label.slice(0, max - 1).trimEnd()}…` : label;
}

/** Conservative width estimate for the app sans at weight 600–700. */
export function textWidth(text: string, px: number): number {
  return text.length * px * 0.58 + 4;
}

export interface Box {
  id: string;
  x: number;
  y: number;
  hw: number;
  up: number;
  down: number;
}

/** Screen-space box a node occupies including its label line(s). */
export function nodeBox(n: GraphNode): Box {
  const r = nodeRadius(n);
  const extraLine = n.ghost || n.aggregate;
  return {
    id: n.id,
    x: n.x,
    y: n.y,
    hw: Math.max(r + 8, textWidth(canvasLabel(n.label), NODE_LABEL_PX) / 2),
    up: r + 8,
    down: r + (extraLine ? 36 : 22),
  };
}

export function clusterLabelBox(c: Pick<Cluster, "id" | "label">, x: number, y: number): Box {
  return { id: `cluster:${c.id}`, x, y, hw: textWidth(canvasLabel(c.label, 28), CLUSTER_LABEL_PX) / 2 + 4, up: 16, down: 24 };
}

export function boxesOverlap(a: Box, b: Box, margin = 0): boolean {
  const ox = a.hw + b.hw + margin - Math.abs(a.x - b.x);
  const oy = Math.min(a.y + a.down, b.y + b.down) - Math.max(a.y - a.up, b.y - b.up) + margin;
  return ox > 0 && oy > 0;
}

function hash(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return ((h >>> 0) % 1000) / 1000;
}

interface Body extends Box {
  tx: number;
  ty: number;
}

export interface LaidOutGraph {
  model: GraphModel;
  /** Virtual extent the layout used; larger than the view box for big graphs. */
  extent: { width: number; height: number };
}

export function layoutGraph(model: GraphModel, view: ViewBox): LaidOutGraph {
  const nodes = model.nodes.map((n) => ({ ...n }));

  // Grow the virtual canvas when the boxes can't fit (the view then starts zoomed out).
  const boxArea = nodes.reduce((s, n) => {
    const b = nodeBox(n);
    return s + b.hw * 2 * (b.up + b.down);
  }, 0) + model.clusters.length * 160 * 40;
  const usableH = view.height - view.gutter;
  const scale = Math.max(1, Math.sqrt((boxArea * 2.2) / (view.width * usableH)));
  const W = view.width * scale;
  const H = usableH * scale;
  const cx = W / 2;
  const cy = H / 2 + 6;

  const k = model.clusters.length;
  const rx = Math.max(0, W / 2 - Math.min(170, W * 0.2));
  const ry = Math.max(0, H / 2 - Math.min(130, H * 0.2));
  const anchor = new Map<string, { x: number; y: number }>();
  model.clusters.forEach((c, i) => {
    const a = -Math.PI / 2 + (i / Math.max(k, 1)) * Math.PI * 2;
    anchor.set(c.id, k === 1 ? { x: cx, y: cy } : { x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry });
  });

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const neighbours = new Map<string, string[]>();
  for (const e of model.edges) {
    (neighbours.get(e.a) ?? neighbours.set(e.a, []).get(e.a)!).push(e.b);
    (neighbours.get(e.b) ?? neighbours.set(e.b, []).get(e.b)!).push(e.a);
  }
  const owners = (n: GraphNode) => (n.bridge ?? (n.cluster ? [n.cluster] : [])).filter((id) => anchor.has(id));
  const mean = (ids: string[]) => {
    const pts = ids.map((id) => anchor.get(id)!);
    return { x: pts.reduce((s, p) => s + p.x, 0) / pts.length, y: pts.reduce((s, p) => s + p.y, 0) / pts.length };
  };

  const memberCount = new Map<string, number>();
  for (const n of nodes) {
    const own = owners(n);
    if (own.length === 1) memberCount.set(own[0]!, (memberCount.get(own[0]!) ?? 0) + 1);
  }
  const avgBox = Math.sqrt(boxArea / Math.max(nodes.length, 1));

  const seen = new Map<string, number>();
  const bodies: Body[] = [];
  for (const n of nodes) {
    const own = owners(n);
    let t: { x: number; y: number };
    if (own.length === 1) {
      const a = anchor.get(own[0]!)!;
      const j = seen.get(own[0]!) ?? 0;
      seen.set(own[0]!, j + 1);
      if (j === 0) t = { ...a };
      else if ((memberCount.get(own[0]!) ?? 0) > 6) {
        // Big concerns: sunflower spiral so members start spread out.
        const rad = avgBox * 0.95 * Math.sqrt(j);
        t = { x: a.x + Math.cos(j * 2.39996) * rad, y: a.y + Math.sin(j * 2.39996) * rad * 0.8 };
      } else {
        const out = Math.atan2(a.y - cy, a.x - cx);
        const ang = out + Math.PI + (j % 2 ? 1 : -1) * Math.ceil(j / 2) * 0.95;
        t = { x: a.x + Math.cos(ang) * 78, y: a.y + Math.sin(ang) * 62 };
      }
    } else if (own.length > 1) {
      const key = [...own].sort().join("|");
      const j = seen.get(key) ?? 0;
      seen.set(key, j + 1);
      const m = mean(own);
      t = { x: m.x + (j % 2 ? 1 : -1) * Math.ceil(j / 2) * 60, y: m.y + (hash(n.id) - 0.5) * 30 };
    } else {
      const linked = Array.from(new Set((neighbours.get(n.id) ?? []).flatMap((id) => (byId.get(id) ? owners(byId.get(id)!) : []))));
      const m = linked.length ? mean(linked) : { x: cx, y: cy };
      // Pull unassigned context toward the centre so it reads as shared.
      t = { x: m.x * 0.5 + cx * 0.5 + (hash(n.id) - 0.5) * 120, y: m.y * 0.5 + cy * 0.5 + (hash(`${n.id}y`) - 0.5) * 90 };
    }
    const box = nodeBox({ ...n, x: t.x, y: t.y });
    bodies.push({ ...box, tx: t.x, ty: t.y });
  }
  const labelBodies = model.clusters.map((c) => {
    const a = anchor.get(c.id)!;
    const box = clusterLabelBox(c, a.x, a.y - 64);
    return { ...box, tx: box.x, ty: box.y };
  });
  const all: Body[] = [...bodies, ...labelBodies];

  const n = all.length;
  const iterations = n > 250 ? 220 : 400;
  const settle = Math.floor(iterations * 0.7);
  for (let it = 0; it < iterations; it++) {
    const pull = it < settle ? 0.06 : 0;
    for (const b of all) {
      b.x += (b.tx - b.x) * pull;
      b.y += (b.ty - b.y) * pull;
    }
    for (let i = 0; i < n; i++) {
      const p = all[i]!;
      for (let j = i + 1; j < n; j++) {
        const q = all[j]!;
        const dx = q.x - p.x;
        const ox = p.hw + q.hw + MARGIN - Math.abs(dx);
        if (ox <= 0) continue;
        const oy = Math.min(p.y + p.down, q.y + q.down) - Math.max(p.y - p.up, q.y - q.up) + MARGIN;
        if (oy <= 0) continue;
        if (ox < oy) {
          const s = (dx === 0 ? (i % 2 ? 1 : -1) : Math.sign(dx)) * ox * 0.5;
          p.x -= s;
          q.x += s;
        } else {
          const dcy = q.y + (q.down - q.up) / 2 - (p.y + (p.down - p.up) / 2);
          const s = (dcy === 0 ? (j % 2 ? 1 : -1) : Math.sign(dcy)) * oy * 0.5;
          p.y -= s;
          q.y += s;
        }
      }
    }
    for (const b of all) {
      // Left band stays clear for the zoom controls, top band for the zoom-level hint.
      b.x = Math.min(W - b.hw - MARGIN, Math.max(b.hw + CONTROLS_W, b.x));
      b.y = Math.min(H - b.down - 4, Math.max(b.up + MARGIN + 36, b.y));
    }
  }

  bodies.forEach((b, i) => {
    nodes[i]!.x = Math.round(b.x * 10) / 10;
    nodes[i]!.y = Math.round(b.y * 10) / 10;
  });

  const clusters: Cluster[] = model.clusters.map((c, i) => {
    const label = labelBodies[i]!;
    const members = bodies.filter((_, bi) => {
      const nd = nodes[bi]!;
      return nd.cluster === c.id && !nd.bridge;
    });
    const boxes: Box[] = [label, ...members];
    const minX = Math.min(...boxes.map((b) => b.x - b.hw));
    const maxX = Math.max(...boxes.map((b) => b.x + b.hw));
    const minY = Math.min(...boxes.map((b) => b.y - b.up));
    const maxY = Math.max(...boxes.map((b) => b.y + b.down));
    return {
      ...c,
      cx: (minX + maxX) / 2,
      cy: (minY + maxY) / 2,
      rx: Math.max(84, (maxX - minX) / 2 + 26),
      ry: Math.max(64, (maxY - minY) / 2 + 22),
      labelX: label.x,
      labelY: label.y,
    };
  });

  return { model: { ...model, nodes, clusters }, extent: { width: W, height: H } };
}
