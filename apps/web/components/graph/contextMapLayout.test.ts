import { describe, expect, it } from "vitest";
import { growWorldLook, growViewportLook, hopLength, placeMapConstellation, mapWeightDiameter } from "@wellbe/ui/map/core";

describe("context map layout", () => {
  it("keeps full-map circles apart", () => {
    const nodes = Array.from({ length: 6 }, (_, index) => ({ id: String(index), degree: index }));
    const links = nodes.slice(1).map((node) => ({ source: "0", target: node.id }));
    const placed = placeMapConstellation(nodes, links, 900, 560);
    const points = [...placed.values()];
    for (let left = 0; left < points.length; left += 1) {
      for (let right = left + 1; right < points.length; right += 1) {
        const a = points[left];
        const b = points[right];
        if (!a || !b) continue;
        expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThan(1);
      }
    }
  });

  it("seats an opened record and hops its neighbours", () => {
    const origin = { x: 100, y: 100 };
    const radii = new Map([
      ["a", 15],
      ["b", 14],
      ["c", 14],
    ]);
    const placed = growWorldLook({
      stored: new Map(),
      shownIds: ["a", "b", "c"],
      latestId: "a",
      fullMap: new Map(),
      radii,
      origin,
    });
    expect(placed.get("a")).toEqual(origin);
    const neighbour = placed.get("b");
    expect(neighbour).toBeDefined();
    if (!neighbour) return;
    expect(Math.hypot(neighbour.x - origin.x, neighbour.y - origin.y)).toBeCloseTo(hopLength(15, 14), 5);
    expect(neighbour.y).toBeGreaterThan(origin.y);
  });

  it("keeps a placed note still when the walk steps", () => {
    const stored = growWorldLook({
      stored: new Map(),
      shownIds: ["a", "b"],
      latestId: "a",
      fullMap: new Map(),
      radii: new Map([
        ["a", mapWeightDiameter(2) / 2],
        ["b", mapWeightDiameter(1) / 2],
        ["c", mapWeightDiameter(0) / 2],
      ]),
      origin: { x: 40, y: 40 },
    });
    const kept = stored.get("a");
    const next = growWorldLook({
      stored,
      shownIds: ["a", "b", "c"],
      latestId: "b",
      fullMap: new Map(),
      radii: new Map([
        ["a", mapWeightDiameter(2) / 2],
        ["b", mapWeightDiameter(1) / 2],
        ["c", mapWeightDiameter(0) / 2],
      ]),
    });
    expect(next.get("a")).toEqual(kept);
    expect(next.has("c")).toBe(true);
  });

  it("seats new neighbours inside the viewport without collapsing them at an edge", () => {
    const parent = { x: 245, y: 100 };
    const placed = growViewportLook({
      stored: new Map([["a", parent]]),
      shownIds: ["a", "b", "c", "d", "e"],
      latestId: "a",
      radii: new Map(["a", "b", "c", "d", "e"].map((id) => [id, 38])),
      labelWidths: new Map(["a", "b", "c", "d", "e"].map((id) => [id, 130])),
      width: 980,
      height: 620,
    });
    expect(placed.get("a")).toEqual(parent);
    expect(placed.size).toBe(5);
    for (const [id, point] of placed) {
      expect(point.x).toBeGreaterThanOrEqual(75);
      expect(point.x).toBeLessThanOrEqual(905);
      expect(point.y).toBeGreaterThanOrEqual(54);
      expect(point.y).toBeLessThanOrEqual(540);
      for (const [otherId, other] of placed) {
        if (id === otherId) continue;
        expect(Math.abs(point.x - other.x) >= 150 || Math.abs(point.y - other.y) >= 130).toBe(true);
      }
    }
  });

});
