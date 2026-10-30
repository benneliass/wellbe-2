import { boxesOverlap } from './geometry';
import type { MapBounds, Point } from './types';

/** Place labels close to their moving preferred homes, without moving objects. */
export function placeMapLabels(labels: readonly MapBounds[], obstacles: readonly MapBounds[], bounds: { width: number; height: number }, gap = 8): Record<string, Point> {
  const occupied = [...obstacles];
  const positions: Record<string, Point> = {};
  for (const label of labels) {
    const constrain = (p: Point): Point => ({ x: Math.max(label.hw + 16, Math.min(bounds.width - label.hw - 16, p.x)), y: Math.max(label.up + 16, Math.min(bounds.height - label.down - 16, p.y)) });
    const clear = (p: Point) => occupied.every((box) => !boxesOverlap({ ...label, ...p }, box, gap));
    const home = constrain(label);
    const candidates = [home, ...occupied.flatMap((box) => {
      const left = box.x - box.hw - label.hw - gap, right = box.x + box.hw + label.hw + gap;
      const top = box.y - box.up - label.down - gap, bottom = box.y + box.down + label.up + gap;
      return [{ x: home.x, y: top }, { x: home.x, y: bottom }, { x: left, y: home.y }, { x: right, y: home.y }, { x: left, y: top }, { x: right, y: top }, { x: left, y: bottom }, { x: right, y: bottom }].map(constrain);
    })];
    candidates.sort((a, b) => Math.hypot(a.x - home.x, a.y - home.y) - Math.hypot(b.x - home.x, b.y - home.y));
    let position = candidates.find(clear);
    // Dense scenes may need an outside corridor between several obstacles.
    for (let radius = 16; !position && radius < Math.hypot(bounds.width, bounds.height); radius += 16) {
      position = Array.from({ length: 32 }, (_, i) => constrain({ x: home.x + Math.cos(i * Math.PI / 16) * radius, y: home.y + Math.sin(i * Math.PI / 16) * radius })).find(clear);
    }
    position ??= { x: home.x, y: Math.max(label.up + 16, ...occupied.map((box) => box.y + box.down + label.up + gap)) };
    positions[label.id] = position;
    occupied.push({ ...label, ...position });
  }
  return positions;
}
