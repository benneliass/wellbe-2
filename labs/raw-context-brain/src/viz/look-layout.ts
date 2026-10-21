import { mapSettings } from "./settings.js";

export type Point = { x: number; y: number };

const AIR = 42;
// Center distance over the average of the two circle sizes. The empty gap is
// a bit under one circle: long enough to read, short enough that a few steps stay on screen.
export const HOP_DIAMETERS = 1.85;

export type GrowLookInput = {
  stored: ReadonlyMap<string, Point>;
  shownIds: readonly string[];
  latestId: string;
  fullMap: ReadonlyMap<string, Point>;
  radii: ReadonlyMap<string, number>;
  origin?: Point;
};

export function hopLength(parentRadius: number, childRadius: number): number {
  return HOP_DIAMETERS * (parentRadius + childRadius);
}

// The opened look keeps every note that is already placed. A first click seats
// the neighborhood on a short hop. A later click places only notes that were not stored yet.
export function growLook(input: GrowLookInput): Map<string, Point> {
  const shown = unique(input.shownIds);
  const next = new Map<string, Point>();
  const radius = (id: string) => input.radii.get(id) ?? 16;
  const hasStored = shown.some((id) => input.stored.has(id));
  if (!hasStored) {
    const origin = input.origin ?? { x: 0, y: 0 };
    const anchor = shown.includes(input.latestId) ? input.latestId : shown[0];
    if (!anchor) return next;
    next.set(anchor, copy(origin));
    const others = shown.filter((id) => id !== anchor);
    others.forEach((id, index) => {
      const angle = -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(others.length, 1);
      next.set(id, at(origin, angle, hopLength(radius(anchor), radius(id))));
    });
    return next;
  }
  for (const id of shown) {
    const place = input.stored.get(id);
    if (place) next.set(id, copy(place));
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
    const obstacles = [...next.entries()].map(([keptId, point]) => ({
      point,
      radius: radius(keptId),
    }));
    const placed = relaxNewPoint(parent, start, radius(id), obstacles);
    next.set(id, placed);
  });
  return next;
}

// Move only the new note. Stored notes are obstacles and are not returned.
export function relaxNewPoint(
  parent: Point,
  start: Point,
  selfRadius: number,
  obstacles: readonly { point: Point; radius: number }[],
): Point {
  const startAngle = Math.atan2(start.y - parent.y, start.x - parent.x);
  const dist = Math.hypot(start.x - parent.x, start.y - parent.y) || 1;
  const clear = (point: Point) => !blocked(parent, point, selfRadius, obstacles);
  if (clear(start)) return copy(start);
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
  return copy(start);
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

function copy(point: Point): Point {
  return { x: point.x, y: point.y };
}

function copyOrNull(point: Point | undefined): Point | null {
  return point ? copy(point) : null;
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

function blocked(
  parent: Point,
  point: Point,
  selfRadius: number,
  obstacles: readonly { point: Point; radius: number }[],
): boolean {
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
  if (along < mapSettings.linkBand.start || along > mapSettings.linkBand.end) return false;
  const closestX = start.x + abx * along;
  const closestY = start.y + aby * along;
  return Math.hypot(center.x - closestX, center.y - closestY) < radius;
}
