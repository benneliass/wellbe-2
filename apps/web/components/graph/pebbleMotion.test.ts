import { describe, expect, it } from "vitest";
import { PebbleMotion, pebbleBreathAmplitude, pebbleScreenScale } from "@wellbe/ui/map/core";

describe("size-adaptive pebble breathing", () => {
  it('makes hover smaller than selection, allows a host size limit and keeps reduced motion static', () => {
    const root = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    const body = document.createElementNS(root.namespaceURI, 'g');
    body.setAttribute('data-pebble-body', ''); root.append(body);
    const motion = new PebbleMotion();
    const frame = { now: 1000, radius: 20, calm: true, grabbed: false, hot: true, lift: 0, phase: 0 };
    motion.paint(root, { ...frame, emphasis: 'hover' });
    expect(body).toHaveAttribute('transform', 'rotate(0) scale(1.12 1.12)');
    motion.paint(root, { ...frame, emphasis: 'selected' });
    expect(body).toHaveAttribute('transform', 'rotate(0) scale(1.35 1.35)');
    motion.paint(root, { ...frame, now: 9000, emphasis: 'selected' });
    expect(body).toHaveAttribute('transform', 'rotate(0) scale(1.35 1.35)');
    motion.paint(root, { ...frame, emphasis: 'selected', maxScale: 1.11 });
    expect(root).toHaveAttribute('data-pebble-scale', '1.1100');
    motion.paint(root, { ...frame, grabbed: true, emphasis: 'selected' });
    expect(body).toHaveAttribute('transform', 'rotate(0) scale(1.35 1.35)');
  });
  it("keeps comparable edge travel as density or zoom changes the visible radius", () => {
    const radii = [20, 32, 60];
    const travel = radii.map((radius) => radius * pebbleBreathAmplitude(radius));
    expect(Math.max(...travel) - Math.min(...travel)).toBeLessThan(0.01);
    expect(travel[0]).toBeGreaterThan(1.5);
    expect(pebbleBreathAmplitude(20)).toBeGreaterThan(pebbleBreathAmplitude(60));
  });

  it("bounds the response for extreme zoom and tiny objects", () => {
    expect(pebbleBreathAmplitude(2)).toBeLessThanOrEqual(0.08);
    expect(pebbleBreathAmplitude(400)).toBeGreaterThanOrEqual(0.025);
    expect(Number.isFinite(pebbleBreathAmplitude(0))).toBe(true);
  });

  it("uses the screen transform including zoom without measuring its own breathing", () => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", "g");
    Object.assign(node, { getScreenCTM: () => ({ a: 0, b: 0.6, c: -0.6, d: 0 }) });
    expect(pebbleScreenScale(node)).toBeCloseTo(0.6);
    const body = document.createElementNS(node.namespaceURI, "g");
    body.setAttribute("data-pebble-body", "");
    node.append(body);
    const paint = (screenScale: number, calm = false, grabbed = false) => {
      new PebbleMotion().paint(node, { now: 1375, radius: 40, screenScale, calm, grabbed, hot: false, lift: 0, phase: 0 });
      return body.getAttribute("transform")!;
    };
    expect(paint(0.5)).toContain("matrix(1.0800");
    expect(paint(1)).toContain("matrix(1.0400");
    expect(paint(2)).toContain("matrix(1.0250");
    expect(paint(0.5, true)).toBe("rotate(0) scale(1 1)");
    const draggedScale = Number(paint(0.5, false, true).match(/matrix\(([^ ]+)/)![1]);
    expect(draggedScale).toBeGreaterThanOrEqual(1);
    expect(draggedScale).toBeLessThanOrEqual(1.024);
  });
});
