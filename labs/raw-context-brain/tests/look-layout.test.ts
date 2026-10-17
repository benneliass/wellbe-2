import { describe, expect, it } from "vitest";
import { growLook, hopLength, relaxNewPoint, type Point } from "../src/viz/look-layout.js";

const radii = new Map([
  ["a", 10],
  ["b", 10],
  ["c", 10],
  ["d", 10],
  ["e", 10],
]);

function places(entries: Array<[string, Point]>): Map<string, Point> {
  return new Map(entries);
}

function same(actual: Point | undefined, expected: Point): void {
  expect(actual?.x).toBe(expected.x);
  expect(actual?.y).toBe(expected.y);
}

function segmentHits(start: Point, end: Point, center: Point, radius: number): boolean {
  const abx = end.x - start.x;
  const aby = end.y - start.y;
  const length2 = abx * abx + aby * aby || 1;
  const along = Math.max(0, Math.min(1, ((center.x - start.x) * abx + (center.y - start.y) * aby) / length2));
  if (along < 0.12 || along > 0.88) return false;
  const closestX = start.x + abx * along;
  const closestY = start.y + aby * along;
  return Math.hypot(center.x - closestX, center.y - closestY) < radius;
}

describe("opened look places", () => {
  const fullMap = places([
    ["a", { x: 0, y: 0 }],
    ["b", { x: 120, y: 40 }],
    ["c", { x: -30, y: 90 }],
    ["d", { x: 400, y: 400 }],
  ]);

  it("seats the first neighborhood on a short hop around the opened note", () => {
    const placed = growLook({
      stored: new Map(),
      shownIds: ["a", "b", "c"],
      latestId: "a",
      fullMap,
      radii,
    });
    same(placed.get("a"), { x: 0, y: 0 });
    const step = hopLength(10, 10);
    for (const id of ["b", "c"]) {
      const point = placed.get(id);
      const distance = Math.hypot(point?.x ?? 0, point?.y ?? 0);
      expect(distance).toBeCloseTo(step, 5);
    }
    expect(placed.get("b")).not.toEqual(fullMap.get("b"));
    expect(placed.has("d")).toBe(false);
  });

  it("keeps stored notes and places only the new one beside the latest note", () => {
    const stored = places([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 120, y: 40 }],
    ]);
    const placed = growLook({
      stored,
      shownIds: ["a", "b", "d"],
      latestId: "b",
      fullMap,
      radii,
    });
    same(placed.get("a"), { x: 0, y: 0 });
    same(placed.get("b"), { x: 120, y: 40 });
    const added = placed.get("d");
    expect(added).toBeDefined();
    const parent = { x: 120, y: 40 };
    const distance = Math.hypot((added?.x ?? 0) - parent.x, (added?.y ?? 0) - parent.y);
    expect(distance).toBeCloseTo(hopLength(10, 10), 5);
    expect(Math.hypot((added?.x ?? 0) - 0, (added?.y ?? 0) - 0)).toBeGreaterThan(20);
    expect(segmentHits(parent, added ?? parent, { x: 0, y: 0 }, 10)).toBe(false);
  });

  it("keeps a new note on a short hop even when earlier notes are far apart", () => {
    const stored = places([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 300, y: 0 }],
    ]);
    const placed = growLook({
      stored,
      shownIds: ["a", "b", "d"],
      latestId: "b",
      fullMap,
      radii,
    });
    const added = placed.get("d");
    const distance = Math.hypot((added?.x ?? 0) - 300, (added?.y ?? 0) - 0);
    expect(distance).toBeCloseTo(hopLength(10, 10), 5);
    expect(distance).toBeLessThan(80);
    same(placed.get("a"), { x: 0, y: 0 });
    same(placed.get("b"), { x: 300, y: 0 });
  });

  it("moves a new note off a circle its link would cross", () => {
    const parent = { x: 0, y: 0 };
    const blocker = { x: 40, y: 0 };
    const start = { x: 80, y: 0 };
    const moved = relaxNewPoint(parent, start, 10, [{ point: blocker, radius: 16 }]);
    expect(moved.x).not.toBe(start.x);
    expect(moved.y).not.toBe(start.y);
    expect(Math.hypot(moved.x - blocker.x, moved.y - blocker.y)).toBeGreaterThanOrEqual(10 + 16);
    expect(segmentHits(parent, moved, blocker, 16)).toBe(false);
    same(blocker, { x: 40, y: 0 });
  });

  it("drops notes that leave and leaves the rest in place", () => {
    const stored = places([
      ["a", { x: 0, y: 0 }],
      ["b", { x: 120, y: 40 }],
      ["c", { x: -30, y: 90 }],
    ]);
    const placed = growLook({
      stored,
      shownIds: ["a", "b"],
      latestId: "a",
      fullMap,
      radii,
    });
    same(placed.get("a"), { x: 0, y: 0 });
    same(placed.get("b"), { x: 120, y: 40 });
    expect(placed.has("c")).toBe(false);
  });

  it("keeps a new note outside circles that are already on screen", () => {
    const stored = places([
      ["a", { x: 50, y: 0 }],
      ["b", { x: 0, y: 0 }],
    ]);
    const wide = new Map([
      ["a", 40],
      ["b", 40],
      ["d", 40],
    ]);
    const placed = growLook({
      stored,
      shownIds: ["a", "b", "d"],
      latestId: "b",
      fullMap,
      radii: wide,
    });
    const added = placed.get("d");
    expect(added).toBeDefined();
    for (const id of ["a", "b"]) {
      const point = stored.get(id);
      const distance = Math.hypot((added?.x ?? 0) - (point?.x ?? 0), (added?.y ?? 0) - (point?.y ?? 0));
      expect(distance).toBeGreaterThanOrEqual(80);
    }
    same(placed.get("a"), { x: 50, y: 0 });
    same(placed.get("b"), { x: 0, y: 0 });
  });

  it("seeds again after the stored places are cleared", () => {
    const stored = places([["a", { x: 5, y: 5 }]]);
    stored.clear();
    const placed = growLook({
      stored,
      shownIds: ["a", "b"],
      latestId: "a",
      fullMap,
      radii,
    });
    same(placed.get("a"), { x: 0, y: 0 });
    const neighbor = placed.get("b");
    expect(neighbor?.x).toBeCloseTo(0, 5);
    expect(neighbor?.y).toBeCloseTo(-hopLength(10, 10), 5);
  });
});
