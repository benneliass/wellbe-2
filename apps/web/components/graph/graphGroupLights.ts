import { fitMapGroupLight, type Point } from '@wellbe/ui/map/core';
import type { Cluster, GraphNode } from './graphData';
import { graphColorConcerns } from './graphAppearance';
import { clusterLabelBox, nodeBox } from './liveGraphLayout';

/** Membership is explicit, including shared concerns and inherited child links.
 * This only describes light coverage; it never changes graph layout or meaning.
 */
export function graphGroupLight(cluster: Cluster, visible: readonly GraphNode[], nodes: Readonly<Record<string, GraphNode>>, positionOf: (id: string) => Point, label: Point, overview: boolean) {
  if (overview) return {
    center: { x: cluster.cx, y: cluster.cy }, radius: { x: cluster.rx, y: cluster.ry },
    layout: { members: [`concern:${cluster.id}`], anchors: [], fit: { minRadiusX: cluster.rx, minRadiusY: cluster.ry } },
  };
  const members = visible.filter((node) => graphColorConcerns(node, nodes).includes(cluster.id));
  const anchors = [clusterLabelBox(cluster, label.x, label.y)];
  const boxes = members.map((node) => nodeBox({ ...node, ...positionOf(node.id) }));
  const geometry = fitMapGroupLight([...anchors, ...boxes])!;
  return {
    center: { x: geometry.cx, y: geometry.cy }, radius: { x: geometry.rx, y: geometry.ry },
    layout: { members: members.map((node) => node.id), anchors },
  };
}
