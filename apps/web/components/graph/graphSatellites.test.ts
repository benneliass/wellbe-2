import { describe, expect, it } from 'vitest';
import { SEED_NODES, type GraphNode } from './graphData';
import { graphEvidence, miniatureAppearance, sourceMiniatures } from './graphMiniatures';
import { indexGraphSatellites, visibleGraphSatellites } from './graphSatellites';
import { GRAPH_ORBIT, graphOrbitExtent, graphOrbitSlots } from '@wellbe/ui/map/core';

const sample = (patch: Partial<GraphNode>): GraphNode => ({ ...SEED_NODES[0]!, ...patch });
const options = { expanded: false, showSources: true, conceptVisible: () => true };

describe('shared graph satellite model', () => {
  it('keeps source identities in orbit while only related concepts expand', () => {
    const parent = sample({ id: 'parent' });
    const child = sample({ id: 'child', anchor: parent.id, deferred: true, evidence: [] });
    const index = indexGraphSatellites([parent, child], () => '#0ea5a4');
    const closed = visibleGraphSatellites(index.parent, options);
    const opened = visibleGraphSatellites(index.parent, { ...options, expanded: true });
    expect(closed.filter((item) => item.kind === 'concept').map((item) => item.id)).toEqual(['child']);
    expect(opened).toEqual(closed.filter((item) => item.kind === 'source'));
    expect(opened).toHaveLength(5);
    expect(visibleGraphSatellites(index.parent, { ...options, showSources: false })).toEqual(closed.filter((item) => item.kind === 'concept'));
    expect(visibleGraphSatellites(index.parent, { ...options, conceptVisible: () => false })).toEqual(opened);
  });

  it('uses actual evidence once, even when records repeat', () => {
    const source = { id: 'kept-record', displayLabel: 'My scan', component: 'c2' as const, kind: 'doc' as const };
    const node = sample({ evidence: [source, source] });
    expect(graphEvidence(node)).toEqual([source]);
    expect(sourceMiniatures(node)).toHaveLength(1);
    expect(sourceMiniatures(node)[0]!.label).toBe('My scan');
    expect(miniatureAppearance(sourceMiniatures(node)[0]!).icon).toBe('file-text');
    expect(sourceMiniatures(sample({ evidence: [], ev: 14, sources: ['doc'] }))).toEqual([]);
    expect(sourceMiniatures(sample({ evidence: undefined, sources: ['doc'] }))).toEqual([]);
    expect(sourceMiniatures(sample({ evidence: [{ id: 'reference', displayLabel: '', component: 'c16' }] }))[0]).toMatchObject({ source: 'research', label: 'Reference' });
  });

  it('shares configurable orbit dimensions between the renderer and layout footprint', () => {
    const config = { ...GRAPH_ORBIT, itemRadius: 4, itemsPerRing: 4, maxItems: 10 };
    const slots = graphOrbitSlots(20, 25, config);
    expect(slots).toHaveLength(10);
    expect(new Set(slots.map((slot) => slot.distance)).size).toBe(3);
    const extent = graphOrbitExtent(20, 25, config);
    for (const slot of slots) {
      expect(Math.hypot(slot.x, slot.y) + slot.itemRadius).toBeLessThan(extent);
      expect(slot.distance - slot.itemRadius).toBeGreaterThan(20 * 1.08);
    }
    expect(graphOrbitSlots(20, 5, { ...config, maxItems: 0 })).toEqual([]);
    expect(() => graphOrbitSlots(20, 5, { ...config, itemsPerRing: 0 })).toThrow('Invalid graph orbit');
  });
});
