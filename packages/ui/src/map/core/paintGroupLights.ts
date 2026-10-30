import { fitMapGroupLight, type GroupLightLayout } from './groupLight';
import type { MapBounds } from './types';

function paintedBounds(element: SVGGraphicsElement, inverse: DOMMatrix): MapBounds | null {
  if (typeof element.getBBox !== 'function') return null;
  const matrix = element.getCTM();
  if (!matrix) return null;
  const box = element.getBBox();
  if (!box.width && !box.height) return null;
  const transform = inverse.multiply(matrix);
  const points = [
    [box.x, box.y], [box.x + box.width, box.y],
    [box.x, box.y + box.height], [box.x + box.width, box.y + box.height],
  ].map(([x, y]) => ({ x: transform.a * x! + transform.c * y! + transform.e, y: transform.b * x! + transform.d * y! + transform.f }));
  const minX = Math.min(...points.map((point) => point.x)), maxX = Math.max(...points.map((point) => point.x));
  const minY = Math.min(...points.map((point) => point.y)), maxY = Math.max(...points.map((point) => point.y));
  return { id: '', x: (minX + maxX) / 2, y: (minY + maxY) / 2, hw: (maxX - minX) / 2, up: (maxY - minY) / 2, down: (maxY - minY) / 2 };
}

/** Paint after object poses, using actual bodies, names, metadata and complete
 * orbital envelopes. No React updates per frame and no domain membership rules.
 */
export function paintMapGroupLights(scene: SVGSVGElement) {
  const nodes = new Map([...scene.querySelectorAll<SVGGElement>('[data-map-object-id]')].map((node) => [node.getAttribute('data-map-object-id')!, node]));
  for (const group of scene.querySelectorAll<SVGGElement>('[data-map-group-light][data-group-layout]')) {
    const matrix = group.getCTM?.();
    if (!matrix) continue;
    const inverse = matrix.inverse();
    const layout: GroupLightLayout = JSON.parse(group.getAttribute('data-group-layout')!);
    const boxes: MapBounds[] = [...layout.anchors];
    for (const id of layout.members) {
      const node = nodes.get(id);
      if (!node) continue;
      for (const part of node.querySelectorAll<SVGGraphicsElement>('[data-pebble-body], text, [data-metadata-badge], [data-accent-envelope], [data-expanded-ring], [data-map-semantic-emphasis]')) {
        const box = paintedBounds(part, inverse);
        if (box) boxes.push(box);
      }
      const orbit = node.querySelector<SVGGElement>('[data-node-orbit]');
      const orbitMatrix = orbit?.getCTM?.();
      if (orbitMatrix) {
        const transform = inverse.multiply(orbitMatrix);
        const radius = Number(orbit!.getAttribute('data-orbit-extent'));
        const rx = radius * Math.hypot(transform.a, transform.c), ry = radius * Math.hypot(transform.b, transform.d);
        boxes.push({ id, x: transform.e, y: transform.f, hw: rx, up: ry, down: ry });
      }
    }
    const geometry = fitMapGroupLight(boxes, layout.fit);
    if (!geometry) continue;
    for (const ellipse of group.querySelectorAll<SVGEllipseElement>('[data-group-light-shape]')) {
      for (const key of ['cx', 'cy', 'rx', 'ry'] as const) ellipse.setAttribute(key, geometry[key].toFixed(3));
    }
  }
}
