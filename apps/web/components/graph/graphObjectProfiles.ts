import type { MapAccentProfile, MapShape } from '@wellbe/ui/map';
import type { GraphNode, NodeType } from './graphData';

/** WellBe meanings select toolkit characteristics; the renderer knows none of
 * these record families. Every declared family has an explicit profile.
 */
const PROFILES = {
  symptom: { kind: 'none', period: 64000, dash: '18 82' },
  context: { kind: 'none', period: 76000, dash: '28 72' },
  pending: { kind: 'open-loop', period: 80000, dash: '3 7' },
  lab: { kind: 'none', period: 68000, dash: '12 38' },
  vital: { kind: 'none', period: 72000, dash: '20 30' },
  visit: { kind: 'none', period: 82000, dash: '24 76' },
  capture: { kind: 'none', period: 88000, dash: '32 68' },
  theory: { kind: 'diamond', period: 90000, dash: '16 34' },
  investigation: { kind: 'diamond', period: 84000, dash: '10 15' },
  external: { kind: 'external', period: 96000, dash: '30 70' },
} satisfies Record<NodeType, MapAccentProfile>;

type Traits = Pick<GraphNode, 'type' | 'ghost' | 'aggregate' | 'lensRole'>;
export function graphObjectShape(node: Traits): MapShape {
  return node.ghost ? 'open-loop' : node.aggregate ? 'comparison' : node.lensRole === 'theory' || node.type === 'theory' || node.type === 'investigation' ? 'diamond' : 'pebble';
}

export function graphAccentProfile(node: Traits, segmented = false): MapAccentProfile {
  const profile = PROFILES[node.type];
  const kind = node.ghost ? 'open-loop' : node.aggregate ? 'comparison' : node.lensRole === 'theory' ? 'diamond' : segmented ? 'bridge' : profile.kind;
  return { ...profile, kind, type: node.type };
}
