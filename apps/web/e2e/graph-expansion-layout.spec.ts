import { expect, test } from '@playwright/test';
import { afterMapPaint, inspectMapGeometry } from './_mapGeometry';

for (const width of [1774, 690, 390]) {
  test(`dragging Light sensitivity into Headache stays local and keeps names attached at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1050 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/design/graph');
    const light = page.locator('[data-node-id="light"]'), headache = page.locator('[data-node-id="headache"]');
    await headache.press('Enter');
    await expect(headache.locator('[data-pebble-object]')).toHaveAttribute('data-pebble-scale', '1.3500');
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(afterMapPaint);
    const start = (await light.locator('[data-pebble-bounds]').boundingBox())!;
    const destination = (await headache.locator('[data-pebble-bounds]').boundingBox())!;
    const from = { x: start.x + start.width / 2, y: start.y + start.height / 2 };
    const to = { x: destination.x + destination.width / 2, y: destination.y + destination.height / 2 };
    const camera = await page.locator('[data-map-camera]').getAttribute('transform');
    const read = () => page.locator('[data-node-id]').evaluateAll((nodes) => nodes.map((node) => ({ id: node.getAttribute('data-node-id')!, x: Number(node.getAttribute('data-pebble-x')), y: Number(node.getAttribute('data-pebble-y')) })));
    let before = await read(), worst = 0;
    await page.mouse.move(from.x, from.y); await page.mouse.down();
    for (let step = 1; step <= 50; step++) {
      await page.mouse.move(from.x + (to.x - from.x) * step / 50, from.y + (to.y - from.y) * step / 50);
      await page.evaluate(afterMapPaint);
      const next = await read();
      for (const node of next) if (node.id !== 'light') {
        const old = before.find((item) => item.id === node.id)!;
        worst = Math.max(worst, Math.hypot(node.x - old.x, node.y - old.y));
      }
      expect(await page.locator('[data-map-camera]').getAttribute('transform')).toBe(camera);
      if (step % 10 === 0) expect((await page.evaluate(inspectMapGeometry)).overlaps).toEqual([]);
      before = next;
    }
    expect(worst).toBeLessThan(18);
    await page.mouse.up(); await page.mouse.move(2, 2);
    await page.evaluate(afterMapPaint);
    const released = await read();
    for (const node of released) {
      const old = before.find((item) => item.id === node.id)!;
      expect(Math.hypot(node.x - old.x, node.y - old.y)).toBeLessThan(1);
    }
    await expect(light).toHaveAttribute('aria-pressed', 'false');
    await expect(light.locator('[data-pebble-object] [data-map-label]')).toHaveCount(1);
    if (width === 1774) await page.locator('svg[aria-label^="Map of your concerns"]').screenshot({ path: '/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/attached-labels/light-into-headache.png' });
  });
}

for (const width of [1774, 690, 390]) {
  test(`the map makes room for Diet change and repeated expansions at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1050 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/design/graph');
    await expect(page.locator('[data-node-id="diet"] [data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(afterMapPaint);
    for (const id of ['diet', 'nausea', 'fatigue', 'light', 'headache', 'sleep']) {
      const node = page.locator(`[data-node-id="${id}"]`);
      if (id === 'diet') {
        const circle = await node.locator('[data-pebble-bounds]').boundingBox();
        await page.mouse.click(circle!.x + circle!.width / 2, circle!.y + circle!.height / 2);
      } else {
        // Keyboard activation also works for a node outside the current pan.
        await node.focus();
        await page.keyboard.press('Enter');
      }
      await expect(node).toHaveAttribute('aria-pressed', 'true');
      if (id === 'diet') for (const child of ['weightlog', 'triggerfoods', 'elimination']) await expect(page.locator(`[data-node-id="${child}"]`)).toBeVisible();
      await page.evaluate(afterMapPaint);
      const geometry = await page.evaluate(inspectMapGeometry);
      expect(geometry.overlaps).toEqual([]);
      expect(geometry.crossings).toEqual([]);
      const sourceCollisions = await page.evaluate(() => {
        const bounds = [...document.querySelectorAll<SVGElement>('[data-node-id]')].map((node) => ({ id: node.getAttribute('data-node-id'), circle: (node.querySelector('[data-pebble-bounds]') ?? node.querySelector('circle'))!.getBoundingClientRect(), labels: [...node.querySelectorAll('text')].map((part) => part.getBoundingClientRect()) }));
        const sources = [...document.querySelectorAll<SVGElement>('[data-orbit-kind="source"] [data-mini-object]')].map((source) => ({ id: source.getAttribute('data-mini-object'), parent: source.closest('[data-node-id]')?.getAttribute('data-node-id'), rect: source.getBoundingClientRect() }));
        const hits: string[] = [];
        const overlap = (a: DOMRect, b: DOMRect) => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
        for (const source of sources) {
          for (const other of bounds) {
            const circle = other.circle, cx = circle.x + circle.width / 2, cy = circle.y + circle.height / 2;
            const x = Math.max(source.rect.left, Math.min(source.rect.right, cx)), y = Math.max(source.rect.top, Math.min(source.rect.bottom, cy));
            const bodyHit = ((x - cx) / (circle.width / 2)) ** 2 + ((y - cy) / (circle.height / 2)) ** 2 < 1;
            if (bodyHit || other.labels.some((rect) => overlap(source.rect, rect))) hits.push(`${source.id}/${other.id}`);
          }
          for (const other of sources) if (source.id !== other.id && overlap(source.rect, other.rect)) hits.push(`${source.id}/${other.id}`);
        }
        return hits;
      });
      expect(sourceCollisions).toEqual([]);
      if (id === 'diet') await page.locator('svg[aria-label^="Map of your concerns"]').screenshot({ path: `/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/dynamic-expansion/diet-expanded-${width}.png` });
    }
    await page.locator('[data-node-id="diet"]').focus();
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-node-id="weightlog"]')).toHaveCount(0);
    expect((await page.evaluate(inspectMapGeometry)).overlaps).toEqual([]);
  });
}

test('opening a zoomed family reveals every child above the map dock', async ({ page }) => {
  await page.setViewportSize({ width: 690, height: 1050 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  for (let i = 0; i < 7; i++) await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
  await page.locator('[data-node-id="diet"]').focus();
  await page.keyboard.press('Enter');
  const revealed = await page.evaluate(() => {
    const svg = document.querySelector<SVGSVGElement>('svg[aria-label^="Map of your concerns"]')!;
    const bounds = svg.getBoundingClientRect();
    const view = svg.viewBox.baseVal;
    const bottom = new DOMPoint(view.width, view.height - 92).matrixTransform(svg.getScreenCTM()!).y;
    return ['diet', 'weightlog', 'triggerfoods', 'elimination'].every((id) => {
      const node = document.querySelector(`[data-node-id="${id}"]`)!;
      const box = node.getBoundingClientRect();
      return box.left >= bounds.left && box.right <= bounds.right && box.top >= bounds.top && box.bottom <= bottom;
    });
  });
  expect(revealed).toBe(true);
});
