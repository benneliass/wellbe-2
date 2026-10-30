import type { EvidenceSource } from '@wellbe/ui';
import { TYPE_ICON, type GraphNode, type NodeType, type SourceType } from './graphData';
import { graphObjectShape } from './graphObjectProfiles';
import { RECORD_KINDS } from './recordKinds';

type Identity = { id: string; label: string };
export type ConceptMiniature = Identity & {
  kind: 'concept'; type: NodeType; color: string;
  ghost?: boolean; aggregate?: boolean; lensRole?: 'theory';
};
export type SourceMiniature = Identity & { kind: 'source'; source: SourceType };
export type MiniGraphItem = ConceptMiniature | SourceMiniature;

const SOURCE_STYLE = {
  lab: { type: 'lab', icon: 'flask-conical', color: RECORD_KINDS.result.color, label: 'Lab result' },
  note: { type: 'capture', icon: 'file-text', color: RECORD_KINDS.note.color, label: 'Clinical note' },
  doc: { type: 'capture', icon: 'file-text', color: RECORD_KINDS.document.color, label: 'Document' },
  wearable: { type: 'vital', icon: 'activity', color: RECORD_KINDS.result.color, label: 'Wearable' },
  reported: { type: 'context', icon: 'message-circle', color: RECORD_KINDS.note.color, label: 'Your note' },
  research: { type: 'external', icon: 'globe', color: RECORD_KINDS.other.color, label: 'Reference' },
} satisfies Record<SourceType, { type: NodeType; icon: string; color: string; label: string }>;

/** One source-record list feeds the inspector and orbit. Summary counts and
 * source-kind hints never manufacture individual source records.
 */
export function uniqueGraphEvidence(records: readonly EvidenceSource[]): EvidenceSource[] {
  const seen = new Set<string>();
  return records.filter((record) => {
    if (seen.has(record.id)) return false;
    seen.add(record.id);
    return true;
  });
}

export function graphEvidence(node: GraphNode): EvidenceSource[] {
  return uniqueGraphEvidence(node.evidence ?? []);
}

export function sourceMiniatures(node: GraphNode): SourceMiniature[] {
  return graphEvidence(node).map((record) => {
    const source = record.kind ?? (record.component === 'c16' ? 'research' : 'reported');
    return { kind: 'source', id: `source:${node.id}:${record.id}`, label: record.displayLabel || SOURCE_STYLE[source].label, source };
  });
}

export function conceptMiniature(node: GraphNode, color: string): ConceptMiniature {
  return { kind: 'concept', id: node.id, label: node.label, type: node.type, color, ghost: node.ghost, aggregate: node.aggregate, lensRole: node.lensRole };
}

export function miniatureAppearance(item: MiniGraphItem) {
  if (item.kind === 'source') return { ...SOURCE_STYLE[item.source], shape: 'pebble' as const };
  const shape = graphObjectShape(item);
  return { type: item.type, color: item.color, icon: TYPE_ICON[item.type], shape };
}
