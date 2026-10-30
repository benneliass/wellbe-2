import { routeAroundRecords, type RoutingPoint } from "./radialRouting";
import { visibilityConnection } from "./visibilityRouting";
import { segmentCrossing } from "./geometry";

export type RoutePoint = { x: number; y: number };
export type RouteCandidate = { d: string; points: RoutePoint[]; length: number; cost: number };
type View = { width: number; height: number };
const dist = (a: RoutePoint, b: RoutePoint) => Math.hypot(b.x - a.x, b.y - a.y);

function candidate(a: RoutingPoint, b: RoutingPoint, da: number, db: number, handle: number, obstacles: readonly RoutingPoint[], view?: View): RouteCandidate | null {
  const start = { x: a.x + Math.cos(da) * (a.r + 1), y: a.y + Math.sin(da) * (a.r + 1) };
  const end = { x: b.x + Math.cos(db) * (b.r + 1), y: b.y + Math.sin(db) * (b.r + 1) };
  const c1 = { x: start.x + Math.cos(da) * handle, y: start.y + Math.sin(da) * handle };
  const c2 = { x: end.x + Math.cos(db) * handle, y: end.y + Math.sin(db) * handle };
  const points: RoutePoint[] = [];
  const blocking = [...obstacles, a, b];
  let length = 0, turns = 0, previousDirection: RoutePoint | undefined;
  const steps = Math.max(48, Math.ceil((dist(a, b) + handle * 2) / 4));
  for (let i = 0; i <= steps; i++) {
    const t = i / steps, s = 1 - t;
    const p = { x: s ** 3 * start.x + 3 * s * s * t * c1.x + 3 * s * t * t * c2.x + t ** 3 * end.x, y: s ** 3 * start.y + 3 * s * s * t * c1.y + 3 * s * t * t * c2.y + t ** 3 * end.y };
    if (view && (p.x < 4 || p.x > view.width - 4 || p.y < 4 || p.y > view.height - 4)) return null;
    for (const obstacle of blocking) {
      const endpoint = obstacle === a || obstacle === b;
      if (!obstacle.labelOnly && (p.x - obstacle.x) ** 2 + (p.y - obstacle.y) ** 2 < (obstacle.r + (endpoint ? 0.25 : 8)) ** 2) return null;
      if (!obstacle.allowUnderLabel && Math.abs(p.x - obstacle.x) < (obstacle.labelWidth ?? 100) / 2 + 4 && p.y > obstacle.y + (obstacle.labelTop ?? obstacle.r + 8) - 2 && p.y < obstacle.y + (obstacle.labelBottom ?? obstacle.r + 34) + 3) return null;
    }
    if (i) {
      const previous = points[i - 1]!, direction = { x: p.x - previous.x, y: p.y - previous.y }, travel = dist(previous, p);
      length += travel;
      if (previousDirection) {
        const angle = Math.acos(Math.max(-1, Math.min(1, (direction.x * previousDirection.x + direction.y * previousDirection.y) / (travel * Math.hypot(previousDirection.x, previousDirection.y) || 1))));
        if (angle > 0.12 && travel / angle < Math.min(16, Math.min(a.r, b.r) * 0.65)) return null;
        turns += angle;
      }
      previousDirection = direction;
    }
    points.push(p);
  }
  return { d: `M ${start.x} ${start.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${end.x} ${end.y}`, points, length, cost: length + turns * 6 };
}

/** Compare radial ports and complete clear curves, rather than accepting the first clear bend. */
export function connectionCandidates(a: RoutingPoint, b: RoutingPoint, obstacles: readonly RoutingPoint[], view?: View): RouteCandidate[] {
  const heading = Math.atan2(b.y - a.y, b.x - a.x), span = dist(a, b);
  const offsets = [0, -Math.PI / 8, Math.PI / 8, -Math.PI / 4, Math.PI / 4, -3 * Math.PI / 8, 3 * Math.PI / 8, -Math.PI / 2, Math.PI / 2, -3 * Math.PI / 4, 3 * Math.PI / 4, Math.PI];
  const all: RouteCandidate[] = [];
  for (const from of offsets) for (const to of offsets) for (const fraction of [0.2, 0.38, 0.65]) {
    const route = candidate(a, b, heading + from, heading + Math.PI + to, Math.max(10, Math.min(180, span * fraction)), obstacles, view);
    if (route) all.push(route);
  }
  all.sort((left, right) => left.cost - right.cost);
  // Keep genuinely different corridors available for the scene crossing pass.
  const diverse: RouteCandidate[] = [];
  for (const route of all) {
    if (route.length > all[0]!.length * 1.55 + 24) continue;
    const middle = route.points[Math.floor(route.points.length / 2)]!;
    if (diverse.some((kept) => dist(middle, kept.points[Math.floor(kept.points.length / 2)]!) < 7 && dist(route.points[0]!, kept.points[0]!) < 5)) continue;
    diverse.push(route);
    if (diverse.length === 16) break;
  }
  return diverse;
}

/** Proper crossings and long shared tracks carry a cost; a natural shared rim does not. */
export function routeInterference(a: readonly RoutePoint[], b: readonly RoutePoint[], sharedEnds: readonly (RoutePoint & { r: number })[] = []): number {
  let crossings = 0, shared = 0;
  const intersections: RoutePoint[] = [];
  const strideA = Math.max(1, Math.floor(a.length / 28)), strideB = Math.max(1, Math.floor(b.length / 28));
  for (let i = strideA; i < a.length - strideA * 2; i += strideA) {
    const p = a[i]!, q = a[i + strideA]!;
    let close = false;
    for (let j = strideB; j < b.length - strideB * 2; j += strideB) {
      const r = b[j]!, s = b[j + strideB]!;
      if (Math.max(p.x, q.x) + 4 < Math.min(r.x, s.x) || Math.min(p.x, q.x) - 4 > Math.max(r.x, s.x) || Math.max(p.y, q.y) + 4 < Math.min(r.y, s.y) || Math.min(p.y, q.y) - 4 > Math.max(r.y, s.y)) continue;
      const intersection = segmentCrossing(p, q, r, s);
      if (intersection && !sharedEnds.some((end) => dist(end, intersection) < end.r) && !intersections.some((previous) => dist(previous, intersection) < 2)) { intersections.push(intersection); crossings++; }
      const dx = q.x - p.x, dy = q.y - p.y, ex = s.x - r.x, ey = s.y - r.y;
      if (dist(p, r) < 5 && Math.abs(dx * ey - dy * ex) / (Math.hypot(dx, dy) * Math.hypot(ex, ey) || 1) < 0.2) close = true;
    }
    if (close && !sharedEnds.some((end) => dist(end, p) < end.r)) shared += dist(p, q);
  }
  return crossings * 90 + shared * 1.8;
}

export type SceneConnection = { id: string; a: RoutingPoint; b: RoutingPoint; obstacles: readonly RoutingPoint[] };

/** A bounded scene-wide crossing pass keeps positions fixed and avoids extravagant detours. */
export function planConnectionScene(edges: readonly SceneConnection[], view: View): Map<string, RouteCandidate> {
  const pools = edges.map((edge) => {
    const pool = connectionCandidates(edge.a, edge.b, edge.obstacles, view);
    if (pool.length < 4 || pool[0]!.length > Math.max(1, dist(edge.a, edge.b) - edge.a.r - edge.b.r) * 1.25) {
      const route = visibilityConnection(edge.a, edge.b, edge.obstacles, view);
      if (route) pool.push(route);
    }
    return pool.sort((a, b) => a.cost - b.cost);
  });
  const selected = pools.map((pool) => pool[0]);
  const owners = new Map<RouteCandidate, SceneConnection>();
  pools.forEach((pool, index) => pool.forEach((route) => owners.set(route, edges[index]!)));
  const cache = new Map<RouteCandidate, Map<RouteCandidate, number>>();
  const interference = (a: RouteCandidate, b: RouteCandidate) => {
    const found = cache.get(a)?.get(b);
    if (found !== undefined) return found;
    const ownerA = owners.get(a)!, ownerB = owners.get(b)!;
    const sharedEnds = [ownerA.a, ownerA.b].filter((end) => [ownerB.a, ownerB.b].some((other) => dist(end, other) < 0.01)).map((end) => ({ ...end, r: end.r + Math.max(16, Math.min(52, Math.min(a.length, b.length) * 0.22)) }));
    const value = routeInterference(a.points, b.points, sharedEnds);
    if (!cache.has(a)) cache.set(a, new Map());
    cache.get(a)!.set(b, value);
    return value;
  };
  for (let pass = 0; pass < 3; pass++) {
    let changed = false;
    for (let i = 0; i < selected.length; i++) {
      const pool = pools[i]!;
      if (!pool.length) continue;
      if (pass === 1 && selected[i] && selected.some((other, j) => other && i !== j && interference(selected[i]!, other) >= 60)) {
        const edge = edges[i]!;
        const route = visibilityConnection(edge.a, edge.b, edge.obstacles, view, selected.flatMap((other, j) => other && i !== j ? [other.points] : []));
        if (route && route.length < pool[0]!.length * 1.4 + 20) { pool.push(route); owners.set(route, edge); }
      }
      let best = selected[i]!, score = Infinity;
      for (const candidate of pool) {
        const cost = candidate.cost + selected.reduce((sum, other, j) => sum + (other && i !== j ? interference(candidate, other) : 0), 0);
        if (cost < score - 0.01) { best = candidate; score = cost; }
      }
      if (selected[i] !== best) { selected[i] = best; changed = true; }
    }
    if (!changed) break;
  }
  return new Map(edges.flatMap((edge, index) => selected[index] ? [[edge.id, selected[index]!] as const] : []));
}

export function shortestClearConnection(a: RoutingPoint, b: RoutingPoint, obstacles: readonly RoutingPoint[], view?: View): string | null {
  return connectionCandidates(a, b, obstacles, view)[0]?.d ?? routeAroundRecords(a, b, obstacles, view);
}
