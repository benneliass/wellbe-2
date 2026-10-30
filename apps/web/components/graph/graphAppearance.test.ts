import { describe, expect, it } from 'vitest';
import { graphColorConcerns, graphObjectColor } from './graphAppearance';
import { NEUTRAL_HUE, SEED_NODES, THEORY_HUE, type GraphNode } from './graphData';

const sample = (patch: Partial<GraphNode>): GraphNode => ({ ...SEED_NODES[0]!, ...patch });
const hues: Record<string, string> = { head: '#0ea5a4', sleep: '#8b5cf6' };
const hueOf = (id: string | undefined) => hues[id ?? ''] ?? NEUTRAL_HUE.hue;

describe('graph object color inheritance', () => {
  it('uses an explicit anchor palette without claiming new concern membership', () => {
    const parent = sample({ id: 'parent', cluster: 'sleep' });
    const child = sample({ id: 'child', cluster: undefined, anchor: parent.id });
    const nodes = { parent, child };
    expect(graphObjectColor(child, nodes, hueOf)).toBe('#8b5cf6');
    expect(child.cluster).toBeUndefined();
    expect(graphColorConcerns(child, nodes)).toEqual(['sleep']);
  });

  it('honors the child’s own palette before its anchor and keeps bridge concerns', () => {
    const parent = sample({ id: 'parent', cluster: 'sleep' });
    const child = sample({ id: 'child', cluster: undefined, bridge: ['head', 'sleep'], anchor: parent.id });
    expect(graphObjectColor(child, { parent, child }, hueOf)).toBe('#0ea5a4');
    expect(graphColorConcerns(child, { parent, child })).toEqual(['head', 'sleep']);
  });

  it('handles missing and circular anchors and preserves special material meanings', () => {
    const a = sample({ id: 'a', cluster: undefined, anchor: 'b' });
    const b = sample({ id: 'b', cluster: undefined, anchor: 'a' });
    expect(graphColorConcerns(a, { a, b })).toEqual([]);
    expect(graphObjectColor(a, { a }, hueOf)).toBe(NEUTRAL_HUE.hue);
    expect(graphObjectColor({ ...a, lensRole: 'theory' }, { a, b }, hueOf)).toBe(THEORY_HUE.hue);
    expect(graphObjectColor({ ...a, type: 'external', cluster: 'head' }, { a, b }, hueOf)).toBe(NEUTRAL_HUE.hue);
  });
});
