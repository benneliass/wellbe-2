import { mapObjectRadius } from "./config";
import type { Point } from "./types";
/**
 * Framework-independent constellation and pinned-walk layout policies.
 * The full map settles linked records, then keeps circles and links from covering each other.
 * An opened record stays where it was put. New neighbours take a short hop into the open side.
 * Circle size matches the knowledge graph. The hop and clearance rules match the lab.
 */

export type ConstellationNode = { id: string; degree: number; label?: string };
export type ConstellationLink = { source: string; target: string };

const TURN = 2.399963;
const SPACE = 4096;
const AIR = 42;
const HOP_DIAMETERS = 1.85;
const LINK_BAND = { start: 0.12, end: 0.88 };
const POINT_CAP = 64;
const FITTED_FRACTION = 0.1;

/** Diameter in pixels at zoom 1. Same growth as a knowledge-graph circle. */
export function mapWeightDiameter(degree: number): number {
  return 2 * mapObjectRadius(degree);
}

/** Screen-space fit: the camera does not zoom when a record is opened. */
export function fitMapConstellation(nodes: ConstellationNode[], links: ConstellationLink[], width: number, height: number): Map<string, Point> {
  const placed = placeMapConstellation(nodes, links, width, height);
  const points = [...placed.values()];
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  const spanX = Math.max(...xs) - minX;
  const spanY = Math.max(...ys) - minY;
  const padX = Math.min(135, width * 0.2);
  const padY = 70;
  for (const [id, point] of placed) {
    placed.set(id, {
      x: spanX ? padX + ((point.x - minX) / spanX) * (width - padX * 2) : width / 2,
      y: spanY ? padY + ((point.y - minY) / spanY) * (height - padY * 2 - 30) : height / 2,
    });
  }
  // Fitting the original layout can compress labels even when circles were clear.
  // Resolve the complete visible footprint in the actual viewport, not just discs.
  const scale = width < 600 ? 0.86 : 1.28;
  const halfWidth = (node: ConstellationNode) => Math.max(mapWeightDiameter(node.degree) * scale + 12, Math.min((node.label?.length ?? 12) * (width < 600 ? 7.5 : 9.5), 230) / 2 + 12);
  const radius = (node: ConstellationNode) => mapWeightDiameter(node.degree) * scale;
  for (let pass = 0; pass < 100; pass += 1) {
    let changed = false;
    for (let left = 0; left < nodes.length; left += 1) {
      for (let right = left + 1; right < nodes.length; right += 1) {
        const a = nodes[left]!; const b = nodes[right]!;
        const pa = placed.get(a.id)!; const pb = placed.get(b.id)!;
        const overlapX = halfWidth(a) + halfWidth(b) - Math.abs(pa.x - pb.x);
        const overlapY = Math.min(pa.y + radius(a) + 42, pb.y + radius(b) + 42) - Math.max(pa.y - radius(a) - 12, pb.y - radius(b) - 12);
        if (overlapX <= 0 || overlapY <= 0) continue;
        changed = true;
        if (overlapX < overlapY) {
          const push = (overlapX + 2) / 2 * (pa.x < pb.x ? -1 : 1);
          pa.x += push; pb.x -= push;
        } else {
          const push = (overlapY + 2) / 2 * (pa.y < pb.y ? -1 : 1);
          pa.y += push; pb.y -= push;
        }
      }
    }
    for (const node of nodes) {
      const point = placed.get(node.id)!;
      point.x = Math.max(halfWidth(node), Math.min(width - halfWidth(node), point.x));
      point.y = Math.max(radius(node) + 20, Math.min(height - radius(node) - 44, point.y));
    }
    if (!changed) break;
  }
  return placed;
}

/** Seat only new neighbours, checking the viewport before committing a place.
 * Clamping a radial layout afterwards can collapse several circles onto one edge.
 */
export function growViewportLook(input: {
  stored: ReadonlyMap<string, Point>;
  background?: ReadonlyMap<string, Point>;
  shownIds: readonly string[];
  latestId: string;
  radii: ReadonlyMap<string, number>;
  labelWidths: ReadonlyMap<string, number>;
  width: number;
  height: number;
}): Map<string, Point> {
  const next = new Map(input.stored);
  const parent = next.get(input.latestId);
  if (!parent) return next;
  const radius = (id: string) => input.radii.get(id) ?? 36;
  const halfWidth = (id: string) => Math.max(radius(id) + 12, (input.labelWidths.get(id) ?? 100) / 2 + 10);
  const base = openDirection(parent, [...next.values()]);
  const background = [...(input.background ?? new Map<string, Point>())].filter(([id]) => !input.shownIds.includes(id));
  for (const id of input.shownIds) {
    if (next.has(id)) continue;
    const r = radius(id);
    const hop = hopLength(radius(input.latestId), r);
    let best: Point | null = null;
    let bestScore = Infinity;
    for (let ring = 0; ring < 8; ring += 1) {
      for (let step = 0; step < 32; step += 1) {
        const turn = Math.ceil(step / 2) * (Math.PI / 16) * (step % 2 ? 1 : -1);
        const candidate = at(parent, base + turn, hop + ring * 32);
        if (candidate.x < halfWidth(id) || candidate.x > input.width - halfWidth(id) || candidate.y < r + 16 || candidate.y > input.height - r - 42) continue;
        let penalty = 0;
        for (const [keptId, point] of [...next, ...background]) {
          const horizontal = halfWidth(id) + halfWidth(keptId) - Math.abs(candidate.x - point.x);
          const top = Math.max(candidate.y - r - 12, point.y - radius(keptId) - 12);
          const bottom = Math.min(candidate.y + r + 42, point.y + radius(keptId) + 42);
          if (horizontal > 0 && bottom > top) penalty += horizontal * (bottom - top);
          if (keptId !== input.latestId && segmentHits(parent, candidate, point, radius(keptId) + 12)) penalty += 10000;
        }
        const score = penalty * 1000 + ring * 32 + Math.abs(turn) * 8;
        if (score < bestScore) { best = candidate; bestScore = score; }
      }
      if (bestScore < 1000) break;
    }
    if (best) next.set(id, best);
  }
  return next;
}

export function hopLength(parentRadius: number, childRadius: number): number {
  return HOP_DIAMETERS * (parentRadius + childRadius);
}

/** How large an opened neighbourhood should read. A few hops fit the short side. */
export function worldLookZoom(shorter: number, referenceDiameter: number): number {
  const side = Math.max(320, shorter);
  const hopPx = side / 5.2;
  const diameter = hopPx / HOP_DIAMETERS;
  if (referenceDiameter <= 0) return 1;
  return diameter / referenceDiameter;
}

function spiral(nodes: ConstellationNode[]): Float32Array {
  const positions = new Float32Array(nodes.length * 2);
  const order = nodes
    .map((node, index) => ({ index, degree: node.degree }))
    .sort((left, right) => right.degree - left.degree || left.index - right.index);
  const spacing = nodes.length > 400 ? 68 : 42;
  const core = Math.min(4, order.filter((item) => item.degree >= 30).length);
  order.forEach((item, rank) => {
    const wobble = ((item.index * 0.618) % 1) - 0.5;
    const inCore = rank < core && core > 0;
    const radius = inCore ? spacing * 1.7 : Math.sqrt(Math.max(rank - core, 0)) * spacing * (1 + wobble * 0.12);
    const angle = inCore ? (rank / core) * Math.PI * 2 + wobble * 0.25 : rank * TURN + wobble * 0.55;
    positions[item.index * 2] = Math.cos(angle) * radius;
    positions[item.index * 2 + 1] = Math.sin(angle) * radius;
  });
  return positions;
}

function reservedRadii(flat: Float32Array, sizes: Float32Array, pad: number, width: number, height: number): Float32Array {
  const count = sizes.length;
  const radii = new Float32Array(count);
  const content = Math.max(120, Math.min(width, height) * 0.6);
  const zoom = content / (SPACE * FITTED_FRACTION);
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (let index = 0; index < count; index += 1) {
    const x = flat[index * 2] ?? 0;
    const y = flat[index * 2 + 1] ?? 0;
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  const span = Math.max(maxX - minX, maxY - minY, 1);
  const unit = span / content;
  for (let index = 0; index < count; index += 1) {
    const drawn = Math.min((sizes[index] ?? 28) * zoom, POINT_CAP);
    radii[index] = (drawn / 2 + pad) * unit;
  }
  return radii;
}

function spreadCircles(flat: Float32Array, sizes: Float32Array, width: number, height: number): void {
  const count = sizes.length;
  if (count < 2) return;
  const radii = reservedRadii(flat, sizes, 4, width, height);
  let maxRadius = 1;
  for (let index = 0; index < count; index += 1) {
    if ((radii[index] ?? 0) > maxRadius) maxRadius = radii[index] ?? 1;
  }
  for (let pass = 0; pass < 40; pass += 1) {
    const cell = maxRadius * 2;
    const grid = new Map<string, number[]>();
    for (let index = 0; index < count; index += 1) {
      const bucket = `${Math.floor((flat[index * 2] ?? 0) / cell)}:${Math.floor((flat[index * 2 + 1] ?? 0) / cell)}`;
      const list = grid.get(bucket);
      if (list) list.push(index);
      else grid.set(bucket, [index]);
    }
    let moved = false;
    for (let index = 0; index < count; index += 1) {
      const cx = Math.floor((flat[index * 2] ?? 0) / cell);
      const cy = Math.floor((flat[index * 2 + 1] ?? 0) / cell);
      for (let ox = -1; ox <= 1; ox += 1) {
        for (let oy = -1; oy <= 1; oy += 1) {
          const list = grid.get(`${cx + ox}:${cy + oy}`);
          if (!list) continue;
          for (const other of list) {
            if (other <= index) continue;
            let dx = (flat[other * 2] ?? 0) - (flat[index * 2] ?? 0);
            let dy = (flat[other * 2 + 1] ?? 0) - (flat[index * 2 + 1] ?? 0);
            let dist = Math.hypot(dx, dy);
            const min = (radii[index] ?? 0) + (radii[other] ?? 0);
            if (dist >= min) continue;
            if (dist < 1e-4) {
              const angle = (index + 1) * TURN;
              dx = Math.cos(angle);
              dy = Math.sin(angle);
              dist = 1;
            }
            const push = (min - dist) / 2;
            const ux = (dx / dist) * push;
            const uy = (dy / dist) * push;
            flat[index * 2] = (flat[index * 2] ?? 0) - ux;
            flat[index * 2 + 1] = (flat[index * 2 + 1] ?? 0) - uy;
            flat[other * 2] = (flat[other * 2] ?? 0) + ux;
            flat[other * 2 + 1] = (flat[other * 2 + 1] ?? 0) + uy;
            moved = true;
          }
        }
      }
    }
    if (!moved) break;
  }
}

function segmentsCross(ax: number, ay: number, bx: number, by: number, cx: number, cy: number, dx: number, dy: number): boolean {
  const side = (px: number, py: number, qx: number, qy: number, rx: number, ry: number) =>
    (qy - py) * (rx - qx) - (qx - px) * (ry - qy);
  return side(ax, ay, bx, by, cx, cy) * side(ax, ay, bx, by, dx, dy) < 0 && side(cx, cy, dx, dy, ax, ay) * side(cx, cy, dx, dy, bx, by) < 0;
}

function clearCrossings(flat: Float32Array, pairs: Array<[number, number]>, sizes: Float32Array, width: number, height: number): void {
  const count = flat.length / 2;
  if (count < 2 || pairs.length < 1) return;
  for (let round = 0; round < 8; round += 1) {
    const radii = reservedRadii(flat, sizes, 10, width, height);
    for (const [left, right] of pairs) {
      const ax = flat[left * 2] ?? 0;
      const ay = flat[left * 2 + 1] ?? 0;
      const bx = flat[right * 2] ?? 0;
      const by = flat[right * 2 + 1] ?? 0;
      const abx = bx - ax;
      const aby = by - ay;
      const length2 = abx * abx + aby * aby || 1;
      for (let index = 0; index < count; index += 1) {
        if (index === left || index === right) continue;
        const px = flat[index * 2] ?? 0;
        const py = flat[index * 2 + 1] ?? 0;
        const along = Math.max(0, Math.min(1, ((px - ax) * abx + (py - ay) * aby) / length2));
        if (along < LINK_BAND.start || along > LINK_BAND.end) continue;
        const qx = ax + abx * along;
        const qy = ay + aby * along;
        let dx = px - qx;
        let dy = py - qy;
        let dist = Math.hypot(dx, dy);
        const need = radii[index] ?? 0;
        if (dist >= need) continue;
        if (dist < 1e-3) {
          dx = -aby;
          dy = abx;
          dist = Math.hypot(dx, dy) || 1;
        }
        const push = (need - dist) * 0.72;
        flat[index * 2] = px + (dx / dist) * push;
        flat[index * 2 + 1] = py + (dy / dist) * push;
      }
    }
    for (let first = 0; first < pairs.length; first += 1) {
      for (let second = first + 1; second < pairs.length; second += 1) {
        const [a, b] = pairs[first] ?? [0, 0];
        const [c, d] = pairs[second] ?? [0, 0];
        if (a === c || a === d || b === c || b === d) continue;
        const ax = flat[a * 2] ?? 0;
        const ay = flat[a * 2 + 1] ?? 0;
        const bx = flat[b * 2] ?? 0;
        const by = flat[b * 2 + 1] ?? 0;
        const cx = flat[c * 2] ?? 0;
        const cy = flat[c * 2 + 1] ?? 0;
        const dx = flat[d * 2] ?? 0;
        const dy = flat[d * 2 + 1] ?? 0;
        if (!segmentsCross(ax, ay, bx, by, cx, cy, dx, dy)) continue;
        const abx = bx - ax;
        const aby = by - ay;
        const span = Math.hypot(abx, aby) || 1;
        const step = ((radii[a] ?? 0) + (radii[c] ?? 0)) * 0.08;
        const px = (-aby / span) * step;
        const py = (abx / span) * step;
        flat[a * 2] = ax - px;
        flat[a * 2 + 1] = ay - py;
        flat[b * 2] = bx - px;
        flat[b * 2 + 1] = by - py;
        flat[c * 2] = cx + px;
        flat[c * 2 + 1] = cy + py;
        flat[d * 2] = dx + px;
        flat[d * 2 + 1] = dy + py;
      }
    }
  }
}

function settle(flat: Float32Array, pairs: Array<[number, number]>): void {
  const count = flat.length / 2;
  const ideal = 96;
  const gap = ideal * 0.82;
  const pull = 0.045;
  for (let pass = 0; pass < 14; pass += 1) {
    for (const [left, right] of pairs) {
      let dx = (flat[right * 2] ?? 0) - (flat[left * 2] ?? 0);
      let dy = (flat[right * 2 + 1] ?? 0) - (flat[left * 2 + 1] ?? 0);
      let dist = Math.hypot(dx, dy);
      if (dist < 1e-3) {
        const angle = (left + 1) * TURN;
        dx = Math.cos(angle);
        dy = Math.sin(angle);
        dist = 1;
      }
      const shift = (dist - ideal) * pull * 0.5;
      const ux = (dx / dist) * shift;
      const uy = (dy / dist) * shift;
      flat[left * 2] = (flat[left * 2] ?? 0) + ux;
      flat[left * 2 + 1] = (flat[left * 2 + 1] ?? 0) + uy;
      flat[right * 2] = (flat[right * 2] ?? 0) - ux;
      flat[right * 2 + 1] = (flat[right * 2 + 1] ?? 0) - uy;
    }
    for (let left = 0; left < count; left += 1) {
      for (let right = left + 1; right < count; right += 1) {
        let dx = (flat[right * 2] ?? 0) - (flat[left * 2] ?? 0);
        let dy = (flat[right * 2 + 1] ?? 0) - (flat[left * 2 + 1] ?? 0);
        let dist = Math.hypot(dx, dy);
        if (dist >= gap) continue;
        if (dist < 1e-3) {
          const angle = (left + 1) * TURN;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          dist = 1;
        }
        const push = (gap - dist) * 0.06;
        const ux = (dx / dist) * push;
        const uy = (dy / dist) * push;
        flat[left * 2] = (flat[left * 2] ?? 0) - ux;
        flat[left * 2 + 1] = (flat[left * 2 + 1] ?? 0) - uy;
        flat[right * 2] = (flat[right * 2] ?? 0) + ux;
        flat[right * 2 + 1] = (flat[right * 2 + 1] ?? 0) + uy;
      }
    }
  }
}

function pairsFor(nodes: ConstellationNode[], links: ConstellationLink[]): Array<[number, number]> {
  const indexOf = new Map(nodes.map((node, index) => [node.id, index]));
  const pairs: Array<[number, number]> = [];
  for (const link of links) {
    const left = indexOf.get(link.source);
    const right = indexOf.get(link.target);
    if (left === undefined || right === undefined || left === right) continue;
    pairs.push([left, right]);
  }
  return pairs;
}

/** Settled places for the full map, in layout units. */
export function placeMapConstellation(nodes: ConstellationNode[], links: ConstellationLink[], width: number, height: number): Map<string, Point> {
  const flat = spiral(nodes);
  const sizes = Float32Array.from(nodes.map((node) => mapWeightDiameter(node.degree)));
  const pairs = pairsFor(nodes, links);
  settle(flat, pairs);
  spreadCircles(flat, sizes, width, height);
  clearCrossings(flat, pairs, sizes, width, height);
  spreadCircles(flat, sizes, width, height);
  const placed = new Map<string, Point>();
  nodes.forEach((node, index) => {
    placed.set(node.id, { x: flat[index * 2] ?? 0, y: flat[index * 2 + 1] ?? 0 });
  });
  return placed;
}

export function growWorldLook(input: {
  stored: ReadonlyMap<string, Point>;
  shownIds: readonly string[];
  latestId: string;
  fullMap: ReadonlyMap<string, Point>;
  radii: ReadonlyMap<string, number>;
  origin?: Point;
}): Map<string, Point> {
  const shown = unique(input.shownIds);
  const next = new Map<string, Point>();
  const radius = (id: string) => input.radii.get(id) ?? 16;
  const hasStored = shown.some((id) => input.stored.has(id));
  if (!hasStored) {
    const origin = input.origin ?? { x: 0, y: 0 };
    const anchor = shown.includes(input.latestId) ? input.latestId : shown[0];
    if (!anchor) return next;
    next.set(anchor, { ...origin });
    const others = shown.filter((id) => id !== anchor);
    // The word sits under the circle, so the first hop leaves that side open.
    const awayFromLabel = Math.PI / 2;
    others.forEach((id, index) => {
      const angle = awayFromLabel + (index * 2 * Math.PI) / Math.max(others.length, 1);
      next.set(id, at(origin, angle, hopLength(radius(anchor), radius(id))));
    });
    return next;
  }
  for (const id of shown) {
    const place = input.stored.get(id);
    if (place) next.set(id, { ...place });
  }
  const parent = next.get(input.latestId) ?? copyOrNull(input.fullMap.get(input.latestId));
  if (!parent) return next;
  if (!next.has(input.latestId)) next.set(input.latestId, parent);
  const missing = shown.filter((id) => !next.has(id));
  const base = openDirection(parent, [...next.values()]);
  missing.forEach((id, index) => {
    const spread = missing.length === 1 ? 0 : (index - (missing.length - 1) / 2) * 0.7;
    const dist = hopLength(radius(input.latestId), radius(id));
    const start = at(parent, base + spread, dist);
    const obstacles = [...next.entries()].map(([keptId, point]) => ({ point, radius: radius(keptId) }));
    next.set(id, relaxNewPoint(parent, start, radius(id), obstacles));
  });
  return next;
}

/** Push discs apart in the same units as `flat`. A pinned index stays under the pointer. */
export function separateOverlaps(flat: Float32Array, radii: Float32Array, pinned: ReadonlySet<number>): void {
  const count = radii.length;
  const pad = 6;
  for (let pass = 0; pass < 32; pass += 1) {
    let moved = false;
    for (let left = 0; left < count; left += 1) {
      for (let right = left + 1; right < count; right += 1) {
        if (pinned.has(left) && pinned.has(right)) continue;
        let dx = (flat[right * 2] ?? 0) - (flat[left * 2] ?? 0);
        let dy = (flat[right * 2 + 1] ?? 0) - (flat[left * 2 + 1] ?? 0);
        let dist = Math.hypot(dx, dy);
        const min = (radii[left] ?? 0) + (radii[right] ?? 0) + pad;
        if (dist >= min) continue;
        if (dist < 1e-4) {
          const angle = (left + 1) * TURN;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          dist = 1;
        }
        const share = pinned.has(left) || pinned.has(right) ? 1 : 0.5;
        const push = (min - dist) * share;
        const ux = (dx / dist) * push;
        const uy = (dy / dist) * push;
        if (!pinned.has(left)) {
          flat[left * 2] = (flat[left * 2] ?? 0) - ux;
          flat[left * 2 + 1] = (flat[left * 2 + 1] ?? 0) - uy;
        }
        if (!pinned.has(right)) {
          flat[right * 2] = (flat[right * 2] ?? 0) + ux;
          flat[right * 2 + 1] = (flat[right * 2 + 1] ?? 0) + uy;
        }
        moved = true;
      }
    }
    if (!moved) break;
  }
}

export function layoutWorldScene(input: {
  nodes: ConstellationNode[];
  links: ConstellationLink[];
  path: readonly string[];
  fullPlaces: Map<string, Point>;
  lookPlaces: Map<string, Point>;
  width: number;
  height: number;
}): Float32Array {
  const { nodes, path } = input;
  if (path.length === 0) {
    input.lookPlaces.clear();
    const same = nodes.length > 0 && nodes.every((node) => input.fullPlaces.has(node.id)) && input.fullPlaces.size === nodes.length;
    if (!same) {
      input.fullPlaces.clear();
      for (const [id, point] of placeMapConstellation(nodes, input.links, input.width, input.height)) input.fullPlaces.set(id, point);
    }
    return flatten(nodes, input.fullPlaces);
  }
  const radii = new Map(nodes.map((node) => [node.id, mapWeightDiameter(node.degree) / 2]));
  const tip = path[path.length - 1] ?? nodes[0]?.id ?? "";
  const placed = growWorldLook({
    stored: input.lookPlaces,
    shownIds: nodes.map((node) => node.id),
    latestId: tip,
    fullMap: input.fullPlaces,
    radii,
    origin: { x: SPACE / 2, y: SPACE / 2 },
  });
  input.lookPlaces.clear();
  for (const [id, point] of placed) input.lookPlaces.set(id, point);
  return flatten(nodes, input.lookPlaces);
}

function flatten(nodes: ConstellationNode[], places: Map<string, Point>): Float32Array {
  const flat = new Float32Array(nodes.length * 2);
  nodes.forEach((node, index) => {
    const point = places.get(node.id);
    flat[index * 2] = point?.x ?? 0;
    flat[index * 2 + 1] = point?.y ?? 0;
  });
  return flat;
}

function unique(ids: readonly string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const id of ids) {
    if (seen.has(id)) continue;
    seen.add(id);
    result.push(id);
  }
  return result;
}

function copyOrNull(point: Point | undefined): Point | null {
  return point ? { ...point } : null;
}

function at(origin: Point, angle: number, dist: number): Point {
  return { x: origin.x + Math.cos(angle) * dist, y: origin.y + Math.sin(angle) * dist };
}

function openDirection(parent: Point, placed: Point[]): number {
  const angles = placed
    .filter((point) => Math.hypot(point.x - parent.x, point.y - parent.y) > 1e-3)
    .map((point) => Math.atan2(point.y - parent.y, point.x - parent.x))
    .sort((left, right) => left - right);
  if (angles.length === 0) return -Math.PI / 2;
  let bestGap = -1;
  let bestMid = angles[0] ?? 0;
  for (let index = 0; index < angles.length; index += 1) {
    const current = angles[index] ?? 0;
    const next = index + 1 < angles.length ? (angles[index + 1] ?? 0) : (angles[0] ?? 0) + Math.PI * 2;
    const gap = next - current;
    if (gap > bestGap) {
      bestGap = gap;
      bestMid = current + gap / 2;
    }
  }
  return bestMid;
}

function relaxNewPoint(parent: Point, start: Point, selfRadius: number, obstacles: readonly { point: Point; radius: number }[]): Point {
  const startAngle = Math.atan2(start.y - parent.y, start.x - parent.x);
  const dist = Math.hypot(start.x - parent.x, start.y - parent.y) || 1;
  const clear = (point: Point) => !blocked(parent, point, selfRadius, obstacles);
  if (clear(start)) return { ...start };
  for (let step = 1; step <= 24; step += 1) {
    const turn = Math.ceil(step / 2) * 0.28 * (step % 2 === 0 ? 1 : -1);
    const point = at(parent, startAngle + turn, dist);
    if (clear(point)) return point;
  }
  for (let extra = 1; extra <= 8; extra += 1) {
    for (let step = 0; step <= 24; step += 1) {
      const turn = step === 0 ? 0 : Math.ceil(step / 2) * 0.28 * (step % 2 === 0 ? 1 : -1);
      const point = at(parent, startAngle + turn, dist + extra * AIR);
      if (clear(point)) return point;
    }
  }
  return { ...start };
}

function blocked(parent: Point, point: Point, selfRadius: number, obstacles: readonly { point: Point; radius: number }[]): boolean {
  for (const obstacle of obstacles) {
    if (Math.hypot(obstacle.point.x - parent.x, obstacle.point.y - parent.y) < 1e-3) continue;
    const dist = Math.hypot(point.x - obstacle.point.x, point.y - obstacle.point.y);
    if (dist < selfRadius + obstacle.radius) return true;
    if (segmentHits(parent, point, obstacle.point, obstacle.radius)) return true;
  }
  return false;
}

function segmentHits(start: Point, end: Point, center: Point, radius: number): boolean {
  const abx = end.x - start.x;
  const aby = end.y - start.y;
  const length2 = abx * abx + aby * aby || 1;
  const along = Math.max(0, Math.min(1, ((center.x - start.x) * abx + (center.y - start.y) * aby) / length2));
  if (along < LINK_BAND.start || along > LINK_BAND.end) return false;
  const closestX = start.x + abx * along;
  const closestY = start.y + aby * along;
  return Math.hypot(center.x - closestX, center.y - closestY) < radius;
}
