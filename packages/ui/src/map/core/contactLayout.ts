import type { MapBounds, MapPositions } from './types';

type ContactOptions = {
  active: ReadonlySet<string>;
  fixed: ReadonlySet<string>;
  origins?: Readonly<MapPositions>;
  left: number; top: number;
  clearance?: number; iterations?: number;
};

/** Warm-started local contact projection. A held object moves immediately;
 * touching neighbours share the minimum separation and pass contact onward.
 * Unlike a free-space search this never chooses a distant new home/corridor.
 */
export function resolveMapContacts(input: readonly MapBounds[], options: ContactOptions): MapPositions {
  const boxes = input.map((box) => ({ ...box }));
  const affected = new Set(options.active);
  const gap = options.clearance ?? 4;
  for (let pass = 0; pass < (options.iterations ?? 96); pass++) {
    let penetration = 0;
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i]!, b = boxes[j]!;
      if (!affected.has(a.id) && !affected.has(b.id)) continue;
      const aFixed = options.fixed.has(a.id), bFixed = options.fixed.has(b.id);
      if (aFixed && bFixed) continue;
      const ox = a.hw + b.hw + gap - Math.abs(b.x - a.x);
      const oy = Math.min(a.y + a.down, b.y + b.down) - Math.max(a.y - a.up, b.y - b.up) + gap;
      if (ox <= 0.01 || oy <= 0.01) continue;
      penetration = Math.max(penetration, Math.min(ox, oy));
      const aShare = aFixed ? 0 : bFixed ? 1 : 0.5;
      const bShare = bFixed ? 0 : aFixed ? 1 : 0.5;
      if (ox < oy) {
        const direction = Math.sign(b.x - a.x || (options.origins?.[b.id]?.x ?? b.x) - (options.origins?.[a.id]?.x ?? a.x) || 1);
        a.x -= direction * (ox + 0.02) * aShare;
        b.x += direction * (ox + 0.02) * bShare;
      } else {
        const direction = Math.sign(b.y + (b.down - b.up) / 2 - a.y - (a.down - a.up) / 2 || (options.origins?.[b.id]?.y ?? b.y) - (options.origins?.[a.id]?.y ?? a.y) || 1);
        a.y -= direction * (oy + 0.02) * aShare;
        b.y += direction * (oy + 0.02) * bShare;
      }
      if (!aFixed) affected.add(a.id);
      if (!bFixed) affected.add(b.id);
    }
    for (const box of boxes) if (affected.has(box.id) && !options.fixed.has(box.id)) {
      box.x = Math.max(options.left + box.hw, box.x);
      box.y = Math.max(options.top + box.up, box.y);
    }
    if (penetration < 0.02) break;
  }
  return Object.fromEntries(boxes.map(({ id, x, y }) => [id, { x, y }]));
}
