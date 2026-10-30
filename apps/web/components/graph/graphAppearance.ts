import { NEUTRAL_HUE, THEORY_HUE, type ClusterId, type GraphNode } from './graphData';

/** Color inheritance follows explicit capture/expansion anchors, without changing membership. */
export function graphColorConcerns(node: GraphNode, nodes: Readonly<Record<string, GraphNode>>): ClusterId[] {
  let current: GraphNode | undefined = node;
  const seen = new Set<string>();
  while (current && !seen.has(current.id)) {
    seen.add(current.id);
    const concerns = [...new Set([...(current.bridge ?? []), ...(current.cluster ? [current.cluster] : [])])];
    if (concerns.length) return concerns;
    current = current.anchor ? nodes[current.anchor] : undefined;
  }
  return [];
}

export function graphObjectColor(node: GraphNode, nodes: Readonly<Record<string, GraphNode>>, hueOf: (id: ClusterId | undefined) => string): string {
  if (node.lensRole === 'theory') return THEORY_HUE.hue;
  if (node.type === 'external' || node.aggregate) return NEUTRAL_HUE.hue;
  return hueOf(graphColorConcerns(node, nodes)[0]);
}
