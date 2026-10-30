import { describe, expect, it } from "vitest";
import { SilkLink, sampleSilkRoute, type SilkFrame } from "@wellbe/ui/map/core";

const scene = (): SilkFrame => ({
  a: { x: 180, y: 160, r: 36, labelWidth: 110 },
  b: { x: 530, y: 320, r: 40, labelWidth: 130 },
  obstacles: [{ x: 330, y: 240, r: 35, labelWidth: 120 }],
  viewport: { width: 900, height: 600 }, revision: "full", calm: false, interacting: false,
});

describe("silk link continuity", () => {
  it('keeps the held corridor when the scene bounds grow inside the same coordinate system', () => {
    const silk = new SilkLink('growing-bounds');
    const input = { ...scene(), calm: true, interacting: true };
    const before = silk.frame(1000, input);
    expect(silk.frame(1016, { ...input, viewport: { width: 1100, height: 800 } })).toBe(before);
    expect(silk.plans).toBe(1);
  });
  it('follows a growing object rim without moving its center or replanning the corridor', () => {
    const silk = new SilkLink('growing');
    const input = { ...scene(), obstacles: [], calm: true };
    silk.frame(1000, input);
    const before = { ...silk.endpoints.a };
    const distance = (point: { x: number; y: number }) => Math.hypot(point.x - input.a.x, point.y - input.a.y);
    silk.frame(1100, { ...input, a: { ...input.a, r: input.a.r * 1.14 } });
    expect(distance(silk.endpoints.a) / distance(before)).toBeCloseTo(1.14, 5);
    expect(silk.plans).toBe(1);
  });
  it("keeps one planned route while ambient motion stays alive", () => {
    const silk = new SilkLink("a/b");
    const input = scene();
    const first = silk.frame(1000, input);
    let latest = first;
    for (let frame = 1; frame <= 240; frame += 1) latest = silk.frame(1000 + frame * 16, input);
    expect(silk.plans).toBe(1);
    expect(latest).not.toBe(first);
    expect(sampleSilkRoute(latest)[0]).toEqual(sampleSilkRoute(first)[0]);
    expect(sampleSilkRoute(latest).at(-1)).toEqual(sampleSilkRoute(first).at(-1));
  });

  it("does not switch sides or jump when a dragged endpoint crosses its neighbour", () => {
    const silk = new SilkLink("crossing");
    const input = { ...scene(), interacting: true };
    let previous = sampleSilkRoute(silk.frame(1000, input));
    const commands = (d: string) => d.replace(/[^MLCQ]/g, "");
    const topology = commands(silk.frame(1016, input));
    let maxJump = 0;
    for (let frame = 1; frame <= 180; frame += 1) {
      input.b = { ...input.b, x: 530 - frame * 2, y: 320 + Math.sin(frame / 30) * 20 };
      const d = silk.frame(1016 + frame * 16, input);
      const next = sampleSilkRoute(d);
      expect(commands(d)).toBe(topology);
      for (let i = 1; i < next.length - 1; i += 1) maxJump = Math.max(maxJump, Math.hypot(next[i]!.x - previous[i]!.x, next[i]!.y - previous[i]!.y));
      previous = next;
    }
    expect(silk.plans).toBe(1);
    expect(maxJump).toBeLessThan(8);
  });

  it("continues settling after release instead of behaving like a rigid connector", () => {
    const silk = new SilkLink("elastic");
    const input = { ...scene(), obstacles: [], interacting: true };
    silk.frame(1000, input);
    input.a = { ...input.a, x: input.a.x + 90, y: input.a.y + 30 };
    const during = sampleSilkRoute(silk.frame(1016, input));
    input.interacting = false;
    const after = sampleSilkRoute(silk.frame(1032, input));
    const middle = Math.floor(during.length / 2);
    expect(Math.hypot(after[middle]!.x - during[middle]!.x, after[middle]!.y - during[middle]!.y)).toBeGreaterThan(0.1);
    expect(after[0]).toEqual(during[0]);
    expect(after.at(-1)!.x).toBeCloseTo(during.at(-1)!.x, 6);
    expect(after.at(-1)!.y).toBeCloseTo(during.at(-1)!.y, 6);
    expect(silk.plans).toBe(1);
  });

  it("freezes ambient motion for reduced motion while preserving drag and its settled route", () => {
    const silk = new SilkLink("calm");
    const input = { ...scene(), calm: true };
    const before = silk.frame(1000, input);
    expect(silk.frame(5000, { ...input, hot: true })).toBe(before);
    input.interacting = true;
    input.a = { ...input.a, x: input.a.x + 80 };
    expect(silk.frame(5016, input)).not.toBe(before);
    expect(silk.plans).toBe(1);
    input.interacting = false;
    const settled = silk.frame(5032, input);
    expect(silk.plans).toBeLessThanOrEqual(2);
    expect(silk.frame(6000, input)).toBe(settled);
  });

  it("resets springs when the viewport changes coordinate systems", () => {
    const silk = new SilkLink("resize");
    const input = scene();
    silk.frame(1000, input);
    const resized = { ...input, a: { ...input.a, x: 90, y: 90 }, b: { ...input.b, x: 280, y: 250 }, viewport: { width: 390, height: 800 }, revision: "phone" };
    const path = silk.frame(1016, resized);
    const fresh = new SilkLink("resize");
    expect(path).toBe(fresh.frame(1016, resized));
  });

  it("accepts a better scene route even when neither endpoint moved", () => {
    const silk = new SilkLink('updated-scene');
    const a = { x: 100, y: 150, r: 20 }, b = { x: 400, y: 150, r: 20 };
    const input = { a, b, obstacles: [], viewport: { width: 500, height: 350 }, revision: 'same', calm: true, interacting: false, peerRoutes: [Array.from({ length: 24 }, (_, i) => ({ x: 330 + i * 2, y: 150 }))] };
    const before = silk.frame(1000, { ...input, preferredRoute: { a, b, d: 'M 121 150 C 180 30, 340 30, 379 150' } });
    const after = silk.frame(2000, { ...input, preferredRoute: { a, b, d: 'M 121 150 C 200 150, 300 150, 379 150' } });
    expect(after).not.toBe(before);
    const points = sampleSilkRoute(after);
    expect(points.every((point) => Math.abs(point.y - 150) < 0.01)).toBe(true);
  });

});
