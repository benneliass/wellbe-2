import { expect, test, type Page } from '@playwright/test';

async function auditBridge(page: Page) {
  return page.locator('[data-node-id="dizzy"]').evaluate((node) => {
    const cases: string[] = JSON.parse(node.getAttribute('data-map-segment-keys')!);
    const results: { concern: string; covered: boolean }[] = [];
    for (const link of document.querySelectorAll<SVGGElement>('[data-silk-link]')) {
      const end = link.getAttribute('data-source') === 'dizzy' ? 'source' : link.getAttribute('data-target') === 'dizzy' ? 'target' : null;
      if (!end) continue;
      const concern = link.getAttribute(`data-${end}-segment`)!;
      if (!cases.includes(concern)) continue;
      const segment = [...node.querySelectorAll<SVGPathElement>('[data-pebble-segment]')].find((path) => path.getAttribute('data-segment-key') === concern)!;
      const path = link.querySelector<SVGPathElement>('[data-connection]')!;
      const port = path.getPointAtLength(end === 'source' ? 0 : path.getTotalLength());
      const local = new DOMPoint(port.x, port.y).matrixTransform(path.getCTM()!).matrixTransform(segment.getCTM()!.inverse());
      const angle = Math.atan2(local.y, local.x);
      results.push({ concern, covered: segment.isPointInFill(new DOMPoint(Math.cos(angle) * 65, Math.sin(angle) * 65)) });
    }
    return results;
  });
}

for (const reducedMotion of ['reduce', 'no-preference'] as const) {
  test(`bridge colors face actual connection ports during hover and after drag (${reducedMotion})`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion });
    await page.goto('/design/graph');
    const bridge = page.locator('[data-node-id="dizzy"]');
    await expect(bridge.locator('[data-pebble-segment][data-segment-key]')).toHaveCount(2);
    const aligned = async () => { const results = await auditBridge(page); return results.length >= 2 && results.every((port) => port.covered); };
    await expect.poll(aligned).toBe(true);
    const bounds = await bridge.locator('[data-pebble-bounds]').boundingBox();
    const x = bounds!.x + bounds!.width / 2, y = bounds!.y + bounds!.height / 2;
    await page.mouse.move(x + 9, y - 8);
    await expect.poll(aligned).toBe(true);
    await page.mouse.down();
    await page.mouse.move(x + 100, y + 60, { steps: 10 });
    await page.mouse.up();
    await page.mouse.move(1, 1);
    await expect.poll(aligned).toBe(true);
  });
}

test('miniatures keep the actual hidden child identity and type; source orbits keep their source glyphs', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  const diet = page.locator('[data-node-id="diet"]');
  const items = await diet.locator('[data-mini-object]').evaluateAll((elements) => elements.map((element) => ({ id: element.getAttribute('data-mini-object'), type: element.getAttribute('data-mini-type'), icon: element.getAttribute('data-mini-icon'), color: element.getAttribute('data-mini-color') })));
  expect(new Set(items.map((item) => item.color))).toEqual(new Set([await diet.getAttribute('data-node-color')]));
  expect(items.map((item) => item.id)).toEqual(['weightlog', 'triggerfoods', 'elimination']);
  await diet.focus();
  await page.keyboard.press('Enter');
  for (const item of items) {
    const node = page.locator(`[data-node-id="${item.id}"]`);
    await expect(node).toBeVisible();
    await expect(node).toHaveAttribute('data-node-color', item.color!);
    expect(item.color).not.toBe('#64748b');
    expect(item.type).toBe('context');
    expect(item.icon).toBe('circle-user');
  }
  await page.locator('[data-node-id="headache"]').focus();
  await page.keyboard.press('Enter');
  // Sources keep their real kind while remaining in orbit after selection.
  const sources = page.locator('[data-mini-source]');
  await expect(sources.first()).toBeVisible();
  const metadata = await sources.evaluateAll((elements) => elements.map((element) => [element.getAttribute('data-mini-source'), element.getAttribute('data-mini-icon')]));
  expect(new Set(await sources.evaluateAll((elements) => elements.map((element) => element.getAttribute('data-mini-color')))).size).toBeGreaterThan(1);
  expect(metadata).toEqual(expect.arrayContaining([['reported', 'message-circle'], ['wearable', 'activity'], ['note', 'file-text']]));
});

test('amber remains an explicitly conflicting relationship even within one purple concern', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  const link = page.locator('[data-silk-link][data-source="caffeine"][data-target="fatigue"]');
  await expect(link).toHaveAttribute('data-relationship', 'conflict');
  await expect(link.locator('[data-connection]')).toHaveAttribute('stroke-dasharray', '8 6');
  const colors = await link.locator('stop').evaluateAll((stops) => stops.map((stop) => stop.getAttribute('stop-color')));
  expect(colors[0]).toBe(colors[1]);
  expect(colors[0]).toBe('#faca79');
  await link.locator('[data-connection]').dispatchEvent('click');
  await expect(page.getByText('Conflicting information', { exact: true }).first()).toBeVisible();
});
