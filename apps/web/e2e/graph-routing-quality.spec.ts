import { expect, test } from "@playwright/test";
import { inspectRoutingQuality } from "./_routingQuality";

for (const viewport of [{ width: 1774, height: 1100, baseline: 3027, maxCrossings: 2, maxDetour: 1.06 }, { width: 390, height: 1100, baseline: 3300, maxCrossings: 2, maxDetour: 1.1 }]) {
  test(`graph routes stay economical and clear at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/design/graph');
    await expect(page.locator('[data-node-id="headache"] [data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    const quality = await page.evaluate(inspectRoutingQuality);
    expect(quality.edges).toBe(14);
    expect(quality.obstructions).toEqual([]);
    expect(quality.overlaps).toEqual([]);
    expect(quality.crossings.length).toBeLessThanOrEqual(viewport.maxCrossings);
    expect(quality.maxDetour).toBeLessThan(viewport.maxDetour);
    expect(quality.totalLength).toBeLessThan(viewport.baseline * 0.85);
    const readability = await page.locator('[data-node-id] text').evaluateAll((labels) => labels.every((label) => { const style = getComputedStyle(label); return style.paintOrder.startsWith('stroke') && parseFloat(style.strokeWidth) >= 2.5; }));
    expect(readability).toBe(true);
  });
  test(`the named sleep connections have direct corridors at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/design/graph');
    await expect(page.locator('[data-node-id="headache"] [data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
    const composition = await page.evaluate(() => {
      const node = (id: string) => { const element = document.querySelector(`[data-node-id="${id}"]`)!; return { x: Number(element.getAttribute('data-pebble-x')), y: Number(element.getAttribute('data-pebble-y')), r: Number(element.getAttribute('data-pebble-radius')) }; };
      const caffeine = node('caffeine'), fatigue = node('fatigue'), sleep = node('sleep'), screen = node('screen');
      const lineY = fatigue.y + (sleep.y - fatigue.y) * (caffeine.x - fatigue.x) / (sleep.x - fatigue.x);
      const directness = (source: string, target: string) => {
        const path = document.querySelector<SVGPathElement>(`[data-connection][data-source="${source}"][data-target="${target}"]`)!;
        const length = path.getTotalLength(), start = path.getPointAtLength(0), end = path.getPointAtLength(length);
        return { ratio: length / Math.hypot(end.x - start.x, end.y - start.y), points: Array.from({ length: 101 }, (_, i) => { const point = path.getPointAtLength(length * i / 100); return { x: point.x, y: point.y }; }) };
      };
      return { caffeine, lineY, screen, bridge: directness('dizzy', 'sleep'), crossConcern: directness('headache', 'sleep') };
    });
    expect(composition.caffeine.y).toBeGreaterThan(composition.lineY + composition.caffeine.r);
    expect(composition.bridge.ratio).toBeLessThan(1.02);
    if (viewport.width > 1000) {
      expect(composition.crossConcern.ratio).toBeLessThan(1.02);
      const nearest = composition.crossConcern.points.reduce((best, point) => Math.abs(point.x - composition.screen.x) < Math.abs(best.x - composition.screen.x) ? point : best);
      expect(nearest.y).toBeGreaterThan(composition.screen.y + composition.screen.r + 8);
    }
  });
}
