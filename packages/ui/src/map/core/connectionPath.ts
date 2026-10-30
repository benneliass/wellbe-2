import { shortestClearConnection } from "./routing";
import type { Point } from "./types";

/** Rim-to-rim silk curve. Avoid other circles and their labels when routing. */
type PorcelainPoint = Point & { r: number; labelWidth?: number; labelTop?: number; labelBottom?: number };
export function porcelainLinkPath(
  a: PorcelainPoint,
  b: PorcelainPoint,
  obstacles: readonly (PorcelainPoint & { labelWidth: number; labelOnly?: boolean })[] = [],
  _flex = 0,
  viewport?: { width: number; height: number },
): string {
  const routed = shortestClearConnection(a, b, obstacles, viewport);
  if (routed) return routed;
  // Degenerate/fully blocked scenes retain a finite emergency connector.
  const angle = Math.atan2(b.y - a.y, b.x - a.x);
  const start = { x: a.x + Math.cos(angle) * (a.r + 1), y: a.y + Math.sin(angle) * (a.r + 1) };
  const end = { x: b.x - Math.cos(angle) * (b.r + 1), y: b.y - Math.sin(angle) * (b.r + 1) };
  return `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
}
