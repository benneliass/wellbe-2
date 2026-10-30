import { expect, test } from '@playwright/test';
import { afterMapPaint, inspectMapGeometry } from './_mapGeometry';

test('selection sends a quiet glint along the actual silhouette and respects drag and reduced motion', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/design/graph');
  const node = page.locator('[data-node-id="headache"]');
  const edge = node.locator('[data-map-edge-flow]');
  const core = edge.locator('path').last();
  await expect(edge).toHaveCSS('opacity', '0');
  expect(await core.getAttribute('d')).toBe(await node.locator('[data-pebble-silhouette]').getAttribute('d'));
  await node.press('Enter');
  await expect(edge).toHaveCSS('opacity', '1');
  await expect(core).toHaveCSS('animation-play-state', 'running');
  await expect(core).toHaveCSS('animation-duration', '12s');
  const offset = () => core.evaluate((element) => getComputedStyle(element).strokeDashoffset);
  const before = await offset();
  await expect.poll(offset).not.toBe(before);
  await page.evaluate(afterMapPaint);
  const box = (await node.locator('[data-pebble-bounds]').boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 30, box.y + box.height / 2, { steps: 6 });
  await expect(core).toHaveCSS('animation-play-state', 'paused');
  await page.mouse.up();
  await page.mouse.move(2, 2);
  await expect(core).toHaveCSS('animation-play-state', 'running');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(core).toHaveCSS('animation-name', 'none');
  const still = await offset();
  await page.evaluate(afterMapPaint);
  expect(await offset()).toBe(still);
  await expect(edge).toHaveCSS('opacity', '1');
  await page.locator('svg[aria-label^="Map of your concerns"]').screenshot({ path: '/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/object-emphasis/edge-flow-selected.png' });
});

for (const width of [1774, 390]) for (const reducedMotion of ['reduce', 'no-preference'] as const) {
  test(`hover and selection emphasize the object volume without extra circles at ${width}px (${reducedMotion})`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1050 });
    await page.emulateMedia({ reducedMotion });
    await page.goto('/design/graph');
    const node = page.locator('[data-node-id="headache"]');
    const object = node.locator('[data-pebble-object]');
    const volume = node.locator('[data-map-volume]');
    await expect(object).toHaveAttribute('data-pebble-pose', reducedMotion === 'reduce' ? 'still' : 'rest');
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(afterMapPaint);
    const circles = await node.locator('circle').count();
    const orbitRadius = Number(await node.locator('[data-orbit-dot]').first().getAttribute('data-orbit-radius'));
    const miniatureRadius = await node.locator('[data-mini-radius]').first().getAttribute('data-mini-radius');
    const labelY = await node.locator('text').first().getAttribute('y');
    const box = (await node.locator('[data-pebble-bounds]').boundingBox())!;
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await expect(node).toHaveAttribute('data-pebble-hot', 'true');
    if (reducedMotion === 'reduce') await expect(object).toHaveAttribute('data-pebble-scale', '1.1200');
    else await expect.poll(async () => Number(await object.getAttribute('data-pebble-scale'))).toBeGreaterThan(1.08);
    await expect.poll(() => volume.evaluate((element) => getComputedStyle(element).filter)).toContain('drop-shadow');
    await page.mouse.down(); await page.mouse.up();
    await expect(node).toHaveAttribute('aria-pressed', 'true');
    await page.mouse.move(2, 2);
    if (reducedMotion === 'reduce') await expect(object).toHaveAttribute('data-pebble-scale', '1.3500');
    else await expect.poll(async () => Number(await object.getAttribute('data-pebble-scale'))).toBeGreaterThan(1.30);
    await page.evaluate(afterMapPaint);
    expect(await node.locator('circle').count()).toBe(circles);
    expect(await node.locator('text').first().getAttribute('y')).toBe(labelY);
    await expect(node.locator('[data-pebble-object] [data-map-label]')).toHaveCount(1);
    await expect.poll(async () => Number((await node.locator('[data-map-label]').getAttribute('transform'))?.match(/scale\(([^)]+)\)/)?.[1])).toBeGreaterThan(1.04);
    expect(Number(await node.locator('[data-orbit-dot]').first().getAttribute('data-orbit-radius'))).toBeGreaterThan(orbitRadius + 3);
    expect(await node.locator('[data-mini-radius]').first().getAttribute('data-mini-radius')).toBe(miniatureRadius);
    const scene = await page.evaluate(inspectMapGeometry);
    expect(scene.overlaps).toEqual([]);
    expect(scene.crossings).toEqual([]);
    const geometry = await node.evaluate((element) => {
      const bounds = element.querySelector<SVGCircleElement>('[data-pebble-bounds]')!;
      const matrix = bounds.getScreenCTM()!;
      const center = new DOMPoint(0, 0).matrixTransform(matrix);
      const radius = Number(bounds.getAttribute('r')) * Math.hypot(matrix.a, matrix.b);
      const endpoints = [...document.querySelectorAll<SVGPathElement>('[data-connection][data-source="headache"], [data-connection][data-target="headache"]')].map((path) => {
        const p = path.getPointAtLength(path.getAttribute('data-source') === 'headache' ? 0 : path.getTotalLength());
        const screen = new DOMPoint(p.x, p.y).matrixTransform(path.getScreenCTM()!);
        return Math.hypot(screen.x - center.x, screen.y - center.y) / radius;
      });
      const orbitClear = [...element.querySelectorAll('[data-orbit-dot]')].every((dot) => {
        const inner = Number(dot.getAttribute('data-orbit-radius')) - Number(dot.getAttribute('data-orbit-item-radius'));
        return inner > Number(element.getAttribute('data-pebble-radius')) * Number(element.querySelector('[data-pebble-scale]')!.getAttribute('data-pebble-scale'));
      });
      return { endpoints, orbitClear };
    });
    expect(geometry.endpoints.length).toBeGreaterThan(0);
    for (const distance of geometry.endpoints) expect(Math.abs(distance - 1)).toBeLessThan(0.15);
    expect(geometry.orbitClear).toBe(true);
    await node.press('Escape');
    await expect(node).toHaveAttribute('aria-pressed', 'false');
    await expect.poll(async () => Number(await object.getAttribute('data-pebble-scale'))).toBeLessThan(1.085);
    if (width === 1774 && reducedMotion === 'reduce') {
      await node.press('Enter');
      await expect(object).toHaveAttribute('data-pebble-scale', '1.3500');
      await page.locator('svg[aria-label^="Map of your concerns"]').screenshot({ path: '/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/object-emphasis/selected.png' });
    }
  });
}
