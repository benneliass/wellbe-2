import { describe, expect, it } from 'vitest';
import { boxesOverlap, GRAPH_ORBIT, graphOrbitExtent, mapBadgeOffset } from '@wellbe/ui/map/core';
import { DESIGN_PREVIEW_MODEL } from './graphData';
import { graphGroupLabels } from './graphGroupLabels';
import { clusterLabelBox, nodeBox } from './liveGraphLayout';

describe('moving group headings and orbital metadata', () => {
  it('moves a heading with its members and yields when a member covers its preferred home', () => {
    const cluster = DESIGN_PREVIEW_MODEL.clusters.find((c) => c.id === 'head')!;
    const nodes = DESIGN_PREVIEW_MODEL.nodes.filter((n) => ['headache', 'light'].includes(n.id));
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const extent = { width: 1800, height: 1400 };
    const preferred = () => ({ x: 300, y: 100 });
    const before = graphGroupLabels([cluster], nodes, byId, (id) => byId[id]!, preferred, extent, {});
    const after = graphGroupLabels([cluster], nodes, byId, (id) => ({ x: byId[id]!.x + 500, y: byId[id]!.y + 300 }), preferred, extent, {});
    expect(after['cluster:head']!.x - before['cluster:head']!.x).toBeCloseTo(500);
    expect(after['cluster:head']!.y - before['cluster:head']!.y).toBeCloseTo(300);
    const position = (id: string) => id === 'light' ? preferred() : byId[id]!;
    const covered = graphGroupLabels([cluster], nodes, byId, position, preferred, extent, {});
    const title = clusterLabelBox(cluster, covered['cluster:head']!.x, covered['cluster:head']!.y);
    for (const node of nodes) expect(boxesOverlap(title, { ...nodeBox(node), ...position(node.id) }, 4)).toBe(false);
  });
  it('enlarges miniatures by 20% and keeps badges beyond every complete orbital sweep', () => {
    expect(GRAPH_ORBIT.itemRadius).toBeCloseTo(3.5 * 1.2);
    for (const radius of [14, 20, 28]) for (const count of [1, 6, 7, 12]) {
      const badge = mapBadgeOffset(radius, count);
      expect(Math.hypot(badge.x, badge.y) - 4.2).toBeGreaterThan(graphOrbitExtent(radius, count) + 3);
    }
  });
});
