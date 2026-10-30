"use client";

import { useId } from 'react';
import type { Point } from './core/types';
import type { GroupLightLayout } from './core/groupLight';

/** Soft grouping is presentation only; the adapter owns group membership. */
export function MapGroupLight({ id, center, radius, color, opacity = 1, blur = 14, intensity = 1, layout }: {
  id: string; center: Point; radius: Point; color: string; opacity?: number; blur?: number; intensity?: number;
  layout?: GroupLightLayout;
}) {
  const paint = `group-${useId().replace(/:/g, '')}`;
  return <g data-map-group-light={id} data-group-layout={layout ? JSON.stringify(layout) : undefined} aria-hidden="true" pointerEvents="none" opacity={opacity} style={{ mixBlendMode: 'multiply' }}>
    <defs>
      <radialGradient id={paint} cx="46%" cy="46%" r="58%"><stop offset="0" stopColor={color} stopOpacity={0.14 * intensity} /><stop offset="0.45" stopColor={color} stopOpacity={0.085 * intensity} /><stop offset="0.78" stopColor={color} stopOpacity={0.028 * intensity} /><stop offset="1" stopColor={color} stopOpacity="0" /></radialGradient>
      <filter id={`${paint}-blur`} x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation={blur} /></filter>
    </defs>
    <ellipse data-group-light={id} data-group-light-shape="" cx={center.x} cy={center.y} rx={radius.x} ry={radius.y} fill={`url(#${paint})`} filter={`url(#${paint}-blur)`} />
    <ellipse data-group-light-outline={id} data-group-light-shape="" cx={center.x} cy={center.y} rx={radius.x} ry={radius.y} fill="none" stroke={color} strokeWidth={1} strokeDasharray="2 7" opacity={0.12} />
  </g>;
}
