import { describe, expect, it } from "vitest";
import { bridgeArcPaths, bridgeFillPaths, bridgeSectors, serializeSegmentBearings, type BridgeBearing } from "@wellbe/ui/map/core";

const tau = Math.PI * 2;
const inside = (bearing: BridgeBearing, sector: ReturnType<typeof bridgeSectors>[number]) => {
  const angle = ((bearing.angle - sector.from) % tau + tau) % tau;
  return sector.index === bearing.index && angle <= sector.to - sector.from + 1e-8;
};

describe('bridge concern sectors', () => {
  it('serializes equivalent cross-runtime angles without hydration mismatches', () => {
    const server = [{ index: 0, angle: -1.9600510735540413 }, { index: 1, angle: 0.621479102 }];
    const browser = [{ index: 0, angle: -1.960051073554041 }, { index: 1, angle: 0.621479102 + Number.EPSILON }];
    expect(serializeSegmentBearings(server)).toBe(serializeSegmentBearings(browser));
    expect(bridgeFillPaths(2, server)).toEqual(bridgeFillPaths(2, browser));
    expect(bridgeArcPaths(2, 21.36, server)).toEqual(bridgeArcPaths(2, 21.36, browser));
  });
  it.each([
    [{ index: 0, angle: Math.PI }, { index: 1, angle: 0 }],
    [{ index: 0, angle: -0.04 }, { index: 1, angle: 0.06 }],
    [{ index: 0, angle: 0 }, { index: 1, angle: 1 }, { index: 0, angle: 2 }, { index: 1, angle: 4 }],
    [{ index: 0, angle: -2 }, { index: 1, angle: 0.3 }, { index: 2, angle: 2.3 }],
  ])('puts every connection inside its own concern color (%j)', (...ports) => {
    const count = Math.max(...ports.map((port) => port.index)) + 1;
    const sectors = bridgeSectors(count, ports);
    for (const port of ports) expect(sectors.some((sector) => inside(port, sector))).toBe(true);
    expect(sectors.reduce((sum, sector) => sum + sector.to - sector.from, 0)).toBeCloseTo(tau);
    for (let i = 1; i < sectors.length; i++) expect(sectors[i]!.from).toBeCloseTo(sectors[i - 1]!.to);
  });

  it('retains concerns without visible links and produces bounded SVG sectors', () => {
    const ports = [{ index: 1, angle: 0.8 }];
    expect(new Set(bridgeSectors(3, ports).map((sector) => sector.index)).size).toBe(3);
    for (const paths of [bridgeFillPaths(3, ports), bridgeArcPaths(3, 24, ports, 0.025)]) {
      expect(paths).toHaveLength(3);
      expect(paths.every((path) => path.startsWith('M ') && !/NaN|Infinity/.test(path))).toBe(true);
    }
    expect(bridgeSectors(1)).toEqual([]);
  });
});
