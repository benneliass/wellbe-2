import type { SVGProps } from 'react';
import { PEBBLE_OUTLINE } from './core/material';
import type { MapDataAttributes, MapShape } from './visualTypes';

type Paint = Pick<SVGProps<SVGElement>, 'id' | 'className' | 'fill' | 'stroke' | 'strokeWidth' | 'strokeDasharray' | 'strokeLinecap' | 'opacity' | 'filter' | 'pathLength' | 'vectorEffect'> & MapDataAttributes;

/** Body paint and edge light share the exact same geometry, including corners. */
export function MapShapeGeometry({ radius, shape, miniature = false, ...paint }: Paint & { radius: number; shape: MapShape; miniature?: boolean }) {
  if (shape === 'open-loop' || shape === 'comparison') return <circle r={radius * (miniature ? 0.95 : 1)} {...paint} />;
  if (shape === 'diamond') {
    const half = radius * (miniature ? 0.68 : 1);
    return <rect x={-half} y={-half} width={half * 2} height={half * 2} rx={miniature ? radius * 0.2 : 6} transform="rotate(45)" {...paint} />;
  }
  return <path d={PEBBLE_OUTLINE} transform={`scale(${radius / 100})`} {...paint} />;
}
