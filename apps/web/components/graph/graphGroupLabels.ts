import { MAP_MOTION, placeMapLabels, type Point } from '@wellbe/ui/map/core';
import { graphColorConcerns } from './graphAppearance';
import type { Cluster, GraphNode } from './graphData';
import { clusterLabelBox, nodeBox, nodeRadius } from './liveGraphLayout';

/** Headings follow the group's displacement; labels yield to objects, not vice versa. */
export function graphGroupLabels(clusters: readonly Cluster[], visible: readonly GraphNode[], nodes: Readonly<Record<string, GraphNode>>, positionOf: (id: string) => Point, preferred: (cluster: Cluster) => Point, extent: { width: number; height: number }, manual: Readonly<Record<string, Point>>) {
  const labels = clusters.map((cluster) => {
    const members = visible.filter((node) => graphColorConcerns(node, nodes).includes(cluster.id));
    const home = preferred(cluster);
    const delta = members.reduce((sum, node) => ({ x: sum.x + positionOf(node.id).x - node.x, y: sum.y + positionOf(node.id).y - node.y }), { x: 0, y: 0 });
    const point = manual[`cluster:${cluster.id}`] ?? { x: home.x + delta.x / Math.max(1, members.length), y: home.y + delta.y / Math.max(1, members.length) };
    return clusterLabelBox(cluster, point.x, point.y);
  });
  const obstacles = visible.map((node) => {
    const box = { ...nodeBox(node), ...positionOf(node.id) };
    const growth = nodeRadius(node) * (MAP_MOTION.selectedScale - 1) + 4;
    return { ...box, hw: Math.max(box.hw * 1.06, box.up + growth), up: box.up + growth, down: box.down + 4 };
  });
  return placeMapLabels(labels, obstacles, extent);
}
