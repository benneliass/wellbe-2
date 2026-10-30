import type { MapBounds } from './types';

export type GroupLightGeometry = { cx: number; cy: number; rx: number; ry: number };
export type GroupLightFit = {
  paddingX: number; paddingY: number;
  minRadiusX: number; minRadiusY: number;
  coverage: number;
};
export type GroupLightLayout = {
  members: readonly string[];
  anchors: readonly MapBounds[];
  fit?: Partial<GroupLightFit>;
};
export const GROUP_LIGHT_FIT: Readonly<GroupLightFit> = Object.freeze({ paddingX: 26, paddingY: 22, minRadiusX: 84, minRadiusY: 64, coverage: 0.9 });

/** Fit the actual member corners into the visible part of a soft ellipse.
 * A bounding rectangle alone is insufficient: its corners can lie outside an
 * ellipse with the same width and height. Preserve the aspect ratio and expand
 * only as far as the actual member footprints require.
 */
export function fitMapGroupLight(boxes: readonly MapBounds[], options: Partial<GroupLightFit> = {}): GroupLightGeometry | null {
  if (!boxes.length) return null;
  const config = { ...GROUP_LIGHT_FIT, ...options };
  const coverage = Math.max(0.1, Math.min(1, config.coverage));
  const minX = Math.min(...boxes.map((box) => box.x - box.hw)), maxX = Math.max(...boxes.map((box) => box.x + box.hw));
  const minY = Math.min(...boxes.map((box) => box.y - box.up)), maxY = Math.max(...boxes.map((box) => box.y + box.down));
  const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
  const rx = Math.max(config.minRadiusX, (maxX - minX) / 2 + config.paddingX);
  const ry = Math.max(config.minRadiusY, (maxY - minY) / 2 + config.paddingY);
  let scale = 1;
  for (const box of boxes) for (const x of [box.x - box.hw, box.x + box.hw]) for (const y of [box.y - box.up, box.y + box.down]) {
    scale = Math.max(scale, Math.hypot((x - cx) / rx, (y - cy) / ry) / coverage);
  }
  // Stable server/browser SVG attributes; rounding outwards preserves coverage.
  const round = (value: number) => Math.round(value * 1000) / 1000;
  const guard = scale > 1 ? 0.002 : 0;
  return { cx: round(cx), cy: round(cy), rx: round(rx * scale + guard), ry: round(ry * scale + guard) };
}
