import { boxesOverlap, nodeBox, type Box, type Pt } from './liveGraphLayout';
import type { GraphNode } from './graphData';
import type { Positions } from './graphDrag';
import { MAP_MOTION, resolveMapContacts } from '@wellbe/ui/map/core';
import { nodeRadius } from './liveGraphLayout';

type Scene = {
  nodes: readonly GraphNode[];
  moved: Positions;
  titles: readonly Box[];
  extent: { width: number; height: number };
  grabbed?: readonly string[];
  previous?: Readonly<Positions>;
  emphasis?: Readonly<Record<string, number>>;
};
const PAD = 8;
const LEFT = 58; // Match the initial layout's reserved zoom-control strip.
const TOP = PAD * 2; // Match revealMapFamily's usable top inset.

/** Repack the currently visible scene, keeping existing homes whenever they fit.
 * Node boxes include the complete source and related-item orbit envelope.
 * Automatic placements are derived, never written into the person's saved positions.
 */
export function layoutExpandedGraph(scene: Scene) {
  const positions: Positions = {};
  const extent = { ...scene.extent };
  const occupied: Box[] = [...scene.titles];
  const changedBoxes: Box[] = scene.titles.filter((title) => Boolean(scene.moved[title.id]));
  const grabbed = new Set(scene.grabbed);
  if (grabbed.size) {
    const boxes = scene.nodes.map((node) => {
      const home = grabbed.has(node.id) ? scene.moved[node.id] ?? node : scene.previous?.[node.id] ?? scene.moved[node.id] ?? node;
      const box = { ...nodeBox(node), x: home.x, y: home.y };
      const scale = scene.emphasis?.[node.id] ?? 1;
      const growth = nodeRadius(node) * Math.max(0, scale - 1);
      return { ...box, hw: Math.max(box.hw * (1 + (scale - 1) * MAP_MOTION.labelEmphasisFactor), box.up + growth), up: box.up + growth + (scale > 1 || grabbed.has(node.id) ? Math.min(MAP_MOTION.hoverLift, nodeRadius(node) * MAP_MOTION.hoverLiftRadius) : 0), down: box.down + 1 };
    });
    const contacts = resolveMapContacts([...scene.titles, ...boxes], {
      active: grabbed, fixed: new Set([...grabbed, ...scene.titles.map((box) => box.id)]),
      origins: scene.previous, left: LEFT, top: TOP,
    });
    for (const box of boxes) {
      const point = contacts[box.id]!;
      positions[box.id] = point;
      extent.width = Math.max(extent.width, point.x + box.hw + PAD);
      extent.height = Math.max(extent.height, point.y + box.down + PAD);
    }
    return { positions, extent };
  }
  // Initial corridor refinement accepts 4px-clear homes. Requiring the larger
  // expansion gap when a manual move starts can reject those same homes and
  // send an otherwise nearby neighbour to the other side of the group.
  const clearance = Object.keys(scene.moved).length ? 4 : PAD;
  const active = scene.nodes.some((node) => node.deferred) || Object.keys(scene.moved).length > 0;
  if (!active) {
    scene.nodes.forEach((node) => { positions[node.id] = { x: node.x, y: node.y }; });
    return { positions, extent };
  }
  const clear = (box: Box) => box.x - box.hw >= LEFT && box.y - box.up >= TOP &&
    box.x + box.hw <= extent.width - PAD && box.y + box.down <= extent.height - PAD &&
    occupied.every((other) => !boxesOverlap(box, other, clearance));

  const place = (shape: Box, home: Pt, orbit = 0, angle = -Math.PI / 2, held = false): Pt => {
    const at = (point: Pt): Box => ({ ...shape, ...point });
    if (held || !orbit && clear(at(home))) {
      occupied.push(at(home));
      extent.width = Math.max(extent.width, home.x + shape.hw + PAD);
      extent.height = Math.max(extent.height, home.y + shape.down + PAD);
      return { x: home.x, y: home.y };
    }
    if (!orbit) {
      // Slide an obstructed existing record by the actual penetration distance.
      // A coarse radial grid would make its connections jump during a drag.
      const nearby: Pt[] = occupied.flatMap((other) => [
        { x: other.x - other.hw - shape.hw - clearance, y: home.y },
        { x: other.x + other.hw + shape.hw + clearance, y: home.y },
        { x: home.x, y: other.y - other.up - shape.down - clearance },
        { x: home.x, y: other.y + other.down + shape.up + clearance },
      ]);
      nearby.push({ x: Math.max(LEFT + shape.hw, Math.min(extent.width - PAD - shape.hw, home.x)), y: Math.max(TOP + shape.up, Math.min(extent.height - PAD - shape.down, home.y)) });
      nearby.sort((a, b) => Math.hypot(a.x - home.x, a.y - home.y) - Math.hypot(b.x - home.x, b.y - home.y));
      const point = nearby.find((candidate) => clear(at(candidate)));
      if (point) { occupied.push(at(point)); return point; }
    }
    // Search nearby open space before growing the virtual canvas. Candidate order
    // is deterministic, so hovering or selecting does not shuffle the scene.
    for (let growth = 0; ; growth++) {
      const maxRadius = Math.hypot(extent.width, extent.height);
      for (let radius = orbit || 24; radius <= maxRadius; radius += 20) {
        const candidates = Array.from({ length: 32 }, (_, index) => {
          const step = index === 0 ? 0 : Math.ceil(index / 2) * (index % 2 ? 1 : -1);
          const bearing = angle + step * Math.PI / 16;
          return { x: home.x + Math.cos(bearing) * radius, y: home.y + Math.sin(bearing) * radius };
        });
        const point = candidates.find((candidate) => clear(at(candidate)));
        if (point) { occupied.push(at(point)); return point; }
      }
      // Growing both dimensions avoids packing new records into an ever longer column.
      extent.width += Math.max(120, shape.hw * 2 + PAD * 2);
      extent.height += Math.max(120, shape.up + shape.down + PAD * 2);
      if (growth > 100) throw new Error('Map layout could not place a visible object');
    }
  };
  const priority = (node: GraphNode) => grabbed.has(node.id) ? 0 : scene.moved[node.id] ? 1 : 2;
  const roots = scene.nodes.filter((node) => !node.deferred || scene.moved[node.id]);
  roots.sort((a, b) => priority(a) - priority(b));
  for (const node of roots) {
    const home = scene.moved[node.id] ?? scene.previous?.[node.id] ?? node;
    const box = { ...nodeBox(node), ...home };
    // An expansion must not displace the record that was clicked. Established
    // homes are already settled by the initial layout. During a manual move,
    // the moved home wins and obstructed neighbours find another clear home.
    const preserve = scene.moved[node.id]
      ? occupied.slice(scene.titles.length).every((other) => !boxesOverlap(box, other, clearance))
      : changedBoxes.every((other) => !boxesOverlap(box, other, clearance));
    positions[node.id] = place(nodeBox(node), home, 0, -Math.PI / 2, grabbed.has(node.id) || preserve);
    const point = positions[node.id]!;
    if (point.x !== node.x || point.y !== node.y) changedBoxes.push({ ...nodeBox(node), ...point });
  }
  // Deeper anchored children wait for their parent; broken/circular anchors
  // receive a safe ordinary placement rather than disappearing or hanging.
  let pending = scene.nodes.filter((node) => !positions[node.id]);
  while (pending.length) {
    const ready = pending.filter((node) => !node.anchor || positions[node.anchor]);
    for (const node of ready.length ? ready : pending) {
      const anchor = node.anchor ? positions[node.anchor] : undefined;
      positions[node.id] = place(nodeBox(node), anchor ?? node, anchor ? 90 : 0);
    }
    pending = pending.filter((node) => !positions[node.id]);
  }
  return { positions, extent };
}

/** Reveal a newly opened family without resetting a person's chosen pan/zoom. */
export function revealMapFamily(boxes: readonly Box[], zoom: { k: number; tx: number; ty: number }, view: { width: number; height: number }) {
  if (!boxes.length) return zoom;
  const minX = Math.min(...boxes.map((box) => box.x - box.hw)), maxX = Math.max(...boxes.map((box) => box.x + box.hw));
  const minY = Math.min(...boxes.map((box) => box.y - box.up)), maxY = Math.max(...boxes.map((box) => box.y + box.down));
  const k = Math.min(zoom.k, (view.width - LEFT - PAD * 3) / Math.max(1, maxX - minX), (view.height - PAD * 4) / Math.max(1, maxY - minY));
  const clamp = (value: number, lower: number, upper: number) => Math.max(lower, Math.min(upper, value));
  return { k, tx: clamp(zoom.tx, LEFT + PAD - minX * k, view.width - PAD * 2 - maxX * k), ty: clamp(zoom.ty, PAD * 2 - minY * k, view.height - PAD * 2 - maxY * k) };
}
