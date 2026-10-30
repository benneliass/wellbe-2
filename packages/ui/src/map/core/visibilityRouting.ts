import type { RoutingPoint } from "./radialRouting";
import type { RouteCandidate, RoutePoint } from "./routing";
import { segmentCrossing } from "./geometry";

const distance = (a: RoutePoint, b: RoutePoint) => Math.hypot(a.x - b.x, a.y - b.y);

/** Multi-port shortest paths through visible obstacle vertices, with a checked rounded finish. */
export function visibilityConnection(a: RoutingPoint, b: RoutingPoint, others: readonly RoutingPoint[], view: { width: number; height: number }, peers: readonly (readonly RoutePoint[])[] = []): RouteCandidate | null {
  const obstacles = [...others, a, b];
  const circles = obstacles.filter((o) => !o.labelOnly).map((o) => ({ ...o, radius: o.r + (o === a || o === b ? 0.25 : 8) }));
  const rects = obstacles.filter((o) => !o.allowUnderLabel).map((o) => ({ left: o.x - (o.labelWidth ?? 100) / 2 - 4, right: o.x + (o.labelWidth ?? 100) / 2 + 4, top: o.y + (o.labelTop ?? o.r + 8) - 2, bottom: o.y + (o.labelBottom ?? o.r + 34) + 3 }));
  const free = (p: RoutePoint) => p.x >= 4 && p.x <= view.width - 4 && p.y >= 4 && p.y <= view.height - 4 && circles.every((o) => distance(p, o) >= o.radius) && rects.every((r) => p.x <= r.left || p.x >= r.right || p.y <= r.top || p.y >= r.bottom);
  const clear = (p: RoutePoint, q: RoutePoint) => {
    const dx = q.x - p.x, dy = q.y - p.y, len2 = dx * dx + dy * dy || 1;
    const left = Math.min(p.x, q.x), right = Math.max(p.x, q.x), top = Math.min(p.y, q.y), bottom = Math.max(p.y, q.y);
    for (const o of circles) {
      if (right < o.x - o.radius || left > o.x + o.radius || bottom < o.y - o.radius || top > o.y + o.radius) continue;
      const t = Math.max(0, Math.min(1, ((o.x - p.x) * dx + (o.y - p.y) * dy) / len2));
      if ((p.x + t * dx - o.x) ** 2 + (p.y + t * dy - o.y) ** 2 < (o.radius - 0.001) ** 2) return false;
    }
    for (const r of rects) {
      if (right <= r.left || left >= r.right || bottom <= r.top || top >= r.bottom) continue;
      let min = 0, max = 1;
      for (const [start, delta, low, high] of [[p.x, dx, r.left, r.right], [p.y, dy, r.top, r.bottom]]) {
        if (Math.abs(delta!) < 1e-9) { if (start! <= low! || start! >= high!) { min = 2; break; } }
        else { const t1 = (low! - start!) / delta!, t2 = (high! - start!) / delta!; min = Math.max(min, Math.min(t1, t2)); max = Math.min(max, Math.max(t1, t2)); }
      }
      if (min < max - 0.0001) return false;
    }
    return true;
  };
  const crossingCost = (p: RoutePoint, q: RoutePoint) => {
    let cost = 0;
    const found: RoutePoint[] = [];
    for (const peer of peers) for (let j = 1; j < peer.length; j++) {
      const r = peer[j - 1]!, s = peer[j]!;
      if (Math.max(p.x, q.x) < Math.min(r.x, s.x) || Math.min(p.x, q.x) > Math.max(r.x, s.x) || Math.max(p.y, q.y) < Math.min(r.y, s.y) || Math.min(p.y, q.y) > Math.max(r.y, s.y)) continue;
      const intersection = segmentCrossing(p, q, r, s);
      if (intersection && !found.some((previous) => distance(previous, intersection) < 2)) { cost += 90; found.push(intersection); }
    }
    return cost;
  };
  const points: RoutePoint[] = [];
  const starts = new Map<number, RoutePoint>(), goals = new Map<number, RoutePoint>();
  for (const [node, ports] of [[a, starts], [b, goals]] as const) for (let i = 0; i < 16; i++) {
    const angle = i * Math.PI / 8;
    const rim = { x: node.x + Math.cos(angle) * (node.r + 1), y: node.y + Math.sin(angle) * (node.r + 1) };
    const lead = { x: node.x + Math.cos(angle) * (node.r + 11), y: node.y + Math.sin(angle) * (node.r + 11) };
    if (free(rim) && free(lead) && clear(rim, lead)) { ports.set(points.length, rim); points.push(lead); }
  }
  if (!starts.size || !goals.size) return null;
  for (const o of circles) for (let i = 0; i < 12; i++) {
    const angle = i * Math.PI / 6, radius = (o.radius + 3) / Math.cos(Math.PI / 12);
    const p = { x: o.x + Math.cos(angle) * radius, y: o.y + Math.sin(angle) * radius };
    if (free(p)) points.push(p);
  }
  for (const r of rects) for (const x of [r.left - 5, r.right + 5]) for (const y of [r.top - 5, r.bottom + 5]) if (free({ x, y })) points.push({ x, y });
  const links = points.map(() => [] as { index: number; cost: number }[]);
  for (let i = 0; i < points.length; i++) for (let j = i + 1; j < points.length; j++) if (clear(points[i]!, points[j]!)) {
    const cost = distance(points[i]!, points[j]!) + crossingCost(points[i]!, points[j]!);
    links[i]!.push({ index: j, cost }); links[j]!.push({ index: i, cost });
  }
  const costs = new Float64Array(points.length).fill(Infinity), parents = new Int32Array(points.length).fill(-1), closed = new Set<number>();
  for (const [index, rim] of starts) costs[index] = distance(points[index]!, rim);
  let found = -1, total = Infinity;
  for (let step = 0; step < points.length; step++) {
    let current = -1;
    for (let i = 0; i < points.length; i++) if (!closed.has(i) && (current < 0 || costs[i]! < costs[current]!)) current = i;
    if (current < 0 || !Number.isFinite(costs[current]) || costs[current]! > total) break;
    if (goals.has(current)) { const cost = costs[current]! + distance(points[current]!, goals.get(current)!); if (cost < total) { found = current; total = cost; } }
    closed.add(current);
    for (const link of links[current]!) if (!closed.has(link.index) && costs[current]! + link.cost < costs[link.index]!) { costs[link.index] = costs[current]! + link.cost; parents[link.index] = current; }
  }
  if (found < 0) return null;
  const raw: RoutePoint[] = [goals.get(found)!];
  let cursor = found;
  while (cursor >= 0) { raw.unshift(points[cursor]!); if (parents[cursor]! < 0) break; cursor = parents[cursor]!; }
  raw.unshift(starts.get(cursor)!);
  const route = [raw[0]!];
  for (let from = 0; from < raw.length - 1;) {
    let to = raw.length - 1;
    while (to > from + 1 && (!clear(raw[from]!, raw[to]!) || crossingCost(raw[from]!, raw[to]!) > raw.slice(from + 1, to + 1).reduce((sum, point, j) => sum + crossingCost(raw[from + j]!, point), 0))) to--;
    route.push(raw[to]!); from = to;
  }
  const sampled: RoutePoint[] = [route[0]!];
  let d = `M ${route[0]!.x} ${route[0]!.y}`;
  const line = (p: RoutePoint) => {
    const from = sampled.at(-1)!, steps = Math.max(1, Math.ceil(distance(from, p) / 3));
    for (let i = 1; i <= steps; i++) sampled.push({ x: from.x + (p.x - from.x) * i / steps, y: from.y + (p.y - from.y) * i / steps });
    d += ` L ${p.x} ${p.y}`;
  };
  for (let i = 1; i < route.length - 1; i++) {
    const before = route[i - 1]!, corner = route[i]!, after = route[i + 1]!;
    const lenA = distance(before, corner), lenB = distance(corner, after);
    let radius = Math.min(28, lenA * 0.35, lenB * 0.35), curve: RoutePoint[] = [], entry = corner, exit = corner;
    for (let attempt = 0; attempt < 6; attempt++) {
      entry = { x: corner.x + (before.x - corner.x) * radius / (lenA || 1), y: corner.y + (before.y - corner.y) * radius / (lenA || 1) };
      exit = { x: corner.x + (after.x - corner.x) * radius / (lenB || 1), y: corner.y + (after.y - corner.y) * radius / (lenB || 1) };
      curve = Array.from({ length: 21 }, (_, j) => { const t = j / 20, s = 1 - t; return { x: s * s * entry.x + 2 * s * t * corner.x + t * t * exit.x, y: s * s * entry.y + 2 * s * t * corner.y + t * t * exit.y }; });
      if (curve.every(free)) break;
      radius *= 0.5;
    }
    if (!curve.every(free)) { line(corner); continue; }
    line(entry); sampled.push(...curve.slice(1)); d += ` Q ${corner.x} ${corner.y} ${exit.x} ${exit.y}`;
  }
  line(route.at(-1)!);
  const length = sampled.slice(1).reduce((sum, p, i) => sum + distance(p, sampled[i]!), 0);
  return { d, points: sampled, length, cost: length + Math.max(0, route.length - 2) * 8 };
}
