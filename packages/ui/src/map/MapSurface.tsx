"use client";

import { useId } from 'react';
import { LivingPebbleSurface } from './LivingPebbleSurface';
import { pebblePalette, porcelainTint } from './core/material';
import { MapShapeGeometry } from './MapShapeGeometry';
import { MapEdgeFlow } from './MapEdgeFlow';
import type { MapShape, MapSurfaceAppearance } from './visualTypes';

type Detail = 'full' | 'miniature';

/** The same object taxonomy at both detail levels. Tiny objects use only the
 * glaze details that remain visible at that size, avoiding expensive filters.
 */
export function MapSurface({ radius, appearance, detail = 'full' }: {
  radius: number;
  appearance: MapSurfaceAppearance;
  detail?: Detail;
}) {
  const id = `surface-${useId().replace(/:/g, '')}`;
  const { color, shape = 'pebble', segments, segmentBearings, opacity = 1 } = appearance;

  if (detail === 'full' && shape === 'pebble') {
    return (
      <g data-map-surface={shape} opacity={opacity}>
        <LivingPebbleSurface radius={radius} color={color} segments={segments} segmentBearings={segmentBearings} />
      </g>
    );
  }

  const miniature = detail === 'miniature';
  const paint = pebblePalette(color);
  const filled = shape === 'pebble' || shape === 'diamond';
  const shadow = !miniature && (shape === 'diamond' || shape === 'open-loop');
  const stops = miniature
    ? [{ at: 0, color: paint.light }, { at: 0.35, color: paint.crown }, { at: 0.72, color: paint.body }, { at: 1, color: paint.base }]
    : [{ at: 0, color: '#fff', opacity: 0.92 }, { at: 0.34, color: porcelainTint(color, 0.74) }, { at: 0.72, color: porcelainTint(color, 0.68) }, { at: 1, color: porcelainTint(color, 0.35) }];

  return (
    <g data-map-surface={shape} opacity={opacity}>
      <defs>
        {filled && (
          <radialGradient id={id} cx={miniature ? '28%' : '34%'} cy={miniature ? '18%' : '28%'} r={miniature ? '75%' : '78%'}>
            {stops.map((stop) => <stop key={stop.at} offset={stop.at} stopColor={stop.color} stopOpacity={'opacity' in stop ? stop.opacity : undefined} />)}
          </radialGradient>
        )}
        {shadow && (
          <filter id={`${id}-shadow`} x="-40%" y="-40%" width="180%" height="180%">
            <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#0f172a" floodOpacity="0.18" />
          </filter>
        )}
      </defs>
      {miniature && <ellipse cx={radius * 0.08} cy={radius * 0.95} rx={radius * 0.85} ry={radius * 0.18} fill="#31434a" opacity="0.17" />}
      <g data-pebble-body={miniature ? undefined : ''}>
        {!miniature && <circle data-pebble-bounds="" r={radius} fill="transparent" pointerEvents="none" />}
        <SurfaceBody radius={radius} color={color} shape={shape} detail={detail} paintId={id} />
        {!miniature && <MapEdgeFlow radius={radius} shape={shape} />}
        {miniature && filled && <ellipse cx={-radius * 0.3} cy={-radius * 0.46} rx={radius * 0.22} ry={radius * 0.35} transform="rotate(38)" fill="#fff" opacity="0.33" />}
      </g>
    </g>
  );
}

function SurfaceBody({ radius, color, shape, detail, paintId }: {
  radius: number; color: string; shape: MapShape; detail: Detail; paintId: string;
}) {
  const miniature = detail === 'miniature';
  if (shape === 'open-loop' || shape === 'comparison') {
    const comparison = shape === 'comparison';
    return (
      <MapShapeGeometry radius={radius} shape={shape} miniature={miniature}
        fill={miniature ? '#fcfdff' : comparison ? 'var(--bg-subtle, #f1f5f9)' : 'var(--bg-surface, #fff)'}
        stroke={!miniature && comparison ? '#94a3b8' : color}
        strokeWidth={miniature ? 0.55 : comparison ? 1.6 : 1.8}
        strokeDasharray={miniature ? comparison ? '0.4 1' : '1 1' : comparison ? '2 3' : '3 3'}
        opacity={!miniature && comparison ? 0.85 : 1}
        filter={!miniature && !comparison ? `url(#${paintId}-shadow)` : undefined}
      />
    );
  }
  if (shape === 'diamond') {
    return (
      <MapShapeGeometry radius={radius} shape={shape} miniature={miniature}
        fill={`url(#${paintId})`} opacity={miniature ? 1 : 0.9}
        filter={miniature ? undefined : `url(#${paintId}-shadow)`}
      />
    );
  }
  return <MapShapeGeometry radius={radius} shape={shape} miniature={miniature} data-mini-silhouette="" fill={`url(#${paintId})`} stroke={pebblePalette(color).light} strokeWidth="5" />;
}
