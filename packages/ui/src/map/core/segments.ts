export type BridgeBearing = { index: number; angle: number };
export type BridgeSector = { index: number; from: number; to: number };
const TAU = Math.PI * 2;
const angle = (value: number) => (value % TAU + TAU) % TAU;
// Trigonometric results can differ in the last bits between server and browser
// runtimes. Serialize paint geometry at sub-pixel precision, never raw doubles.
const coordinate = (value: number) => String(Number(value.toFixed(4)));
const largeArc = (span: number) => span > Math.PI + 1e-8 ? 1 : 0;
export function serializeSegmentBearings(bearings: readonly BridgeBearing[] = []): string {
  return JSON.stringify(bearings.map(({ index, angle }) => ({ index, angle: Number(angle.toFixed(8)) })));
}

/** Midpoints between actual port bearings put every port inside its own concern color. */
export function bridgeSectors(count: number, bearings: readonly BridgeBearing[] = []): BridgeSector[] {
  if (count < 2) return [];
  const sites = bearings.filter((site) => site.index >= 0 && site.index < count && Number.isFinite(site.angle)).map((site) => ({ ...site, angle: angle(site.angle) }));
  for (let index = 0; index < count; index++) if (!sites.some((site) => site.index === index)) sites.push({ index, angle: angle(-Math.PI / 2 + (index + 0.5) * TAU / count) });
  sites.sort((a, b) => a.angle - b.angle || a.index - b.index);
  const unique = sites.filter((site, i) => !i || site.index !== sites[i - 1]!.index || Math.abs(site.angle - sites[i - 1]!.angle) > 0.001);
  return unique.map((site, i) => {
    const before = unique[(i + unique.length - 1) % unique.length]!.angle - (i === 0 ? TAU : 0);
    const after = unique[(i + 1) % unique.length]!.angle + (i === unique.length - 1 ? TAU : 0);
    return { index: site.index, from: (before + site.angle) / 2, to: (site.angle + after) / 2 };
  });
}

export function bridgeFillPaths(count: number, bearings?: readonly BridgeBearing[]): string[] {
  const paths = Array.from({ length: count }, () => '');
  for (const sector of bridgeSectors(count, bearings)) paths[sector.index] += `M 0 0 L ${coordinate(Math.cos(sector.from) * 140)} ${coordinate(Math.sin(sector.from) * 140)} A 140 140 0 ${largeArc(sector.to - sector.from)} 1 ${coordinate(Math.cos(sector.to) * 140)} ${coordinate(Math.sin(sector.to) * 140)} Z `;
  return paths;
}

export function bridgeArcPaths(count: number, radius: number, bearings?: readonly BridgeBearing[], shimmer = 0): string[] {
  const paths = Array.from({ length: count }, () => '');
  for (const sector of bridgeSectors(count, bearings)) {
    const span = sector.to - sector.from;
    const from = sector.from + span * 0.2 + shimmer, to = sector.to - span * 0.2 + shimmer;
    paths[sector.index] += `M ${coordinate(Math.cos(from) * radius)} ${coordinate(Math.sin(from) * radius)} A ${coordinate(radius)} ${coordinate(radius)} 0 ${largeArc(to - from)} 1 ${coordinate(Math.cos(to) * radius)} ${coordinate(Math.sin(to) * radius)} `;
  }
  return paths;
}
