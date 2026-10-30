import { describe, expect, it } from "vitest";
import { connectionCandidates, planConnectionScene, routeInterference, visibilityConnection } from "@wellbe/ui/map/core";

const view = { width: 700, height: 500 };
describe('clear and economical connections', () => {
  it('uses opposing radial ports for a clear horizontal connection without a detour', () => {
    const a = { x: 100, y: 120, r: 20 }, b = { x: 500, y: 120, r: 20 };
    const best = connectionCandidates(a, b, [], view)[0]!;
    expect(best.length).toBeCloseTo(358, 1);
    expect(best.points[0]!.x).toBeGreaterThan(a.x);
    expect(best.points.at(-1)!.x).toBeLessThan(b.x);
  });
  it('treats the two endpoints symmetrically and clears a blocking object', () => {
    const a = { x: 100, y: 220, r: 20 }, b = { x: 520, y: 220, r: 20 }, obstacle = { x: 310, y: 220, r: 42, labelWidth: 100 };
    const forward = connectionCandidates(a, b, [obstacle], view)[0]!, reverse = connectionCandidates(b, a, [obstacle], view)[0]!;
    expect(Math.abs(forward.length - reverse.length)).toBeLessThan(1);
    expect(forward.length).toBeLessThan(500);
    for (const point of forward.points) expect(Math.hypot(point.x - obstacle.x, point.y - obstacle.y)).toBeGreaterThanOrEqual(obstacle.r + 8);
  });
  it('allows a clear bottom port beneath a protected title instead of detouring around its text', () => {
    const a = { x: 200, y: 100, r: 20, labelWidth: 150, allowUnderLabel: true }, b = { x: 200, y: 400, r: 20, labelWidth: 150, allowUnderLabel: true };
    const best = connectionCandidates(a, b, [], view)[0]!;
    expect(best.length).toBeCloseTo(258, 1);
    expect(best.points[0]!.y).toBeGreaterThan(a.y);
    expect(best.points.at(-1)!.y).toBeLessThan(b.y);
  });
  it('finds a short multi-bend route where labels close the single-curve corridor', () => {
    const a = { x: 454.5, y: 148.3, r: 19.88, labelWidth: 65, labelTop: 20.88, labelBottom: 41.88 };
    const b = { x: 352.1, y: 67.7, r: 15.68, labelWidth: 82.83, labelTop: 16.68, labelBottom: 37.68 };
    const title = { x: 445.1, y: 60.8, r: 0, labelOnly: true, labelWidth: 87.2, labelTop: -16, labelBottom: 24 };
    const route = visibilityConnection(a, b, [title], view)!;
    expect(route).not.toBeNull();
    expect(route.length).toBeLessThan(220);
    expect(route.d).toContain('Q');
    for (const p of route.points) expect(p.x < title.x - title.labelWidth / 2 - 4 || p.x > title.x + title.labelWidth / 2 + 4 || p.y < title.y + title.labelTop - 2 || p.y > title.y + title.labelBottom + 3).toBe(true);
  });
  it('penalizes both proper crossings and long overlapping tracks', () => {
    const line = (x: number, y: number, dx: number, dy: number) => Array.from({ length: 40 }, (_, i) => ({ x: x + i * dx, y: y + i * dy }));
    const a = line(100, 100, 4, 0);
    expect(routeInterference(a, line(180, 20, 0, 4))).toBeGreaterThan(0);
    expect(routeInterference(a, line(100, 102, 4, 0))).toBeGreaterThan(0);
    expect(routeInterference(a, line(100, 150, 4, 0))).toBe(0);
  });
  it('allows natural convergence around a shared object without excusing distant overlap', () => {
    const a = Array.from({ length: 50 }, (_, i) => ({ x: i * 4, y: 100 }));
    const b = a.map((point) => ({ x: point.x, y: point.y + 2 }));
    const all = routeInterference(a, b);
    const converging = routeInterference(a, b, [{ x: 196, y: 100, r: 60 }]);
    expect(converging).toBeGreaterThan(0);
    expect(converging).toBeLessThan(all);
  });
  it('plans a deterministic complete scene without changing the node positions', () => {
    const scene = [{ id: 'a/b', a: { x: 100, y: 100, r: 20 }, b: { x: 500, y: 220, r: 20 }, obstacles: [] }];
    const before = JSON.stringify(scene);
    expect(planConnectionScene(scene, view).get('a/b')!.d).toBe(planConnectionScene(scene, view).get('a/b')!.d);
    expect(JSON.stringify(scene)).toBe(before);
  });
});
