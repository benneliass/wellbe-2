import { expect, test } from '@playwright/test';
import { afterMapPaint } from './_mapGeometry';

for (const width of [1774, 390]) test(`headings yield to moved objects and pins are actionable at ${width}px`, async ({ page }) => {
  await page.setViewportSize({ width, height: 1050 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/design/graph');
  const head = page.locator('[data-node-id="headache"]');
  const pin = head.getByRole('button', { name: 'Unpin Headache', exact: true });
  await expect(pin).toBeVisible();
  const clearance = await head.evaluate((node) => {
    const badge = node.querySelector('[data-metadata-badge="pinned"]')!;
    const distance = Math.hypot(Number(badge.getAttribute('data-badge-offset-x')), Number(badge.getAttribute('data-badge-offset-y')));
    return distance - 4.2 - Number(node.querySelector('[data-node-orbit]')!.getAttribute('data-orbit-base-extent'));
  });
  expect(clearance).toBeGreaterThan(3);
  await pin.click();
  await expect(pin).toHaveCount(0);
  await head.press('Enter');
  const panel = page.getByRole('complementary', { name: 'Details' });
  await panel.getByRole('button', { name: 'Pin Headache', exact: true }).click();
  await expect(pin).toBeVisible();
  await page.reload();
  await expect(pin).toBeVisible();
  await pin.press('Enter');
  await page.reload();
  await expect(pin).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Set current view as default', exact: true })).toBeVisible();
  const title = page.locator('[data-group-heading="dig"]');
  const before = (await title.boundingBox())!;
  const body = (await page.locator('[data-node-id="bloods"] [data-pebble-bounds]').boundingBox())!;
  await page.mouse.move(body.x + body.width / 2, body.y + body.height / 2);
  await page.mouse.down();
  await page.mouse.move(before.x + before.width / 2, before.y + before.height / 2, { steps: 20 });
  await page.mouse.up(); await page.mouse.move(2, 2); await page.evaluate(afterMapPaint);
  const overlap = await title.evaluate((heading) => {
    const a = heading.getBoundingClientRect();
    return [...document.querySelectorAll('[data-node-id] [data-pebble-body], [data-node-id] text')].some((part) => {
      const b = part.getBoundingClientRect();
      return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
    });
  });
  expect(overlap).toBe(false);
  if (width === 1774) await page.screenshot({ path: "/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/group-light-coverage/following-heading.png" });
  const after = (await title.boundingBox())!;
  expect(Math.hypot(after.x - before.x, after.y - before.y)).toBeGreaterThan(2);
});
