export type GraphOrbitConfig = { itemRadius: number; gap: number; itemsPerRing: number; maxItems: number };
export const GRAPH_ORBIT: Readonly<GraphOrbitConfig> = Object.freeze({ itemRadius: 4.2, gap: 2.1, itemsPerRing: 6, maxItems: 12 });

export function graphOrbitCount(count: number, config = GRAPH_ORBIT) {
  if (!Number.isFinite(config.itemRadius) || config.itemRadius <= 0 || !Number.isFinite(config.gap) || config.gap < 0 || !Number.isInteger(config.itemsPerRing) || config.itemsPerRing < 1 || !Number.isInteger(config.maxItems) || config.maxItems < 0) throw new Error('Invalid graph orbit dimensions or preview limits');
  return Math.max(0, Math.min(config.maxItems, count));
}
export function graphOrbitRadius(radius: number, ring = 0, config = GRAPH_ORBIT) {
  return radius * 1.08 + config.itemRadius + config.gap + ring * (config.itemRadius * 2 + config.gap);
}
export function graphOrbitExtent(radius: number, count: number, config = GRAPH_ORBIT) {
  const rings = Math.ceil(graphOrbitCount(count, config) / config.itemsPerRing);
  return rings ? graphOrbitRadius(radius, rings - 1, config) + config.itemRadius + 0.5 : radius + 8;
}
export function graphOrbitLabelOffset(count: number, config = GRAPH_ORBIT) {
  const rings = Math.ceil(graphOrbitCount(count, config) / config.itemsPerRing);
  return rings ? 30 + (rings - 1) * (config.itemRadius * 2 + config.gap) : 16;
}

/** The renderer and collision layout share these dimensions. No visible tracks. */
export function graphOrbitSlots(radius: number, count: number, config = GRAPH_ORBIT) {
  const total = graphOrbitCount(count, config);
  return Array.from({ length: total }, (_, index) => {
    const ring = Math.floor(index / config.itemsPerRing), offset = index % config.itemsPerRing;
    const inRing = Math.min(config.itemsPerRing, total - ring * config.itemsPerRing);
    const angle = -Math.PI / 2 + offset * Math.PI * 2 / inRing;
    const distance = graphOrbitRadius(radius, ring, config);
    return { angle, distance, x: Math.cos(angle) * distance, y: Math.sin(angle) * distance, itemRadius: config.itemRadius };
  });
}

/** Badges live beyond the complete orbital sweep, never in a miniature's lane. */
export function mapBadgeOffset(radius: number, count: number, side = 1, badgeRadius = 4.2, config = GRAPH_ORBIT) {
  const distance = (count ? graphOrbitExtent(radius, count, config) : radius * 1.08) + badgeRadius + 4;
  return { x: side * distance / Math.SQRT2, y: -distance / Math.SQRT2 };
}
