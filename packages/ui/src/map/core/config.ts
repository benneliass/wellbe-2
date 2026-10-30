/** Physical defaults are shared by drawing, layout and motion. Domain colors,
 * meanings and actions belong in an adapter, never in the map toolkit.
 */
export const MAP_SIZE = Object.freeze({ baseRadius: 14, alternativeRadius: 17, growth: 0.42, maxWeight: 14 });
export function mapObjectRadius(weight: number, base: number = MAP_SIZE.baseRadius): number {
  return base + Math.min(Math.max(weight, 0), MAP_SIZE.maxWeight) * MAP_SIZE.growth;
}

export const MAP_MOTION = Object.freeze({
  breathDurationMs: 5500, breathTravelPx: 1.6, minBreathScale: 0.025, maxBreathScale: 0.08,
  poseSettleMs: 105, positionSettleMs: 65, maxDragStretch: 0.024,
  hoverLift: 6, hoverLiftRadius: 0.15, driftAmplitude: 0.65, driftRate: 0.0005,
  hoverScale: 1.12, selectedScale: 1.35, emphasisSettleMs: 160, activeBreathFactor: 0.35,
  labelEmphasisFactor: 0.16,
  orbitMinPeriodMs: 48000, orbitPeriodStepMs: 2000, accentPeriodMs: 76000,
});
export type MapMotionConfig = { [K in keyof typeof MAP_MOTION]: number };

export const MAP_LINK = Object.freeze({ tint: 0.45, glowBlur: 2.8, glowPeriodMs: 5500, hitWidth: 12, reflectionWidth: 0.45 });
export type MapLinkConfig = { [K in keyof typeof MAP_LINK]: number };

export const MAP_INTERACTION = Object.freeze({ dragThresholdPx: 4, keyStep: 8, bigKeyStep: 40, minZoom: 0.3, maxZoom: 2.6 });
