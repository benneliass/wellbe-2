import { expect, test } from '@playwright/test';
import { afterMapPaint } from './_mapGeometry';

test('mode changes add weak links without replacing existing connection instances or moving records', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  const graph = page.locator('svg[aria-label^="Map of your concerns"]');
  await expect(graph.locator('[data-connection]')).toHaveCount(14);
  await page.evaluate(afterMapPaint);
  const positions = () => graph.locator('[data-node-id]').evaluateAll((nodes) => nodes.map((node) => [node.getAttribute('data-node-id'), node.getAttribute('data-pebble-x'), node.getAttribute('data-pebble-y')]));
  const before = await positions();
  const existing = graph.locator('[data-silk-link][data-source="dizzy"][data-target="sleep"]');
  await existing.evaluate((node) => node.setAttribute('data-instance-probe', 'original'));
  await page.getByRole('tab', { name: 'Explore all', exact: true }).click();
  await expect(graph.locator('[data-connection]')).toHaveCount(15);
  await expect(graph.locator('[data-connection][data-source="headache"][data-target="fatigue"]')).toHaveCount(1);
  await expect(existing).toHaveAttribute('data-instance-probe', 'original');
  expect(await positions()).toEqual(before);
  await page.getByRole('tab', { name: 'Cluster detail', exact: true }).click();
  await expect(graph.locator('[data-connection]')).toHaveCount(14);
  await expect(existing).toHaveAttribute('data-instance-probe', 'original');
  expect(await positions()).toEqual(before);
});
