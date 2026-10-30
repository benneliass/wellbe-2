"use client";

import { Icon } from '@wellbe/ui';
import type { PointerEvent } from 'react';
import { MapObject, mapObjectHandlers, type MapBadge } from '@wellbe/ui/map';
import { mapBadgeOffset, type BridgeBearing } from '@wellbe/ui/map/core';
import { TYPE_ICON, type GraphNode } from './graphData';
import { canvasLabel, nodeLabelOffset, nodeRadius } from './liveGraphLayout';
import { plural, typeLabelOf } from './graphPresentation';
import { graphAccentProfile, graphObjectShape } from './graphObjectProfiles';
import { presentGraphMiniature } from './graphMiniaturePresentation';
import type { MiniGraphItem } from './graphMiniatures';

export type GraphObjectProps = {
  n: GraphNode; hue: string; bridgeColors?: readonly string[]; bridgeBearings?: readonly BridgeBearing[]; orbitItems: readonly MiniGraphItem[];
  dim: number; hot: boolean; grabbed: boolean; selected: boolean; selectedForShare: boolean; expandedNode: boolean; childCount: number;
  onTogglePin?: () => void; onSelect: () => void; onContext: () => void; onHoverIn: () => void; onHoverOut: () => void; onHoldStart: () => void; onHoldEnd: () => void; onArrow: (key: string) => void;
  onNudge: (key: string, big: boolean) => void; onDragStart: (event: PointerEvent) => void; onDragMove: (event: PointerEvent) => void; onDragEnd: (event: PointerEvent) => void;
};

/** All WellBe-specific semantics and actions are bound here. MapObject renders
 * the result without depending on GraphNode, a router, or a source taxonomy.
 */
export function GraphObject({ n, hue, bridgeColors, bridgeBearings, orbitItems, dim, hot, grabbed, selected, selectedForShare, expandedNode, childCount, ...actions }: GraphObjectProps) {
  const radius = nodeRadius(n), shape = graphObjectShape(n);
  const expandable = childCount > 0 && !expandedNode;
  const type = typeLabelOf(n);
  const label = n.ghost ? `${n.label}, open loop${n.statusNote ? `, ${n.statusNote}` : ''}`
    : `${n.label}, ${type}, ${plural(n.ev, "source")}, first noted ${n.first}${n.bridge && n.lensRole !== 'theory' ? `, shared by ${n.bridge.length} concerns` : ''}${expandable ? `, expandable — ${childCount} related items hidden` : ''}`;
  const badges: MapBadge[] = [];
  if (n.pinned) badges.push({ id: 'pinned', radius: 4.2, offset: mapBadgeOffset(radius, orbitItems.length), color: hue, onActivate: actions.onTogglePin, accessibleLabel: `Unpin ${n.label}`, pressed: true, glyph: <Icon name="star" size={6.5} /> });
  if (n.ghost && TYPE_ICON[n.type] !== 'clock') badges.push({ id: 'open-loop', radius: 4.2, offset: mapBadgeOffset(radius, orbitItems.length, -1), color: hue, fill: 'var(--warning-soft)', glyphColor: '#b45309', glyph: <Icon name="clock" size={6.5} /> });
  return <MapObject objectId={n.id} position={n} radius={radius} accessibleLabel={label}
    data-node="" data-node-id={n.id} data-node-color={hue}
    segmentKeys={n.bridge} segmentBearings={bridgeBearings}
    appearance={{ color: hue, shape, segments: bridgeColors, segmentBearings: bridgeBearings, opacity: shape === 'pebble' ? 0.82 + n.act * 0.18 : 1 }}
    glyph={<Icon name={TYPE_ICON[n.type]} size={13} />}
    accent={graphAccentProfile(n, Boolean(bridgeColors && bridgeColors.length > 1))}
    orbitItems={orbitItems.map(presentGraphMiniature)} badges={badges}
    label={{ text: canvasLabel(n.label), offset: nodeLabelOffset(n), secondary: n.ghost ? { text: 'open loop', color: hue } : n.aggregate ? { text: 'others also track', color: '#64748b' } : undefined }}
    state={{ hot, grabbed, selected, expanded: expandedNode, opacity: dim, emphasis: selectedForShare ? { color: '#0ea5a4', width: 2.4, dash: '4 3' } : undefined }}
    {...mapObjectHandlers({
      activate: actions.onSelect, context: actions.onContext, focus: actions.onHoverIn, blur: actions.onHoverOut,
      holdStart: actions.onHoldStart, holdEnd: actions.onHoldEnd, navigate: actions.onArrow, nudge: actions.onNudge,
      dragStart: actions.onDragStart, dragMove: actions.onDragMove, dragEnd: actions.onDragEnd,
    })}
  />;
}
