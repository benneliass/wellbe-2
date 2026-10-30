import { expect, test } from '@playwright/test';
import { injectSession } from './_session';
import { inspectMapGeometry } from './_mapGeometry';

for (const route of ['/design/graph', '/graph?preview=design']) {
  test(`source records remain orbiting when Headache is selected on ${route}`, async ({ page }) => {
    if (route.startsWith('/graph')) await injectSession(page);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(route);
    const parent = page.locator('[data-node-id="headache"]');
    const sources = parent.locator('[data-orbit-kind="source"]');
    await expect(sources).toHaveCount(5);
    // Source identity and appearance are stable; orbit radius deliberately
    // expands with the selected parent without enlarging the source objects.
    const read = () => sources.evaluateAll((items) => items.map((item) => ({ id: item.getAttribute('data-orbit-item'), content: item.innerHTML })));
    const before = await read();
    const graphNodes = await page.locator('[data-node-id]').count();
    const links = await page.locator('[data-connection]').count();
    const circle = await parent.locator('[data-pebble-bounds]').boundingBox();
    await page.mouse.click(circle!.x + circle!.width / 2, circle!.y + circle!.height / 2);
    await expect(parent).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('complementary', { name: 'Details' })).toContainText('Clinical note');
    await expect(page.getByRole('button', { name: /^(Expand|Collapse) on map$/ })).toHaveCount(0);
    expect(await read()).toEqual(before);
    expect(await page.locator('[data-node-id]').count()).toBe(graphNodes);
    expect(await page.locator('[data-connection]').count()).toBe(links);
    await expect(page.locator('[data-source-marker]')).toHaveCount(0);
    await parent.focus();
    await page.keyboard.press('Enter');
    expect(await read()).toEqual(before);
    expect((await page.evaluate(inspectMapGeometry)).overlaps).toEqual([]);
    await page.getByRole('button', { name: 'Observations', exact: true }).click();
    await expect(sources).toHaveCount(0);
    await expect(page.locator('[data-node-id="diet"] [data-orbit-kind="concept"]')).toHaveCount(3);
    await page.getByRole('button', { name: 'Observations', exact: true }).click();
    await expect(sources).toHaveCount(5);
    if (route === '/design/graph') await page.locator('svg[aria-label^="Map of your concerns"]').screenshot({ path: '/Users/benelias/repos/wellbe-2/output/design/context-map-concepts/source-orbits/headache-selected.png' });
  });
}
