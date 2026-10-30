import { expect, test } from "@playwright/test";
import { afterMapPaint } from './_mapGeometry';

test('ending a pan while zoom gestures arrive does not read a cleared gesture', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/design/graph');
  const svg = page.locator('svg[aria-label^="Map of your concerns"]');
  await expect(svg).toHaveAttribute('data-map-zoom-ready', 'true');
  await page.evaluate(afterMapPaint);
  for (const ending of ['pointerup', 'pointerleave', 'pointercancel', 'pinch']) {
    await svg.evaluate((element, ending) => {
      const box = element.getBoundingClientRect(), x = box.x + box.width / 2, y = box.y + box.height / 2;
      const pointer = (type: string, dx = 0) => element.dispatchEvent(new PointerEvent(type, { bubbles: true, pointerId: 1, pointerType: 'mouse', clientX: x + dx, clientY: y }));
      pointer('pointerdown'); pointer('pointermove', 10); pointer('pointermove', 20);
      if (ending === 'pinch') {
        const touches = [new Touch({ identifier: 1, target: element, clientX: x - 20, clientY: y }), new Touch({ identifier: 2, target: element, clientX: x + 20, clientY: y })];
        element.dispatchEvent(new TouchEvent('touchstart', { bubbles: true, cancelable: true, touches }));
        element.dispatchEvent(new TouchEvent('touchend', { bubbles: true, touches: [] }));
      } else pointer(ending, 20);
      element.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, ctrlKey: true, deltaY: -25, clientX: x, clientY: y }));
    }, ending);
    await page.evaluate(afterMapPaint);
    await expect(svg).toBeVisible();
    expect(await page.locator('[data-map-camera]').getAttribute('transform')).not.toMatch(/NaN|Infinity/);
  }
  expect(errors).toEqual([]);
});

test('hover placement follows keyboard movement without changing its content', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  const node = page.locator('[data-node-id="headache"]');
  await node.focus();
  const popup = page.locator('[data-graph-tooltip]');
  await expect(popup).toBeVisible();
  const original = await popup.getAttribute('style');
  for (let step = 0; step < 4; step++) await node.press('Shift+ArrowRight');
  await page.evaluate(afterMapPaint);
  await expect(popup).toHaveText('HeadacheSymptom · 14 sources · 5 days ago');
  await expect(popup).not.toHaveAttribute('style', original!);
  const overlap = await node.evaluate((element) => {
    const tooltip = document.querySelector('[data-graph-tooltip]')!.getBoundingClientRect();
    return [element.querySelector('circle')!, ...element.querySelectorAll('text, [data-metadata-badge], [data-node-orbit]')].some((part) => {
      const rect = part.getBoundingClientRect();
      return tooltip.left < rect.right && tooltip.right > rect.left && tooltip.top < rect.bottom && tooltip.bottom > rect.top;
    });
  });
  expect(overlap).toBe(false);
});

for (const width of [1774, 390]) {
  test(`hover content stays unchanged and clear of objects at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/design/graph');
    const nodes = page.locator('[data-node-id]');
    await expect(nodes.first().locator('[data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
    for (const node of await nodes.all()) {
      await node.focus();
      const popup = page.locator('[data-graph-tooltip]');
      await expect(popup).toBeVisible();
      await page.evaluate(afterMapPaint);
      const overlap = await node.evaluate((element) => {
        const popup = document.querySelector('[data-graph-tooltip]')!.getBoundingClientRect();
        return [element.querySelector('circle')!, ...element.querySelectorAll('text, [data-metadata-badge]')].some((part) => {
          const rect = part.getBoundingClientRect();
          return popup.left < rect.right && popup.right > rect.left && popup.top < rect.bottom && popup.bottom > rect.top;
        });
      });
      expect(overlap, await node.getAttribute('data-node-id') ?? '').toBe(false);
    }
    await page.locator('[data-node-id="headache"]').focus();
    await expect(page.locator('[data-graph-tooltip]')).toHaveText('HeadacheSymptom · 14 sources · 5 days ago');
    await expect(page.locator('[data-node-id="mri"] [data-metadata-badge="open-loop"]')).toHaveCount(0);
    await expect(page.locator('[data-node-id="mri"] foreignObject svg')).toHaveCount(1);
  });
}

test('wheel and browser zoom shortcuts affect only the map boundary', async ({ page }) => {
  await page.goto('/design/graph');
  const camera = page.locator('[data-graph-camera]');
  await expect(camera).toBeVisible();
  await expect(page.locator('svg[aria-label^="Map of your concerns"]')).toHaveAttribute('data-map-zoom-ready', 'true');
  const original = await camera.getAttribute('transform');
  const beforePage = await page.evaluate(() => ({ width: innerWidth, ratio: devicePixelRatio, scale: visualViewport!.scale }));
  const outside = await page.locator('h1').evaluate((element) => {
    const event = new WheelEvent('wheel', { bubbles: true, cancelable: true, ctrlKey: true, deltaY: -80 });
    element.dispatchEvent(event);
    return event.defaultPrevented;
  });
  expect(outside).toBe(true);
  expect(await camera.getAttribute('transform')).toBe(original);
  await page.locator('svg[aria-label^="Map of your concerns"]').evaluate((element) => {
    const box = element.getBoundingClientRect();
    element.dispatchEvent(new WheelEvent('wheel', { bubbles: true, cancelable: true, ctrlKey: true, deltaY: -30, clientX: box.x + box.width / 2, clientY: box.y + box.height / 2 }));
  });
  await expect(camera).not.toHaveAttribute('transform', original!);
  const zoomed = await camera.getAttribute('transform');
  await page.mouse.move(4, 4);
  await page.locator('h1').click();
  await page.keyboard.press('Control+=');
  expect(await camera.getAttribute('transform')).toBe(zoomed);
  expect(await page.evaluate(() => ({ width: innerWidth, ratio: devicePixelRatio, scale: visualViewport!.scale }))).toEqual(beforePage);
  const warnings: string[] = [];
  page.on('console', (message) => { if (message.text().includes('passive')) warnings.push(message.text()); });
  const box = await page.locator('svg[aria-label^="Map of your concerns"]').boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.keyboard.down('Control');
  await page.mouse.wheel(0, 40);
  await page.keyboard.up('Control');
  await expect(camera).not.toHaveAttribute('transform', zoomed!);
  expect(await page.evaluate(() => ({ width: innerWidth, ratio: devicePixelRatio, scale: visualViewport!.scale }))).toEqual(beforePage);
  const pinched = await camera.getAttribute('transform');
  await page.mouse.wheel(0, 50);
  await expect(camera).not.toHaveAttribute('transform', pinched!);
  expect(warnings).toEqual([]);
});

test.describe('two-finger map zoom', () => {
  test.use({ hasTouch: true });
  test('pinching changes the map scale while the page scale stays fixed', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 1000 });
    await page.goto('/design/graph');
    const svg = page.locator('svg[aria-label^="Map of your concerns"]');
    await svg.scrollIntoViewIfNeeded();
    const box = (await svg.boundingBox())!;
    const x = box.x + box.width / 2, y = Math.max(100, Math.min(850, box.y + box.height / 2));
    const camera = page.locator('[data-graph-camera]');
    const before = await camera.getAttribute('transform');
    const pageScale = await page.evaluate(() => visualViewport!.scale);
    const session = await page.context().newCDPSession(page);
    await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x - 30, y }, { x: x + 30, y }] });
    for (let step = 1; step <= 5; step++) await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x - 30 - step * 3, y }, { x: x + 30 + step * 3, y }] });
    await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await expect(camera).not.toHaveAttribute('transform', before!);
    expect(await page.evaluate(() => visualViewport!.scale)).toBe(pageScale);
  });
});
