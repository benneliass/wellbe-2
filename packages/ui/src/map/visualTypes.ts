import type { ReactNode } from 'react';
import type { BridgeBearing } from './core/segments';

export type MapShape = 'pebble' | 'diamond' | 'open-loop' | 'comparison';
export type MapDataAttributes = Readonly<Record<`data-${string}`, string | number | boolean | undefined>>;
export type MapSurfaceAppearance = {
  color: string; shape?: MapShape; opacity?: number;
  segments?: readonly string[]; segmentBearings?: readonly BridgeBearing[];
};
export type MapMiniatureItem = {
  id: string; label: string; color: string; shape?: MapShape; opacity?: number; glyph: ReactNode; glyphSize?: number;
  kind?: string; attributes?: MapDataAttributes;
};
export type MapAccentProfile = {
  kind: 'none' | 'rim' | 'paired' | 'layered' | 'diamond' | 'external' | 'open-loop' | 'comparison' | 'bridge';
  period: number; dash: string; name?: string; type?: string;
};
export type MapBadge = {
  id: string; offset: { x: number; y: number }; color: string; glyph: ReactNode;
  fill?: string; glyphColor?: string; radius?: number;
  onActivate?: () => void; accessibleLabel?: string; pressed?: boolean;
};
export type MapVisualState = {
  hot?: boolean; grabbed?: boolean; selected?: boolean; expanded?: boolean; opacity?: number;
  emphasis?: { color: string; width?: number; dash?: string };
};
