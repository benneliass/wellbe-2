import { describe, expect, it } from 'vitest';
import { fitMapGroupLight, type MapBounds } from '@wellbe/ui/map/core';
import { DESIGN_PREVIEW_MODEL } from './graphData';
import { graphGroupLight } from './graphGroupLights';
import { nodeBox } from './liveGraphLayout';

const corners = (box: MapBounds) => [box.x - box.hw, box.x + box.hw].flatMap((x) => [box.y - box.up, box.y + box.down].map((y) => ({ x, y })));

describe('group light coverage', () => {
  it('covers actual diagonal member footprints inside the visible band of the ellipse', () => {
    const boxes = [
      { id: 'north-west', x: 20, y: 20, hw: 45, up: 30, down: 55 },
      { id: 'south-east', x: 500, y: 400, hw: 60, up: 40, down: 70 },
      { id: 'name', x: 260, y: -30, hw: 90, up: 16, down: 24 },
    ];
    const light = fitMapGroupLight(boxes)!;
    for (const box of boxes) for (const p of corners(box)) expect(Math.hypot((p.x - light.cx) / light.rx, (p.y - light.cy) / light.ry)).toBeLessThanOrEqual(0.900001);
    expect(fitMapGroupLight([])).toBeNull();
    const small = fitMapGroupLight([{ id: 'one', x: 0, y: 0, hw: 10, up: 10, down: 10 }])!;
    expect(small.rx).toBe(84); expect(small.ry).toBe(64);
  });

  it('includes shared objects and inherited visible children, and follows distant manual positions', () => {
    const model = DESIGN_PREVIEW_MODEL;
    const head = model.clusters.find((cluster) => cluster.id === 'head')!;
    const nodes = model.nodes.filter((node) => ['headache', 'dizzy', 'glare', 'light', 'nausea'].includes(node.id));
    const byId = Object.fromEntries(model.nodes.map((node) => [node.id, node]));
    const position = (id: string) => id === 'light' ? { x: 1000, y: 700 } : byId[id]!;
    const light = graphGroupLight(head, nodes, byId, position, { x: 200, y: 20 }, false);
    expect(new Set(light.layout.members)).toEqual(new Set(['headache', 'light', 'dizzy', 'glare']));
    expect(light.layout.members).not.toContain('nausea');
    const box = nodeBox({ ...byId.light!, ...position('light') });
    for (const p of corners(box)) expect(Math.hypot((p.x - light.center.x) / light.radius.x, (p.y - light.center.y) / light.radius.y)).toBeLessThanOrEqual(0.900001);
    const sleep = model.clusters.find((cluster) => cluster.id === 'sleep')!;
    expect(graphGroupLight(sleep, nodes, byId, position, { x: 400, y: 20 }, false).layout.members).toContain('dizzy');
  });
});
