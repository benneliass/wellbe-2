/** Obstacle-aware fallback for a silk curve that cannot clear the records. */
import type { MapRoutePoint } from "./types";
export type RoutingPoint = MapRoutePoint;

export function routeAroundRecords(a: RoutingPoint, b: RoutingPoint, others: readonly RoutingPoint[], viewport?: { width: number; height: number }): string | null {
  const obstacles = [...others, a, b];
  const width = viewport?.width ?? Math.max(...obstacles.map((point) => point.x + point.r + 80));
  const height = viewport?.height ?? Math.max(...obstacles.map((point) => point.y + point.r + 80));
  const cell = 12;
  const columns = Math.ceil(width / cell);
  const rows = Math.ceil(height / cell);
  const count = columns * rows;
  const pointAt = (index: number) => ({ x: (index % columns) * cell + cell / 2, y: Math.floor(index / columns) * cell + cell / 2 });
  const blocked = (point: { x: number; y: number }) => {
    if (point.x < 6 || point.x > width - 6 || point.y < 6 || point.y > height - 6) return true;
    return obstacles.some((obstacle) => {
      const margin = obstacle === a || obstacle === b ? 2 : 9;
      const circle = !obstacle.labelOnly && Math.hypot(point.x - obstacle.x, point.y - obstacle.y) < obstacle.r + margin;
      const label = !obstacle.allowUnderLabel && Math.abs(point.x - obstacle.x) < (obstacle.labelWidth ?? 100) / 2 + 9 && point.y > obstacle.y + (obstacle.labelTop ?? obstacle.r + 8) - 5 && point.y < obstacle.y + (obstacle.labelBottom ?? obstacle.r + 34) + 7;
      return circle || label;
    });
  };
  const clearSegment = (from: { x: number; y: number }, to: { x: number; y: number }) => {
    const steps = Math.max(1, Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 3));
    for (let index = 0; index <= steps; index += 1) {
      const t = index / steps;
      if (blocked({ x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t })) return false;
    }
    return true;
  };
  // Side-only attachments cannot describe every clear arc in an opened map.
  // Try the upper rim and diagonals before resorting to a visibility route.
  // Both handles leave radially, so the thread never makes a little elbow at
  // the circle. Keep the lower name area unavailable as an attachment.
  const directions = Array.from({ length: 16 }, (_, index) => {
    const angle = index * Math.PI / 8;
    return { x: Math.cos(angle), y: Math.sin(angle) };
  }).filter((direction) => direction.y < 0.5);
  const span = Math.hypot(b.x - a.x, b.y - a.y);
  let organic: { d: string; score: number } | null = null;
  for (const da of directions) for (const db of directions) {
    const start = { x: a.x + da.x * (a.r + 1), y: a.y + da.y * (a.r + 1) };
    const end = { x: b.x + db.x * (b.r + 1), y: b.y + db.y * (b.r + 1) };
    for (const fraction of [0.28, 0.5, 0.85, 1.2]) {
      const handle = Math.min(260, Math.max(24, span * fraction));
      const c1 = { x: start.x + da.x * handle, y: start.y + da.y * handle };
      const c2 = { x: end.x + db.x * handle, y: end.y + db.y * handle };
      const samples = Math.max(64, Math.ceil((span + handle * 2) / 4));
      let previous = start;
      let previousDirection: { x: number; y: number } | null = null;
      let score = 0;
      let clear = true;
      for (let step = 1; step < samples; step += 1) {
        const t = step / samples, s = 1 - t;
        const point = {
          x: s ** 3 * start.x + 3 * s * s * t * c1.x + 3 * s * t * t * c2.x + t ** 3 * end.x,
          y: s ** 3 * start.y + 3 * s * s * t * c1.y + 3 * s * t * t * c2.y + t ** 3 * end.y,
        };
        if (blocked(point)) { clear = false; break; }
        const direction = { x: point.x - previous.x, y: point.y - previous.y };
        const length = Math.hypot(direction.x, direction.y);
        score += length;
        if (previousDirection) {
          const turn = Math.acos(Math.max(-1, Math.min(1, (direction.x * previousDirection.x + direction.y * previousDirection.y) / (length * Math.hypot(previousDirection.x, previousDirection.y) || 1))));
          // Reject hairpins, rather than merely hiding grid corners with a spline.
          if (turn > 0.16 && length / turn < 18) { clear = false; break; }
          score += turn * 8;
        }
        previous = point; previousDirection = direction;
      }
      score += Math.hypot(end.x - previous.x, end.y - previous.y);
      if (clear && (!organic || score < organic.score)) organic = {
        score,
        d: `M ${start.x} ${start.y} C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${end.x} ${end.y}`,
      };
    }
  }
  if (organic) return organic.d;

  const seeds = (node: RoutingPoint) => {
    const result = new Map<number, { x: number; y: number }>();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, -1], [0, 1]]) {
      const x = node.x + dx! * (node.r + 22);
      const y = node.y + dy! * (node.r + 22);
      const index = Math.floor(y / cell) * columns + Math.floor(x / cell);
      if (index < 0 || index >= count) continue;
      const point = pointAt(index);
      const lead = { x: node.x + dx! * (node.r + 4), y: node.y + dy! * (node.r + 4) };
      if (!blocked(point) && clearSegment(lead, point)) result.set(index, { x: node.x + dx! * (node.r + 1), y: node.y + dy! * (node.r + 1) });
    }
    return result;
  };
  const starts = seeds(a);
  const goals = seeds(b);
  if (!starts.size || !goals.size) return null;
  const distances = new Float64Array(count).fill(Infinity);
  const parents = new Int32Array(count).fill(-1);
  const state = new Uint8Array(count);
  const valid = new Uint8Array(count);
  const open = [...starts.keys()];
  for (const index of open) { distances[index] = 0; state[index] = 1; }
  const goalPoints = [...goals.keys()].map(pointAt);
  const heuristic = (index: number) => {
    const point = pointAt(index);
    return Math.min(...goalPoints.map((goal) => Math.hypot(point.x - goal.x, point.y - goal.y)));
  };
  const canUse = (index: number) => {
    if (valid[index] === 0) valid[index] = blocked(pointAt(index)) ? 2 : 1;
    return valid[index] === 1;
  };
  let found = -1;
  for (let attempts = 0; open.length && attempts < Math.min(count, 20000); attempts += 1) {
    let best = 0;
    for (let index = 1; index < open.length; index += 1) if (distances[open[index]!]! + heuristic(open[index]!) < distances[open[best]!]! + heuristic(open[best]!)) best = index;
    const current = open.splice(best, 1)[0]!;
    if (goals.has(current)) { found = current; break; }
    state[current] = 2;
    const col = current % columns;
    const row = Math.floor(current / columns);
    for (let dx = -1; dx <= 1; dx += 1) for (let dy = -1; dy <= 1; dy += 1) {
      if ((!dx && !dy) || col + dx < 0 || col + dx >= columns || row + dy < 0 || row + dy >= rows) continue;
      const next = current + dy * columns + dx;
      if (state[next] === 2 || !canUse(next)) continue;
      if (dx && dy && (!canUse(current + dx) || !canUse(current + dy * columns))) continue;
      const cost = distances[current]! + cell * Math.hypot(dx, dy);
      if (cost >= distances[next]!) continue;
      distances[next] = cost; parents[next] = current;
      if (state[next] !== 1) { state[next] = 1; open.push(next); }
    }
  }
  if (found < 0) return null;
  const end = goals.get(found)!;
  const points: { x: number; y: number }[] = [];
  let cursor = found;
  while (cursor >= 0) { points.unshift(pointAt(cursor)); if (parents[cursor]! < 0) break; cursor = parents[cursor]!; }
  const start = starts.get(cursor)!;
  const smooth = [points[0]!];
  for (let from = 0; from < points.length - 1;) {
    let to = points.length - 1;
    while (to > from + 1 && !clearSegment(points[from]!, points[to]!)) to -= 1;
    smooth.push(points[to]!); from = to;
  }
  const route = [start, ...smooth, end];
  let d = `M ${start.x} ${start.y}`;
  for (let index = 1; index < route.length - 1; index += 1) {
    const previous = route[index - 1]!; const current = route[index]!; const next = route[index + 1]!;
    const before = Math.hypot(current.x - previous.x, current.y - previous.y) || 1;
    const after = Math.hypot(next.x - current.x, next.y - current.y) || 1;
    const radius = Math.min(48, before * 0.45, after * 0.45);
    const entry = { x: current.x + (previous.x - current.x) * radius / before, y: current.y + (previous.y - current.y) * radius / before };
    const exit = { x: current.x + (next.x - current.x) * radius / after, y: current.y + (next.y - current.y) * radius / after };
    d += ` L ${entry.x} ${entry.y} Q ${current.x} ${current.y} ${exit.x} ${exit.y}`;
  }
  return `${d} L ${end.x} ${end.y}`;
}
