import { TYPE_LABEL, type GraphNode, type GraphEdge } from "./graphData";

export function typeLabelOf(n: GraphNode): string {
  return n.typeLabel ?? TYPE_LABEL[n.type];
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** Connection identity describes the relationship, never its position in a
 * filtered view. Live API ids take precedence over the fixture fallback. */
export function graphConnectionId(edge: GraphEdge): string {
  return edge.id ?? JSON.stringify([edge.a, edge.b, edge.f, edge.layer, edge.week]);
}
