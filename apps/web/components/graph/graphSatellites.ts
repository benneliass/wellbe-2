import type { GraphNode } from './graphData';
import { conceptMiniature, sourceMiniatures, type ConceptMiniature, type MiniGraphItem, type SourceMiniature } from './graphMiniatures';

export type GraphSatellites = { sources: readonly SourceMiniature[]; related: readonly ConceptMiniature[] };

export function indexGraphSatellites(nodes: readonly GraphNode[], colorOf: (node: GraphNode) => string): Record<string, GraphSatellites> {
  const index: Record<string, { sources: SourceMiniature[]; related: ConceptMiniature[] }> = {};
  for (const node of nodes) index[node.id] = { sources: sourceMiniatures(node), related: [] };
  for (const node of nodes) if (node.deferred && node.anchor && index[node.anchor]) index[node.anchor]!.related.push(conceptMiniature(node, colorOf(node)));
  return index;
}

/** Sources remain attached to their parent. Only related concepts can become
 * standalone map objects. Interleave previews so neither category hides the other.
 */
export function visibleGraphSatellites(items: GraphSatellites | undefined, options: { expanded: boolean; showSources: boolean; conceptVisible: (id: string) => boolean }): MiniGraphItem[] {
  const sources = options.showSources ? items?.sources ?? [] : [];
  const related = options.expanded ? [] : (items?.related ?? []).filter((item) => options.conceptVisible(item.id));
  return Array.from({ length: Math.max(sources.length, related.length) }, (_, index) => [sources[index], related[index]])
    .flat().filter((item): item is MiniGraphItem => Boolean(item));
}
