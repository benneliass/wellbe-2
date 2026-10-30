import { TYPE_LABEL, type GraphNode } from "./graphData";

export function typeLabelOf(n: GraphNode): string {
  return n.typeLabel ?? TYPE_LABEL[n.type];
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}
