import { expect, test } from '@playwright/test';
import { afterMapPaint } from './_mapGeometry';

for (const width of [1774, 390]) test(`both maps share object, label and interaction styling at ${width}px`, async ({ page }) => {
  await page.setViewportSize({ width, height: 1050 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const styleOf = () => {
    const node = document.querySelector('[data-node-id="headache"], [data-record-id="r01"] [data-map-object-id]')!;
    const label = getComputedStyle(node.querySelector('text')!);
    const body = node.querySelector('[data-pebble-body]')!;
    return { objectClass: node.getAttribute('class'), labelClass: node.querySelector('text')!.getAttribute('class'), family: label.fontFamily, size: label.fontSize, weight: label.fontWeight, stroke: label.stroke, strokeWidth: label.strokeWidth, paintOrder: label.paintOrder,
      materialOpacity: body.getAttribute('opacity'), glyph: node.querySelector('[data-pebble-face] foreignObject')?.getAttribute('width'), edgeGlow: Boolean(node.querySelector('[data-map-edge-flow]')) };
  };
  await page.goto('/design/graph');
  await expect(page.locator('[data-node-id="headache"]')).toBeVisible();
  const graph = await page.evaluate(styleOf);
  await page.goto('/design/context');
  const context = page.locator('[data-record-id="r01"]');
  await expect(context).toBeVisible(); await page.evaluate(afterMapPaint);
  expect(await page.evaluate(styleOf)).toEqual(graph);
  await expect(page.getByRole('complementary', { name: 'Interaction design details' })).toHaveCount(0);
  await context.locator('[data-object]').focus();
  await expect(context.locator('[data-pebble-object]')).toHaveAttribute('data-pebble-scale', '1.1200');
  await page.keyboard.press('Enter');
  await expect(context.locator('[data-pebble-object]')).toHaveAttribute('data-pebble-scale', '1.3500');
  await expect(context.locator('[data-expanded-ring]')).toHaveCount(0);
  await expect(context.locator('[data-map-object-id]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('button', { name: 'Open r02', exact: true })).toBeVisible();
  await expect(page.locator('[data-silk-link]')).toHaveCount(9);
  await expect(page.locator('[data-node-orbit], [data-map-group-light]')).toHaveCount(0);
  if (width === 1774) await page.screenshot({ path: '/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/shared-context-map.png', fullPage: true });
});
