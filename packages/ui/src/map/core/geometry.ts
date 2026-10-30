import type { Point, MapBounds } from "./types";

/** Includes interior polyline vertices; parallel/shared runs are scored separately. */
export function segmentCrossing(a: Point, b: Point, c: Point, d: Point): Point | null {
  const rx = b.x - a.x, ry = b.y - a.y, sx = d.x - c.x, sy = d.y - c.y;
  const denominator = rx * sy - ry * sx;
  if (Math.abs(denominator) < 1e-8) return null;
  const t = ((c.x - a.x) * sy - (c.y - a.y) * sx) / denominator;
  const u = ((c.x - a.x) * ry - (c.y - a.y) * rx) / denominator;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1 ? { x: a.x + t * rx, y: a.y + t * ry } : null;
}

/** Relative circular-object/label envelopes used by collision layout policies. */
export function boxesOverlap(a: MapBounds, b: MapBounds, margin = 0): boolean {
  const ox = a.hw + b.hw + margin - Math.abs(a.x - b.x);
  const oy = Math.min(a.y + a.down, b.y + b.down) - Math.max(a.y - a.up, b.y - b.up) + margin;
  return ox > 0 && oy > 0;
}
