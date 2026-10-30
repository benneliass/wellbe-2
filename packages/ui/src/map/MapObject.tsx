"use client";

import type { ReactNode, SVGProps } from 'react';
import type { Point } from './core/types';
import { serializeSegmentBearings, type BridgeBearing } from './core/segments';
import { pebblePalette } from './core/material';
import { GRAPH_ORBIT, graphOrbitExtent, graphOrbitLabelOffset, type GraphOrbitConfig } from './core/orbit';
import { MAP_MOTION } from './core/config';
import { MapSurface } from './MapSurface';
import { MapOrbit } from './MapOrbit';
import { MapAccents } from './MapAccents';
import type { MapAccentProfile, MapBadge, MapMiniatureItem, MapSurfaceAppearance, MapVisualState } from './visualTypes';
import styles from './MapVisuals.module.css';

export type MapObjectFrameProps = Omit<SVGProps<SVGGElement>, 'opacity'> & {
  objectId: string; position: Point; radius: number; accessibleLabel: string;
  state?: MapVisualState; segmentKeys?: readonly string[]; segmentBearings?: readonly BridgeBearing[];
};

/** The DOM contract used by effects, connections and accessibility. Application
 * actions and data attributes are forwarded; the toolkit has no navigation policy.
 */
export function MapObjectFrame({ objectId, position, radius, accessibleLabel, state = {}, segmentKeys, segmentBearings, className, children, ...interaction }: MapObjectFrameProps) {
  return <g role="button" tabIndex={0} aria-label={accessibleLabel} aria-pressed={state.selected}
    {...interaction} className={[styles.node, className].filter(Boolean).join(' ')}
    data-map-object-id={objectId} data-pebble-node="" data-pebble-key={objectId}
    data-pebble-x={position.x} data-pebble-y={position.y} data-pebble-radius={radius}
    data-pebble-hot={Boolean(state.hot || state.grabbed)} data-pebble-grabbed={Boolean(state.grabbed)}
    data-map-selected={Boolean(state.selected)} data-map-expanded={Boolean(state.expanded)}
    data-map-segment-keys={segmentKeys ? JSON.stringify(segmentKeys) : undefined}
    data-map-segment-fallback={segmentKeys ? serializeSegmentBearings(segmentBearings) : undefined}
    opacity={state.opacity ?? 1}>{children}</g>;
}

export function MapFocusRing({ position, radius }: { position: Point; radius: number }) {
  return <circle className={styles.focusRing} cx={position.x} cy={position.y} r={radius} />;
}

export function MapObjectBadge({ badge, position }: { badge: MapBadge; position: Point }) {
  const r = badge.radius ?? 7.5;
  return <g data-metadata-badge={badge.id} data-badge-offset-x={badge.offset.x} data-badge-offset-y={badge.offset.y} className={styles.metadataBadge} transform={`translate(${position.x + badge.offset.x} ${position.y + badge.offset.y})`} role={badge.onActivate ? 'button' : undefined} tabIndex={badge.onActivate ? 0 : undefined} aria-label={badge.accessibleLabel} aria-pressed={badge.pressed}
    onPointerDown={badge.onActivate ? (event) => event.stopPropagation() : undefined}
    onPointerUp={badge.onActivate ? (event) => event.stopPropagation() : undefined}
    onClick={badge.onActivate ? (event) => { event.stopPropagation(); badge.onActivate!(); } : undefined}
    onKeyDown={badge.onActivate ? (event) => { event.stopPropagation(); if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); badge.onActivate!(); } } : undefined}
    style={{ pointerEvents: badge.onActivate ? 'all' : 'none', color: badge.color }}>
    <circle data-badge-glint="" className={styles.badgeGlint} r={r} fill="none" stroke={badge.color} strokeWidth="3" opacity="0.12" />
    <circle r={r} fill={badge.fill ?? 'var(--bg-surface, #fff)'} stroke={badge.color} strokeWidth="1" />
    <foreignObject x="-6" y="-6" width="12" height="12"><span className={styles.glyph} style={{ color: badge.glyphColor ?? badge.color }}>{badge.glyph}</span></foreignObject>
  </g>;
}

export function MapObjectLabel({ position, radius, text, offset = 16, secondary }: {
  position: Point; radius: number; text: string; offset?: number; secondary?: { text: string; color: string; gap?: number };
}) {
  return <g data-map-label="" data-label-anchor-x={position.x} data-label-anchor-y={position.y + radius + offset} pointerEvents="none">
    <text className={styles.nodeLabel} x={position.x} y={position.y + radius + offset} textAnchor="middle">{text}</text>
    {secondary && <text className={styles.ghostLabel} x={position.x} y={position.y + radius + offset + (secondary.gap ?? 14)} textAnchor="middle" fill={secondary.color}>{secondary.text}</text>}
  </g>;
}

export type MapObjectProps = MapObjectFrameProps & {
  appearance: MapSurfaceAppearance; glyph: ReactNode; hitRadius?: number;
  accent?: MapAccentProfile; orbitItems?: readonly MapMiniatureItem[]; badges?: readonly MapBadge[];
  orbitConfig?: Readonly<GraphOrbitConfig>;
  label?: { text: string; offset?: number; secondary?: { text: string; color: string; gap?: number } };
};

/** Compose independently reusable frame, surface, glyph, accents, badges and
 * label. Distinct object characteristics are data, not parallel renderers.
 */
export function MapObject({ appearance, glyph, hitRadius, accent, orbitItems = [], orbitConfig = GRAPH_ORBIT, badges = [], label, ...frame }: MapObjectProps) {
  const { position: p, radius: r, state = {} } = frame;
  const labelOffset = label?.offset ?? Math.max(
    graphOrbitLabelOffset(orbitItems.length, orbitConfig),
    orbitItems.length ? graphOrbitExtent(r, orbitItems.length, orbitConfig) + r * (MAP_MOTION.selectedScale - 1) - r + 12 : 16,
  );
  return <MapObjectFrame {...frame} data-map-body-focus="">
    <g className={styles.porcelainObject} data-pebble-object="">
      <MapFocusRing position={p} radius={r + 15} />
      <circle data-map-hit-area="" cx={p.x} cy={p.y} r={Math.max(r, hitRadius ?? r)} fill="transparent" />
      {state.emphasis && <circle data-map-semantic-emphasis="" cx={p.x} cy={p.y} r={r + 12} fill="none" stroke={state.emphasis.color} strokeWidth={state.emphasis.width ?? 1.4} opacity={0.6} strokeDasharray={state.emphasis.dash} />}
      <g transform={`translate(${p.x} ${p.y})`}><g data-map-volume="" className={styles.objectVolume} style={{ color: appearance.color }}>
        <MapSurface radius={r} appearance={appearance} />
        <g style={{ pointerEvents: 'none' }}><g data-pebble-face=""><g transform="translate(-7 -7)"><foreignObject width="14" height="14"><span className={`${styles.glyph} ${styles.pebbleGlyph}`} style={{ color: pebblePalette(appearance.color).ink }}>{glyph}</span></foreignObject></g></g></g>
      </g></g>
      {accent && <MapAccents x={p.x} y={p.y} radius={r} color={appearance.color} profile={accent} segments={appearance.segments} bearings={appearance.segmentBearings}><MapOrbit radius={r} items={orbitItems} config={orbitConfig} /></MapAccents>}
      {!accent && orbitItems.length > 0 && <g transform={`translate(${p.x} ${p.y})`} data-node-accents="orbit" aria-hidden="true" pointerEvents="none"><MapOrbit radius={r} items={orbitItems} config={orbitConfig} /></g>}
      {badges.map((badge) => <MapObjectBadge key={badge.id} badge={badge} position={p} />)}
      {label && <MapObjectLabel position={p} radius={r} {...label} offset={labelOffset} />}
    </g>
  </MapObjectFrame>;
}
