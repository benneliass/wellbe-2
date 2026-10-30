export type TooltipRect = { left: number; top: number; right: number; bottom: number };
const overlap = (a: TooltipRect, b: TooltipRect) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));

/** Find nearby empty space before considering more distant corners of the map. */
export function placeGraphTooltip(anchor: TooltipRect, size: { width: number; height: number }, bounds: { width: number; height: number }, obstacles: TooltipRect[]) {
  const margin = 10, gap = 12;
  const maxX = Math.max(margin, bounds.width - size.width - margin), maxY = Math.max(margin, bounds.height - size.height - margin);
  const cx = (anchor.left + anchor.right) / 2, cy = (anchor.top + anchor.bottom) / 2;
  const candidates = [
    { x: cx - size.width / 2, y: anchor.top - size.height - gap },
    { x: anchor.right + gap, y: cy - size.height / 2 },
    { x: anchor.left - size.width - gap, y: cy - size.height / 2 },
    { x: cx - size.width / 2, y: anchor.bottom + gap },
  ];
  for (let y = margin; y <= maxY + 47; y += 48) for (let x = margin; x <= maxX + 47; x += 48) candidates.push({ x, y });
  let best = { x: margin, y: margin, score: Infinity };
  for (const candidate of candidates) {
    const x = Math.max(margin, Math.min(maxX, candidate.x)), y = Math.max(margin, Math.min(maxY, candidate.y));
    const rect = { left: x, top: y, right: x + size.width, bottom: y + size.height };
    const own = overlap(rect, anchor);
    const collisions = obstacles.reduce((sum, obstacle) => sum + overlap(rect, obstacle), 0);
    const distance = Math.hypot(x + size.width / 2 - cx, y + size.height / 2 - cy);
    const score = own * 1000000 + collisions * 1000 + distance;
    if (score < best.score) best = { x, y, score };
  }
  return { x: best.x, y: best.y };
}
