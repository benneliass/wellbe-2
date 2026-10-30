import { expect, test } from "@playwright/test";
import { inspectMapGeometry } from "./_mapGeometry";

for (const width of [1774, 390]) {
  test(`metadata dots orbit clear of names and respond to hover at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1050 });
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.goto('/design/graph');
    const diet = page.locator('[data-node-id="diet"]');
    const dots = diet.locator('[data-orbit-dot]');
    await expect(dots).toHaveCount(3);
    const position = () => dots.first().evaluate((dot) => ({ x: Number(dot.getAttribute('data-orbit-x')), y: Number(dot.getAttribute('data-orbit-y')) }));
    const before = await position();
    await expect.poll(async () => { const after = await position(); return Math.hypot(after.x - before.x, after.y - before.y); }).toBeGreaterThan(1);
    const nameGap = await diet.evaluate((node) => {
      const circle = node.querySelector('circle')!.getBoundingClientRect();
      return node.querySelector('text')!.getBoundingClientRect().y - circle.y - circle.height / 2;
    });
    await diet.focus();
    await expect(dots.first()).toHaveCSS('opacity', '1');
    const nextGap = await diet.evaluate((node) => {
      const circle = node.querySelector('circle')!.getBoundingClientRect();
      return node.querySelector('text')!.getBoundingClientRect().y - circle.y - circle.height / 2;
    });
    expect(Math.abs(nextGap - nameGap)).toBeLessThan(1.5);
    const collision = await diet.evaluate((node) => {
      const label = node.querySelector('text')!.getBoundingClientRect();
      const radius = Number(node.getAttribute('data-pebble-radius'));
      const accent = node.querySelector<SVGGElement>('[data-node-accents]')!;
      const matrix = accent.getScreenCTM()!;
      const dot = node.querySelector('[data-orbit-dot]')!;
      const orbitRadius = Math.hypot(Number(dot.getAttribute('data-orbit-x')), Number(dot.getAttribute('data-orbit-y')));
      const itemRadius = Number(dot.getAttribute('data-orbit-item-radius'));
      if (orbitRadius - itemRadius <= radius * 1.08) return true;
      // Audit the invisible circular orbit, including positions not currently on screen.
      return Array.from({ length: 120 }, (_, index) => {
        const a = index * Math.PI / 60;
        const p = new DOMPoint(Math.cos(a) * orbitRadius, Math.sin(a) * orbitRadius + itemRadius).matrixTransform(matrix);
        return p.y >= label.top && p.x >= label.left && p.x <= label.right;
      }).some(Boolean);
    });
    expect(collision).toBe(false);
    await expect(diet.locator('[data-node-orbit] > path, [data-node-orbit] > ellipse, [data-node-orbit] > circle')).toHaveCount(0);
    const radii = await dots.evaluateAll((elements) => elements.map((dot) => Math.hypot(Number(dot.getAttribute('data-orbit-x')), Number(dot.getAttribute('data-orbit-y')))));
    expect(Math.max(...radii) - Math.min(...radii)).toBeLessThan(0.001);
    await page.keyboard.press('Enter');
    // Activating an expandable object opens its children in the current graph.
    await expect(dots).toHaveCount(0);
    await expect(page.locator('[data-node-id="weightlog"]')).toBeVisible();
    await expect(diet.locator('[data-expanded-ring]')).toHaveCount(0);
    await expect(diet).toHaveAttribute('data-map-expanded', 'true');
    await page.getByRole('button', { name: 'Collapse on map', exact: true }).click();
    await expect(dots).toHaveCount(3);
  });
}

test('hidden special cases have distinct effects and reduced motion freezes every accent', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/design/graph');
  await page.getByRole('button', { name: 'Investigation', exact: true }).click();
  await page.getByRole('button', { name: 'External', exact: true }).click();
  await page.getByRole('button', { name: 'Compare', exact: true }).click();
  await page.getByRole('button', { name: 'Turn on', exact: true }).click();
  for (const kind of ['diamond', 'external', 'comparison', 'bridge', 'open-loop']) await expect(page.locator(`[data-node-accents="${kind}"]`).first()).toBeVisible();
  const badge = page.locator('[data-node-id="headache"] [data-metadata-badge]');
  await page.locator('[data-node-id="headache"]').focus();
  await expect(badge).not.toHaveCSS('filter', 'none');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(page.locator('[data-node-id="headache"] [data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
  const snapshot = () => page.locator('[data-node-accents], [data-badge-glint]').evaluateAll((elements) => elements.map((element) => element.outerHTML));
  const still = await snapshot();
  await page.evaluate(() => new Promise<void>((resolve) => {
    let frames = 0;
    const next = () => ++frames === 12 ? resolve() : requestAnimationFrame(next);
    requestAnimationFrame(next);
  }));
  expect(await snapshot()).toEqual(still);
  const geometry = await page.evaluate(inspectMapGeometry);
  expect(geometry.overlaps).toEqual([]);
});

test('dragging pauses satellite motion without interrupting the drag or selecting the object', async ({ page }) => {
  await page.setViewportSize({ width: 1774, height: 1050 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/design/graph');
  const node = page.locator('[data-node-id="diet"]');
  await expect(node.locator('[data-orbit-dot]')).toHaveCount(3);
  const bounds = await node.locator('[data-pebble-bounds]').boundingBox();
  const x = bounds!.x + bounds!.width / 2, y = bounds!.y + bounds!.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 32, y - 10, { steps: 5 });
  await expect(node).toHaveAttribute('data-pebble-grabbed', 'true');
  const dots = node.locator('[data-orbit-dot]');
  const read = () => dots.evaluateAll((elements) => elements.map((element) => [element.getAttribute('data-orbit-x'), element.getAttribute('data-orbit-y')]));
  const held = await read();
  await page.evaluate(() => new Promise<void>((resolve) => {
    let frames = 0;
    const next = () => ++frames === 8 ? resolve() : requestAnimationFrame(next);
    requestAnimationFrame(next);
  }));
  expect(await read()).toEqual(held);
  await page.mouse.up();
  await page.mouse.move(1, 1);
  await expect.poll(read).not.toEqual(held);
  await expect(node).toHaveAttribute('aria-pressed', 'false');
});
