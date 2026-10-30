import { MapSurface } from './MapSurface';
import { pebblePalette } from './core/material';
import type { MapMiniatureItem } from './visualTypes';

export function MapMiniature({ item, radius }: { item: MapMiniatureItem; radius: number }) {
  return <g data-mini-object={item.id} data-mini-color={item.color} data-mini-kind={item.kind} data-mini-radius={radius} color={pebblePalette(item.color).ink} {...item.attributes}>
    <title>{item.label}</title>
    <MapSurface radius={radius} appearance={item} detail="miniature" />
    <g transform={`translate(${-radius * 0.65} ${-radius * 0.65}) scale(${radius * 1.3 / (item.glyphSize ?? 24)})`}>{item.glyph}</g>
  </g>;
}
