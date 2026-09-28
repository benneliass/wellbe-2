/*
 * Deterministic layout for the live cockpit. Concerns sit on an ellipse; their
 * concepts gather around them, bridges between the concerns they share, and
 * unassigned context near whatever it links to. A relaxation pass then pushes
 * node+label boxes (and concern titles) apart and nudges nodes off any link that
 * runs through them. Links between concerns bend gently away from the other
 * concerns; links inside a concern stay straight. When a dense graph still has
 * collisions the virtual canvas grows (the view then starts zoomed out).
 */

import { type Cluster, type GraphEdge, type GraphModel, type GraphNode, LAYERS } from "./graphData";

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
const EDGE_MARGIN = 5;
const CONTROLS_W = 58;
const MAX_GROW_ATTEMPTS = 6;

export function nodeRadius(n: Pick<GraphNode, "ev" | "lensRole">): number {
  return (n.lensRole === "theory" ? 17 : 14) + Math.min(n.ev, 14) * 0.42;
}

/** The label drawn on the canvas; the full label lives in the tooltip and inspector. */
export function canvasLabel(label: string, max = LABEL_MAX): string {
  return label.length > max ? `${label.slice(0, max - 1).trimEnd()}…` : label;
}

type Measure = (text: string, px: number, weight: number) => number;
let measurer: Measure | null | undefined;

/** Canvas 2D text metrics in a real browser; null under SSR and jsdom. */
function browserMeasure(): Measure | null {
  if (measurer !== undefined) return measurer;
  measurer = null;
  if (typeof document === "undefined" || typeof navigator === "undefined" || /jsdom/i.test(navigator.userAgent)) return null;
  let ctx: CanvasRenderingContext2D | null = null;
  try {
    ctx = document.createElement("canvas").getContext("2d");
  } catch {
    ctx = null;
  }
  if (!ctx) return null;
  const c = ctx;
  const cache = new Map<string, number>();
  measurer = (text, px, weight) => {
    const family = getComputedStyle(document.body).fontFamily || "sans-serif";
    const key = `${weight}|${px}|${family}|${text}`;
    const hit = cache.get(key);
    if (hit !== undefined) return hit;
    c.font = `${weight} ${px}px ${family}`;
    const w = c.measureText(text).width;
    if (!document.fonts || document.fonts.status === "loaded") cache.set(key, w);
    return w;
  };
  return measurer;
}

/** Label width: measured in the browser, a conservative estimate in tests and SSR. */
export function textWidth(text: string, px: number, weight = 600): number {
  const m = browserMeasure();
  return m ? m(text, px, weight) + 6 : text.length * px * 0.58 + 4;
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
  return { id: `cluster:${c.id}`, x, y, hw: textWidth(canvasLabel(c.label, 28), CLUSTER_LABEL_PX, 700) / 2 + 4, up: 16, down: 24 };
}

export function boxesOverlap(a: Box, b: Box, margin = 0): boolean {
  const ox = a.hw + b.hw + margin - Math.abs(a.x - b.x);
  const oy = Math.min(a.y + a.down, b.y + b.down) - Math.max(a.y - a.up, b.y - b.up) + margin;
  return ox > 0 && oy > 0;
}

/* ---------- edge geometry ---------- */

export interface Pt {
  x: number;
  y: number;
}

/** The fixed bow every link used before routing existed (design preview, links you add). */
export function defaultBend(a: Pt, b: Pt): number {
  return Math.min(46, Math.hypot(b.x - a.x, b.y - a.y) * 0.13);
}

/** Quadratic control point: `bend` px along the left normal of a→b from the midpoint. */
export function edgeControl(a: Pt, b: Pt, bend: number): Pt {
  const dx = b.x - a.x, dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  return { x: (a.x + b.x) / 2 + (-dy / len) * bend, y: (a.y + b.y) / 2 + (dx / len) * bend };
}

/** SVG path for a link; `bend` 0 draws a straight segment. */
export function edgePathD(a: Pt, b: Pt, bend: number): string {
  if (!bend) return `M${a.x},${a.y} L${b.x},${b.y}`;
  const c = edgeControl(a, b, bend);
  return `M${a.x},${a.y} Q${c.x.toFixed(1)},${c.y.toFixed(1)} ${b.x},${b.y}`;
}

/** Points along the drawn link (the curve flattened into short segments). */
export function edgePolyline(a: Pt, b: Pt, bend: number, steps = 10): Pt[] {
  if (!bend) return [a, b];
  const c = edgeControl(a, b, bend);
  const pts: Pt[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps, u = 1 - t;
    pts.push({ x: u * u * a.x + 2 * u * t * c.x + t * t * b.x, y: u * u * a.y + 2 * u * t * c.y + t * t * b.y });
  }
  return pts;
}

interface Rect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/** What a link must not pass through: a node's circle and its label line(s), or a concern title. */
export interface Obstacle {
  id: string;
  circle?: { x: number; y: number; r: number };
  rect: Rect;
}

export function nodeObstacle(n: GraphNode, x = n.x, y = n.y): Obstacle {
  const r = nodeRadius(n);
  const hw = textWidth(canvasLabel(n.label), NODE_LABEL_PX) / 2;
  return { id: n.id, circle: { x, y, r }, rect: { x0: x - hw, x1: x + hw, y0: y + r + 4, y1: y + r + (n.ghost || n.aggregate ? 34 : 20) } };
}

export function clusterTitleObstacle(c: Pick<Cluster, "id" | "label">, x: number, y: number): Obstacle {
  const hw = textWidth(canvasLabel(c.label, 28), CLUSTER_LABEL_PX, 700) / 2;
  return { id: `cluster:${c.id}`, rect: { x0: x - hw, x1: x + hw, y0: y - 13, y1: y + 21 } };
}

interface Push {
  nx: number;
  ny: number;
  pen: number;
}

function segRect(p: Pt, q: Pt, r: Rect, m: number): Push | null {
  const x0 = r.x0 - m, x1 = r.x1 + m, y0 = r.y0 - m, y1 = r.y1 + m;
  if (Math.max(p.x, q.x) < x0 || Math.min(p.x, q.x) > x1 || Math.max(p.y, q.y) < y0 || Math.min(p.y, q.y) > y1) return null;
  const dx = q.x - p.x, dy = q.y - p.y;
  const len = Math.hypot(dx, dy);
  if (len < 1e-6) return null;
  let nx = -dy / len, ny = dx / len;
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  let d = (cx - p.x) * nx + (cy - p.y) * ny;
  const e = Math.abs(nx) * ((x1 - x0) / 2) + Math.abs(ny) * ((y1 - y0) / 2);
  if (Math.abs(d) >= e) return null;
  if (d < 0) {
    nx = -nx;
    ny = -ny;
    d = -d;
  }
  return { nx, ny, pen: e - d };
}

function segCircle(p: Pt, q: Pt, c: { x: number; y: number; r: number }, m: number): Push | null {
  const dx = q.x - p.x, dy = q.y - p.y;
  const l2 = dx * dx + dy * dy;
  const t = l2 ? Math.max(0, Math.min(1, ((c.x - p.x) * dx + (c.y - p.y) * dy) / l2)) : 0;
  const ox = c.x - (p.x + dx * t), oy = c.y - (p.y + dy * t);
  const dist = Math.hypot(ox, oy);
  const need = c.r + m;
  if (dist >= need) return null;
  if (dist > 1e-6) return { nx: ox / dist, ny: oy / dist, pen: need - dist };
  const len = Math.sqrt(l2) || 1;
  return { nx: -dy / len, ny: dx / len, pen: need };
}

/** Deepest intrusion of a flattened link into an obstacle, or null when it stays clear. */
function hit(pts: Pt[], o: Obstacle, m: number): Push | null {
  let best: Push | null = null;
  for (let i = 1; i < pts.length; i++) {
    const p = pts[i - 1]!, q = pts[i]!;
    const a = o.circle ? segCircle(p, q, o.circle, m) : null;
    const b = segRect(p, q, o.rect, m);
    for (const h of [a, b]) if (h && (!best || h.pen > best.pen)) best = h;
  }
  return best;
}

function bounds(pts: Pt[]): Rect {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of pts) {
    if (p.x < x0) x0 = p.x;
    if (p.x > x1) x1 = p.x;
    if (p.y < y0) y0 = p.y;
    if (p.y > y1) y1 = p.y;
  }
  return { x0, y0, x1, y1 };
}

function obstacleBounds(o: Obstacle): Rect {
  const r = o.rect;
  if (!o.circle) return r;
  const c = o.circle;
  return { x0: Math.min(r.x0, c.x - c.r), x1: Math.max(r.x1, c.x + c.r), y0: Math.min(r.y0, c.y - c.r), y1: Math.max(r.y1, c.y + c.r) };
}

function rectsTouch(a: Rect, b: Rect, m: number): boolean {
  return a.x0 - m < b.x1 && b.x0 - m < a.x1 && a.y0 - m < b.y1 && b.y0 - m < a.y1;
}

/** Links (as drawn) that pass through a node or label they don't belong to. */
export function edgeCrossings(model: GraphModel, margin = 1): string[] {
  const byId = new Map(model.nodes.map((n) => [n.id, n]));
  const obstacles: Obstacle[] = [
    ...model.nodes.filter((n) => !n.deferred).map((n) => nodeObstacle(n)),
    ...model.clusters.filter((c) => c.labelX !== undefined && c.labelY !== undefined).map((c) => clusterTitleObstacle(c, c.labelX!, c.labelY!)),
  ];
  const out: string[] = [];
  for (const e of model.edges) {
    const a = byId.get(e.a), b = byId.get(e.b);
    if (!a || !b || a.deferred || b.deferred) continue;
    const pts = edgePolyline(a, b, e.bend ?? defaultBend(a, b));
    const bb = bounds(pts);
    for (const o of obstacles) {
      if (o.id === e.a || o.id === e.b || !rectsTouch(bb, obstacleBounds(o), margin)) continue;
      if (hit(pts, o, margin)) out.push(`${e.a}→${e.b} × ${o.id}`);
    }
  }
  return out;
}

/* ---------- layout ---------- */

const DEFAULT_LAYERS = new Set(LAYERS.filter((l) => l.defaultOn).map((l) => l.id));

function shownByDefault(n: GraphNode): boolean {
  return DEFAULT_LAYERS.has(n.layer) && !n.deferred && !n.aggregate;
}

function edgeShownByDefault(e: GraphEdge, a: GraphNode, b: GraphNode): boolean {
  const exempt = e.f === "user" || e.f === "hypothesis" || e.f === "relevance";
  return DEFAULT_LAYERS.has(e.layer) && (exempt || e.s >= 3) && shownByDefault(a) && shownByDefault(b);
}

/** The part of the graph shown with the default layers and link strength. */
export function defaultVisible(model: GraphModel): GraphModel {
  const byId = new Map(model.nodes.map((n) => [n.id, n]));
  return {
    ...model,
    nodes: model.nodes.filter(shownByDefault),
    edges: model.edges.filter((e) => byId.has(e.a) && byId.has(e.b) && edgeShownByDefault(e, byId.get(e.a)!, byId.get(e.b)!)),
  };
}

function hash(id: string): number {
  let h = 2166136261;
  for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619);
  return ((h >>> 0) % 1000) / 1000;
}

interface Body extends Box {
  tx: number;
  ty: number;
  /** Obstacle shape at the body's current position. */
  shape: (x: number, y: number) => Obstacle;
  /** Deferred nodes dock around their anchor in the renderer and never block links. */
  solid: boolean;
  /** Shown with the default layers and link strength. */
  visible: boolean;
}

interface Link {
  i: number;
  j: number;
  key: string;
  /** Endpoints share no concern: the link may bend. */
  inter: boolean;
  /** +1 / -1: which side of the chord bends away from the other concerns. */
  side: number;
  bend: number;
  visible: boolean;
}

export interface LaidOutGraph {
  model: GraphModel;
  /** Virtual extent the layout used; larger than the view box for big graphs. */
  extent: { width: number; height: number };
}

/** Halo ellipse wrapping a concern's title and its own concepts. */
export function clusterHalo(label: Box, members: Box[]): Pick<Cluster, "cx" | "cy" | "rx" | "ry"> {
  const boxes = [label, ...members];
  const minX = Math.min(...boxes.map((b) => b.x - b.hw));
  const maxX = Math.max(...boxes.map((b) => b.x + b.hw));
  const minY = Math.min(...boxes.map((b) => b.y - b.up));
  const maxY = Math.max(...boxes.map((b) => b.y + b.down));
  return {
    cx: (minX + maxX) / 2,
    cy: (minY + maxY) / 2,
    rx: Math.max(84, (maxX - minX) / 2 + 26),
    ry: Math.max(64, (maxY - minY) / 2 + 22),
  };
}

export function layoutGraph(model: GraphModel, view: ViewBox): LaidOutGraph {
  const boxArea = model.nodes.reduce((s, n) => {
    const b = nodeBox(n);
    return s + b.hw * 2 * (b.up + b.down);
  }, 0) + model.clusters.length * 160 * 40;
  const usableH = view.height - view.gutter;
  let scale = Math.max(1, Math.sqrt((boxArea * 2.2) / (view.width * usableH)));
  const big = model.nodes.length + model.clusters.length > 120;

  let best: { out: LaidOutGraph; bad: number } | null = null;
  for (let attempt = 0; attempt < (big ? 1 : MAX_GROW_ATTEMPTS); attempt++) {
    // A near miss first tries the concerns rotated half a step before growing the canvas.
    for (const turn of [0, 0.5]) {
      const { bad, ...out } = layoutAt(model, view, scale, turn);
      if (!best || bad < best.bad) best = { out, bad };
      if (bad === 0) return out;
      if (bad > 2) break;
    }
    scale *= best!.bad > 8 ? 1.2 : 1.1;
  }
  return best!.out;
}

/** Pairs of node boxes / concern titles that intersect. */
export function labelOverlaps(model: GraphModel): string[] {
  const boxes = [
    ...model.nodes.filter((n) => !n.deferred).map(nodeBox),
    ...model.clusters.filter((c) => c.labelX !== undefined).map((c) => clusterLabelBox(c, c.labelX!, c.labelY!)),
  ];
  const out: string[] = [];
  for (let i = 0; i < boxes.length; i++)
    for (let j = i + 1; j < boxes.length; j++) if (boxesOverlap(boxes[i]!, boxes[j]!)) out.push(`${boxes[i]!.id} × ${boxes[j]!.id}`);
  return out;
}

function layoutAt(model: GraphModel, view: ViewBox, scale: number, turn: number): LaidOutGraph & { bad: number } {
  const nodes = model.nodes.map((n) => ({ ...n }));
  const boxArea = nodes.reduce((s, n) => {
    const b = nodeBox(n);
    return s + b.hw * 2 * (b.up + b.down);
  }, 0) + model.clusters.length * 160 * 40;
  const usableH = view.height - view.gutter;
  const W = view.width * scale;
  const H = usableH * scale;
  const cx = W / 2;
  const cy = H / 2 + 6;

  const k = model.clusters.length;
  const rx = Math.max(0, W / 2 - Math.min(170, W * 0.2));
  const ry = Math.max(0, H / 2 - Math.min(130, H * 0.2));
  const anchor = new Map<string, { x: number; y: number }>();
  model.clusters.forEach((c, i) => {
    const a = -Math.PI / 2 + ((i + turn) / Math.max(k, 1)) * Math.PI * 2;
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
        t = { x: a.x + Math.cos(ang) * 78 * Math.sqrt(scale), y: a.y + Math.sin(ang) * 62 * Math.sqrt(scale) };
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
    bodies.push({ ...box, tx: t.x, ty: t.y, shape: (x, y) => nodeObstacle(n, x, y), solid: !n.deferred, visible: shownByDefault(n) });
  }
  const labelBodies: Body[] = model.clusters.map((c) => {
    const a = anchor.get(c.id)!;
    const box = clusterLabelBox(c, a.x, a.y - 64);
    return { ...box, tx: box.x, ty: box.y, shape: (x, y) => clusterTitleObstacle(c, x, y), solid: true, visible: true };
  });
  const all: Body[] = [...bodies, ...labelBodies];

  const index = new Map(nodes.map((n, i) => [n.id, i]));
  const links: Link[] = [];
  const linkSeen = new Set<string>();
  for (const e of model.edges) {
    const i = index.get(e.a), j = index.get(e.b);
    if (i === undefined || j === undefined || i === j) continue;
    const key = `${e.a}|${e.b}`;
    if (linkSeen.has(key)) continue;
    linkSeen.add(key);
    const oa = owners(nodes[i]!), ob = owners(nodes[j]!);
    const inter = !oa.some((id) => ob.includes(id));
    links.push({ i, j, key, inter, side: 0, bend: 0, visible: edgeShownByDefault(e, nodes[i]!, nodes[j]!) });
  }
  const linkOwners = links.map((l) => new Set([...owners(nodes[l.i]!), ...owners(nodes[l.j]!)]));

  /** Bend inter-cluster links away from the concerns they don't belong to. */
  const route = () => {
    links.forEach((l, li) => {
      if (!l.inter) {
        l.bend = 0;
        return;
      }
      const a = all[l.i]!, b = all[l.j]!;
      const dx = b.x - a.x, dy = b.y - a.y;
      const len = Math.hypot(dx, dy) || 1;
      const nx = -dy / len, ny = dx / len;
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      let px = 0, py = 0;
      for (const [id, p] of anchor) {
        if (linkOwners[li]!.has(id)) continue;
        const ox = mx - p.x, oy = my - p.y;
        const d2 = Math.max(ox * ox + oy * oy, 400);
        px += ox / d2;
        py += oy / d2;
      }
      if (px === 0 && py === 0) {
        px = mx - cx;
        py = my - cy;
      }
      const dot = px * nx + py * ny;
      l.side = Math.abs(dot) < 1e-9 ? (hash(l.key) < 0.5 ? -1 : 1) : Math.sign(dot);
      l.bend = l.side * Math.min(56, len * 0.18);
    });
  };

  const n = all.length;
  const iterations = n > 120 ? 220 : Math.min(900, 400 + n * 8);
  const settle = Math.floor(iterations * 0.65);
  const edgeForces = links.length > 0 && n <= 120;
  const clamp = (b: Body) => {
    // Left band stays clear for the zoom controls, top band for the zoom-level hint.
    b.x = Math.min(W - b.hw - MARGIN, Math.max(b.hw + CONTROLS_W, b.x));
    b.y = Math.min(H - b.down - 4, Math.max(b.up + MARGIN + 36, b.y));
  };
  const boxPass = () => {
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
  };
  /** Nudge nodes (and titles) perpendicular off any link that runs through them. */
  const edgePass = (gain: number, margin: number) => {
    for (const l of links) {
      const a = all[l.i]!, b = all[l.j]!;
      const pts = edgePolyline(a, b, l.bend, 8);
      const bb = bounds(pts);
      for (let k2 = 0; k2 < n; k2++) {
        if (k2 === l.i || k2 === l.j) continue;
        const o = all[k2]!;
        if (!o.solid) continue;
        if (o.x + o.hw + margin < bb.x0 || o.x - o.hw - margin > bb.x1 || o.y + o.down + margin < bb.y0 || o.y - o.up - margin > bb.y1) continue;
        const h = hit(pts, o.shape(o.x, o.y), margin);
        if (!h) continue;
        const s = Math.min(h.pen, 40) * gain;
        o.x += h.nx * s * 0.7;
        o.y += h.ny * s * 0.7;
        a.x -= h.nx * s * 0.15;
        a.y -= h.ny * s * 0.15;
        b.x -= h.nx * s * 0.15;
        b.y -= h.ny * s * 0.15;
      }
    }
  };
  const crossingsOf = (l: Link, bend: number, obstacles: Array<Obstacle | null>, visibleOnly: boolean) => {
    const pts = edgePolyline(all[l.i]!, all[l.j]!, bend);
    const bb = bounds(pts);
    let c = 0;
    obstacles.forEach((o, oi) => {
      if (!o || oi === l.i || oi === l.j || (visibleOnly && !all[oi]!.visible) || !rectsTouch(bb, obstacleBounds(o), 1)) return;
      if (hit(pts, o, 1)) c++;
    });
    return c;
  };
  /** Per link: keep the preferred bend, or try the other side / a stronger or flatter one. */
  const chooseBends = () => {
    const obstacles = all.map((b) => (b.solid ? b.shape(b.x, b.y) : null));
    for (const l of links) {
      const cost = (bend: number) => crossingsOf(l, bend, obstacles, true) * 4 + crossingsOf(l, bend, obstacles, false);
      let bestC = cost(l.bend);
      if (bestC === 0) continue;
      const a = all[l.i]!, b = all[l.j]!;
      const base = Math.min(56, (Math.hypot(b.x - a.x, b.y - a.y) || 1) * 0.18) * (l.side || 1);
      const candidates = l.inter
        ? [-base, base * 1.6, -base * 1.6, base * 0.5, -base * 0.5, 0, base * 2.4, -base * 2.4]
        : [base * 0.6, -base * 0.6, base * 1.2, -base * 1.2];
      let bestBend = l.bend;
      for (const c of candidates) {
        const cc = cost(c);
        if (cc < bestC) {
          bestC = cc;
          bestBend = c;
          if (cc === 0) break;
        }
      }
      l.bend = bestBend;
    }
  };
  /** Label overlaps and links through default-visible nodes must go; hidden layers count less. */
  const score = () => {
    let overlaps = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (all[i]!.solid && all[j]!.solid && boxesOverlap(all[i]!, all[j]!)) overlaps++;
    const obstacles = all.map((b) => (b.solid ? b.shape(b.x, b.y) : null));
    let visible = 0, hidden = 0;
    for (const l of links) {
      const v = l.visible ? crossingsOf(l, l.bend, obstacles, true) : 0;
      visible += v;
      hidden += crossingsOf(l, l.bend, obstacles, false) - v;
    }
    return { bad: overlaps + visible, total: (overlaps + visible) * 100 + hidden };
  };

  route();
  for (let it = 0; it < iterations; it++) {
    const pull = it < settle ? 0.06 : 0;
    for (const b of all) {
      b.x += (b.tx - b.x) * pull;
      b.y += (b.ty - b.y) * pull;
    }
    boxPass();
    if (edgeForces && it % 2 === 0) {
      if (it % 20 === 0) route();
      edgePass(it < settle ? 0.5 : 0.8, EDGE_MARGIN);
    }
    for (const b of all) clamp(b);
  }
  route();

  // Polish: resolve what's left locally, keeping the best state seen.
  let best = { total: Infinity, bad: Infinity, pos: [] as number[], bends: [] as number[] };
  const rounds = edgeForces ? 40 : 1;
  for (let round = 0; round < rounds; round++) {
    if (edgeForces) chooseBends();
    const s = score();
    if (s.total < best.total) best = { ...s, pos: all.flatMap((b) => [b.x, b.y]), bends: links.map((l) => l.bend) };
    if (s.total === 0) break;
    edgePass(1, EDGE_MARGIN + 2);
    for (let r = 0; r < 4; r++) {
      boxPass();
      for (const b of all) clamp(b);
    }
  }
  all.forEach((b, i) => {
    b.x = best.pos[i * 2]!;
    b.y = best.pos[i * 2 + 1]!;
  });
  links.forEach((l, i) => (l.bend = best.bends[i]!));

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
    return { ...c, ...clusterHalo(label, members), labelX: Math.round(label.x * 10) / 10, labelY: Math.round(label.y * 10) / 10 };
  });

  const bendOf = new Map(links.map((l) => [l.key, Math.round(l.bend * 10) / 10]));
  const edges: GraphEdge[] = model.edges.map((e) => ({ ...e, bend: bendOf.get(`${e.a}|${e.b}`) ?? 0 }));

  return { model: { ...model, nodes, clusters, edges }, extent: { width: W, height: H }, bad: best.bad };
}
