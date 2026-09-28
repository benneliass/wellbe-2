import { beforeEach, describe, expect, it } from "vitest";
import {
  arrowDelta,
  clientToSvg,
  DRAG_THRESHOLD_PX,
  dragTo,
  KEY_STEP,
  KEY_STEP_BIG,
  loadPositions,
  passedThreshold,
  positionsKey,
  savePositions,
  svgToGraph,
} from "./graphDrag";

describe("drag math", () => {
  it("treats small wobbles as a click and larger moves as a drag", () => {
    expect(DRAG_THRESHOLD_PX).toBe(4);
    expect(passedThreshold(2, 2)).toBe(false);
    expect(passedThreshold(3, 0)).toBe(false);
    expect(passedThreshold(4, 0)).toBe(true);
    expect(passedThreshold(-3, -3)).toBe(true);
  });

  it("maps client points through the inverse screen CTM, then undoes pan and zoom", () => {
    // Rendered at half size, offset (100, 50) on screen.
    const ctm = { a: 0.5, b: 0, c: 0, d: 0.5, e: 100, f: 50 };
    const inverse = { a: 2, b: 0, c: 0, d: 2, e: -200, f: -100 };
    const svg = { getScreenCTM: () => ({ ...ctm, inverse: () => inverse }) } as unknown as SVGSVGElement;
    const p = clientToSvg(svg, 300, 250, { width: 860, height: 686 });
    expect(p).toEqual({ x: 400, y: 400 });
    expect(svgToGraph(p, { k: 2, tx: 100, ty: -50 })).toEqual({ x: 150, y: 225 });
  });

  it("falls back to the bounding box when there is no CTM", () => {
    const svg = { getBoundingClientRect: () => ({ left: 10, top: 20, width: 430, height: 343 }) } as unknown as SVGSVGElement;
    expect(clientToSvg(svg, 225, 191.5, { width: 860, height: 686 })).toEqual({ x: 430, y: 343 });
  });

  it("moves every dragged item by the same offset (a concern with its concepts)", () => {
    const start = { "cluster:c1": { x: 100, y: 40 }, a: { x: 90, y: 110 }, b: { x: 160, y: 120 } };
    expect(dragTo(start, { x: 25, y: -10 })).toEqual({ "cluster:c1": { x: 125, y: 30 }, a: { x: 115, y: 100 }, b: { x: 185, y: 110 } });
  });

  it("nudges by a small step, or a bigger one with Shift", () => {
    expect(arrowDelta("ArrowLeft", false)).toEqual({ x: -KEY_STEP, y: 0 });
    expect(arrowDelta("ArrowDown", true)).toEqual({ x: 0, y: KEY_STEP_BIG });
    expect(arrowDelta("Enter", false)).toBeNull();
  });
});

describe("position persistence", () => {
  beforeEach(() => window.localStorage.clear());

  it("saves per patient and view, and ignores ids no longer on the map", () => {
    savePositions("p1", "860x686", { a: { x: 1, y: 2 }, gone: { x: 3, y: 4 }, "cluster:c1": { x: 5, y: 6 } });
    savePositions("p1", "480x760", { a: { x: 9, y: 9 } });
    expect(JSON.parse(window.localStorage.getItem(positionsKey("p1"))!)).toEqual({
      "860x686": { a: [1, 2], gone: [3, 4], "cluster:c1": [5, 6] },
      "480x760": { a: [9, 9] },
    });
    expect(loadPositions("p1", "860x686", new Set(["a", "cluster:c1"]))).toEqual({ a: { x: 1, y: 2 }, "cluster:c1": { x: 5, y: 6 } });
    expect(loadPositions("p2", "860x686", new Set(["a"]))).toEqual({});
  });

  it("clears a view on reset and drops the key once nothing is left", () => {
    savePositions("p1", "860x686", { a: { x: 1, y: 2 } });
    savePositions("p1", "480x760", { a: { x: 3, y: 4 } });
    savePositions("p1", "860x686", {});
    expect(loadPositions("p1", "860x686", new Set(["a"]))).toEqual({});
    expect(loadPositions("p1", "480x760", new Set(["a"]))).toEqual({ a: { x: 3, y: 4 } });
    savePositions("p1", "480x760", {});
    expect(window.localStorage.getItem(positionsKey("p1"))).toBeNull();
  });

  it("survives corrupt storage", () => {
    window.localStorage.setItem(positionsKey("p1"), "{not json");
    expect(loadPositions("p1", "860x686", new Set(["a"]))).toEqual({});
    window.localStorage.setItem(positionsKey("p1"), JSON.stringify({ "860x686": { a: ["x", 2] } }));
    expect(loadPositions("p1", "860x686", new Set(["a"]))).toEqual({});
  });
});
