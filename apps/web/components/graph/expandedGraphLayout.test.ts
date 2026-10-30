import { describe, expect, it } from 'vitest';
import { DESIGN_PREVIEW_MODEL } from './graphData';
import { boxesOverlap, clusterLabelBox, COMPACT_VIEW, layoutGraph, nodeBox, WIDE_VIEW } from './liveGraphLayout';
import { layoutExpandedGraph, revealMapFamily } from './expandedGraphLayout';

describe('visible graph expansion layout', () => {
  it('pushes a local contact chain continuously when Light sensitivity reaches Headache', () => {
    const laid = layoutGraph(DESIGN_PREVIEW_MODEL, WIDE_VIEW);
    const nodes = laid.model.nodes.filter((node) => !node.deferred && !node.aggregate && node.layer !== 'investigation' && node.layer !== 'external');
    const light = nodes.find((node) => node.id === 'light')!, headache = nodes.find((node) => node.id === 'headache')!;
    const titles = laid.model.clusters.map((cluster) => clusterLabelBox(cluster, cluster.labelX!, cluster.labelY!));
    let previous = Object.fromEntries(nodes.map((node) => [node.id, { x: node.x, y: node.y }]));
    let worst = 0;
    for (let step = 1; step <= 60; step++) {
      const held = { x: light.x + (headache.x - light.x) * step / 60, y: light.y + (headache.y - light.y) * step / 60 };
      const next = layoutExpandedGraph({ nodes, moved: { light: held }, grabbed: ['light'], previous, titles, extent: laid.extent, emphasis: { light: 1.12, headache: 1.35 } });
      expect(next.positions.light).toEqual(held);
      for (const node of nodes) if (node.id !== 'light') worst = Math.max(worst, Math.hypot(next.positions[node.id]!.x - previous[node.id]!.x, next.positions[node.id]!.y - previous[node.id]!.y));
      const boxes = nodes.map((node) => nodeBox({ ...node, ...next.positions[node.id]! }));
      for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) expect(boxesOverlap(boxes[i]!, boxes[j]!)).toBe(false);
      previous = next.positions;
    }
    expect(worst).toBeLessThan(18);
    const released = layoutExpandedGraph({ nodes, moved: { light: { x: headache.x, y: headache.y } }, previous, titles, extent: laid.extent });
    for (const node of nodes) expect(released.positions[node.id]).toEqual(previous[node.id]);
  });
  it('slides a top-edge neighbour a short distance rather than jumping sideways during a drag', () => {
    const laid = layoutGraph(DESIGN_PREVIEW_MODEL, WIDE_VIEW);
    const nodes = laid.model.nodes.filter((node) => !node.deferred && !node.aggregate && node.layer !== 'investigation' && node.layer !== 'external');
    const headache = nodes.find((node) => node.id === 'headache')!, referral = nodes.find((node) => node.id === 'mri')!;
    let previous = Object.fromEntries(nodes.map((node) => [node.id, { x: node.x, y: node.y }]));
    for (let step = 1; step <= 16; step++) {
      const scene = layoutExpandedGraph({
        nodes, moved: { headache: { x: headache.x + step * 4, y: headache.y } }, grabbed: ['headache'],
        previous, titles: [], extent: laid.extent,
      });
      // Larger miniature/badge envelopes may require more total separation;
      // each actual drag frame must still remain local and continuous.
      expect(Math.hypot(scene.positions.mri!.x - previous.mri!.x, scene.positions.mri!.y - previous.mri!.y)).toBeLessThan(18);
      const box = nodeBox({ ...referral, ...scene.positions.mri! });
      expect(box.y - box.up).toBeGreaterThanOrEqual(16);
      expect(boxesOverlap(box, nodeBox({ ...headache, ...scene.positions.headache! }))).toBe(false);
      previous = scene.positions;
    }
  });
  it.each([WIDE_VIEW, COMPACT_VIEW])('keeps every expanded concept, orbit envelope and title clear in a $width-wide canvas', (view) => {
    const laid = layoutGraph(DESIGN_PREVIEW_MODEL, view);
    const expanded = new Set(['diet', 'nausea', 'fatigue', 'light', 'headache', 'sleep']);
    const nodes = laid.model.nodes.filter((node) => !node.deferred || node.anchor && expanded.has(node.anchor));
    const titles = laid.model.clusters.map((cluster) => clusterLabelBox(cluster, cluster.labelX!, cluster.labelY!));
    const scene = layoutExpandedGraph({ nodes, moved: {}, titles, extent: laid.extent });
    const boxes = [...titles, ...nodes.map((node) => nodeBox({ ...node, ...scene.positions[node.id]! }))];
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) expect(boxesOverlap(boxes[i]!, boxes[j]!)).toBe(false);
    for (const box of boxes.slice(titles.length)) {
      // Initial homes are rounded to tenths of a pixel by the shared layout.
      expect(box.x - box.hw).toBeGreaterThanOrEqual(58 - 0.05);
      expect(box.x + box.hw).toBeLessThanOrEqual(scene.extent.width);
      expect(box.y + box.down).toBeLessThanOrEqual(scene.extent.height);
    }
    expect(layoutExpandedGraph({ nodes, moved: {}, titles, extent: laid.extent })).toEqual(scene);
  });

  it('keeps the dragged object under the pointer and moves a blocked neighbour instead', () => {
    const first = { ...DESIGN_PREVIEW_MODEL.nodes[0]!, id: 'a', x: 200, y: 200, deferred: false };
    const second = { ...first, id: 'b', x: 240, y: 200 };
    const scene = layoutExpandedGraph({ nodes: [first, second], moved: { a: second }, grabbed: ['a'], titles: [], extent: { width: 480, height: 600 } });
    expect(scene.positions.a).toEqual({ x: 240, y: 200 });
    expect(boxesOverlap(nodeBox({ ...first, ...scene.positions.a! }), nodeBox({ ...second, ...scene.positions.b! }))).toBe(false);
  });

  it('grows a crowded canvas and never mutates saved manual homes', () => {
    const nodes = Array.from({ length: 22 }, (_, i) => ({ ...DESIGN_PREVIEW_MODEL.nodes[0]!, id: String(i), x: 100, y: 100, deferred: false }));
    const moved = { '0': { x: 150, y: 150 } };
    const scene = layoutExpandedGraph({ nodes, moved, titles: [], extent: { width: 240, height: 220 } });
    expect(scene.extent.width).toBeGreaterThan(240);
    expect(moved).toEqual({ '0': { x: 150, y: 150 } });
    expect(Object.keys(scene.positions)).toHaveLength(22);
  });

  it('reveals a zoomed expansion and leaves an already visible family unchanged', () => {
    const box = { id: 'family', x: 300, y: 300, hw: 150, up: 130, down: 150 };
    const view = { width: 480, height: 600 };
    const zoom = revealMapFamily([box], { k: 4, tx: -800, ty: -900 }, view);
    expect(zoom.k).toBeLessThan(4);
    expect((box.x - box.hw) * zoom.k + zoom.tx).toBeGreaterThanOrEqual(58);
    expect((box.x + box.hw) * zoom.k + zoom.tx).toBeLessThanOrEqual(view.width);
    expect((box.y + box.down) * zoom.k + zoom.ty).toBeLessThanOrEqual(view.height);
    expect(revealMapFamily([box], zoom, view)).toEqual(zoom);
  });
});
