import { expect, test } from "@playwright/test";
import { injectSession } from "./_session";
import { inspectMapGeometry, sampleConnectionGeometry } from "./_mapGeometry";

for (const viewport of [{ width: 1774, height: 1100 }, { width: 390, height: 844 }]) {
  test(`porcelain graph is clear at ${viewport.width}px and retains selection`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await injectSession(page);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/graph?preview=design");
    await page.locator('[data-node-id]').first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator('[data-node-id="headache"] [data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
    const geometry = await page.evaluate(inspectMapGeometry);
    expect(geometry.overlaps).toEqual([]);
    expect(geometry.crossings).toEqual([]);
    const node = page.locator('[data-node-id="headache"]');
    await node.focus();
    await page.keyboard.press("Enter");
    await expect(node).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("complementary", { name: "Details" })).toContainText("Headache");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(viewport.width);
  });
}


test("graph link routes remain stable while a concept moves", async ({ page }) => {
  await injectSession(page);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/graph?preview=design");
  const node = page.locator('[data-node-id="headache"]');
  await node.waitFor();
  const center = await node.locator('circle').first().evaluate((circle: SVGCircleElement) => {
    const point = new DOMPoint(Number(circle.getAttribute('cx')), Number(circle.getAttribute('cy'))).matrixTransform(circle.getScreenCTM()!);
    return { x: point.x, y: point.y };
  });
  await page.mouse.move(center.x, center.y);
  await page.mouse.down();
  let previous = await page.evaluate(sampleConnectionGeometry);
  const plans = previous.map((edge) => edge.plans);
  let maxJump = 0;
  const firstGradient = await page.locator('[data-silk-link] linearGradient').first().getAttribute('x1');
  for (let step = 1; step <= 32; step += 1) {
    await page.mouse.move(center.x + step * 2, center.y + Math.sin(step / 32 * Math.PI) * 35);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => resolve())));
    const current = await page.evaluate(sampleConnectionGeometry);
    const aligned = await page.locator('[data-silk-link]').evaluateAll((groups) => groups.every((group) => {
      const shapes = [...group.querySelectorAll('path')].map((path) => path.getAttribute('d'));
      return shapes.every((d) => d && d === shapes[0]);
    }));
    expect(aligned).toBe(true);
    expect(current.map((edge) => edge.plans)).toEqual(plans);
    for (let edge = 0; edge < current.length; edge += 1) for (let i = 1; i < 16; i += 1) maxJump = Math.max(maxJump, Math.hypot(current[edge]!.points[i]!.x - previous[edge]!.points[i]!.x, current[edge]!.points[i]!.y - previous[edge]!.points[i]!.y));
    previous = current;
  }
  await page.mouse.up();
  expect(await page.locator('[data-silk-link] linearGradient').first().getAttribute('x1')).not.toBe(firstGradient);
  expect(maxJump).toBeLessThan(18);
  await expect(node).toHaveAttribute('aria-pressed', 'false');
});

test("connections carry case colors, blend across cases, and glow on hover and selection", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/design/graph');
  const connection = page.locator('[data-connection][data-source="headache"][data-target="light"]');
  await expect(connection).toBeVisible();
  const group = connection.locator('..');
  const colors = await page.locator('[data-silk-link] linearGradient').evaluateAll((gradients) => gradients.map((gradient) => [...gradient.querySelectorAll('stop')].map((stop) => stop.getAttribute('stop-color'))));
  expect(new Set(colors.flat()).size).toBeGreaterThanOrEqual(3);
  expect(colors.some(([start, end]) => start !== end)).toBe(true);
  const gradientIds = await page.locator('[data-silk-link] linearGradient').evaluateAll((gradients) => gradients.map((gradient) => gradient.id));
  expect(new Set(gradientIds).size).toBe(gradientIds.length);
  const glow = group.locator('[data-link-glow]');
  const quietOpacity = Number(await glow.getAttribute('stroke-opacity'));
  expect(await glow.evaluate((element) => getComputedStyle(element).filter)).toContain('blur');
  const node = page.locator('[data-node-id="headache"]');
  const bounds = await node.locator('circle').first().boundingBox();
  await page.mouse.move(bounds!.x + bounds!.width / 2, bounds!.y + bounds!.height / 2);
  await expect(group).toHaveAttribute('data-highlighted', 'true');
  expect(Number(await glow.getAttribute('stroke-opacity'))).toBeGreaterThan(quietOpacity * 2);
  await node.focus();
  await page.keyboard.press('Enter');
  await page.mouse.move(1, 1);
  await expect(group).toHaveAttribute('data-highlighted', 'true');
  const unrelated = page.locator('[data-connection][data-source="sleep"][data-target="caffeine"]').locator('..');
  await expect(unrelated).toHaveAttribute('opacity', '0.16');
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(glow).toHaveCSS('animation-name', 'none');
  // Let the media preference reach React and reset the hovered node's lift.
  await expect(node.locator('[data-pebble-object]')).toHaveAttribute('data-pebble-pose', 'still');
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  const route = await connection.getAttribute('d');
  await page.evaluate(() => new Promise<void>((resolve) => {
    let frames = 0;
    const tick = () => ++frames === 10 ? resolve() : requestAnimationFrame(tick);
    requestAnimationFrame(tick);
  }));
  expect(await connection.getAttribute('d')).toBe(route);
});
