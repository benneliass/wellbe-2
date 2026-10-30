import { expect, test } from "@playwright/test";

test("small graph objects keep visible breathing and soften their percentage when zoomed in", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/design/graph");
  const body = page.locator('[data-node-id="headache"] [data-pebble-body]');
  await expect(body).toBeVisible();
  const sample = () => body.evaluate(async (element) => {
    const surface = element.closest('[data-radius]') as SVGGElement;
    const ctm = surface.getScreenCTM()!;
    const radius = Number(surface.getAttribute('data-radius')) * Math.hypot(ctm.a, ctm.b);
    const scales: number[] = [], widths: number[] = [];
    const start = performance.now();
    await new Promise<void>((resolve) => {
      const frame = () => {
        const scale = element.getAttribute('transform')?.match(/matrix\(([^ ]+)/)?.[1];
        if (scale) {
          scales.push(Number(scale));
          widths.push(element.querySelector('[data-pebble-silhouette]')!.getBoundingClientRect().width);
        }
        if (performance.now() - start < 5600) requestAnimationFrame(frame);
        else resolve();
      };
      requestAnimationFrame(frame);
    });
    return { radius, amplitude: (Math.max(...scales) - Math.min(...scales)) / 2, widthChange: Math.max(...widths) - Math.min(...widths) };
  });
  const small = await sample();
  await page.getByRole('button', { name: 'Zoom in', exact: true }).click({ clickCount: 2 });
  const large = await sample();
  expect(large.radius).toBeGreaterThan(small.radius * 1.3);
  expect(small.amplitude).toBeGreaterThan(large.amplitude * 1.1);
  expect(small.widthChange).toBeGreaterThan(4);
  expect(large.widthChange).toBeGreaterThan(4);
  expect(Math.abs(small.amplitude * small.radius - large.amplitude * large.radius)).toBeLessThan(0.4);
});

for (const view of ["context", "graph"] as const) {
  test(`${view} breathing visibly changes the rendered size with a bounded uniform scale`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto(`/design/${view}`);
    const selector = view === "context" ? '[data-record-id="r01"] [data-pebble-body]' : '[data-node-id="headache"] [data-pebble-body]';
    await expect(page.locator(selector)).toBeVisible();
    const samples = await page.evaluate(async (selector) => {
      const body = document.querySelector(selector)!;
      const values: Array<{ matrix: number[]; width: number }> = [];
      const start = performance.now();
      await new Promise<void>((resolve) => {
        const sample = () => {
          const matrix = body.getAttribute("transform")?.match(/matrix\(([^)]+)\)/)?.[1];
          if (matrix) {
            const silhouette = body.querySelector('[data-pebble-silhouette]')!;
            values.push({ matrix: matrix.split(/\s+/).map(Number), width: silhouette.getBoundingClientRect().width });
          }
          if (performance.now() - start < 3400) requestAnimationFrame(sample);
          else resolve();
        };
        requestAnimationFrame(sample);
      });
      return values;
    }, selector);
    expect(samples.length).toBeGreaterThan(2);
    for (const { matrix } of samples) {
      expect(matrix[0]).toBe(matrix[3]);
      expect(matrix[0]).toBeGreaterThanOrEqual(0.92);
      expect(matrix[0]).toBeLessThanOrEqual(1.08);
    }
    const scales = samples.map(({ matrix }) => matrix[0]!);
    expect(Math.max(...scales) - Math.min(...scales)).toBeGreaterThan(0.025);
    const widths = samples.map(({ width }) => width);
    expect(Math.max(...widths) - Math.min(...widths)).toBeGreaterThan(0.9);
  });

  test(`${view} pebbles are visible on first paint and freeze under reduced motion`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto(`/design/${view}`);
    const node = page.locator(view === "context" ? '[data-record-id="r01"]' : '[data-node-id="headache"]');
    const material = node.locator('[data-pebble-silhouette]');
    await expect(material).toBeVisible();
    expect(await material.getAttribute("d")).toContain("C 29 -101");
    const body = node.locator('[data-pebble-body]');
    await expect(body).toHaveAttribute("opacity", "0.9");
    await expect(body).toHaveAttribute("transform", "rotate(0) scale(1 1)");
    const light = await node.locator('[data-pebble-light]').getAttribute("fx");
    await node.locator('[data-pebble-bounds]').hover({ force: true });
    await expect(body).toHaveAttribute("transform", "rotate(0) scale(1.12 1.12)");
    expect(await node.locator('[data-pebble-light]').getAttribute("fx")).toBe(light);
    expect(await material.evaluate((element) => getComputedStyle(element).visibility)).toBe("visible");
    expect(errors).toEqual([]);
  });

  test(`${view} hover changes the pose, light, and contact shadow with readable labels`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto(`/design/${view}`);
    const node = page.locator(view === "context" ? '[data-record-id="r01"]' : '[data-node-id="headache"]');
    const body = node.locator('[data-pebble-body]');
    await expect(body).toBeVisible();
    const label = node.locator('text').first();
    await expect(label).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await expect.poll(() => label.evaluate((element) => element.getBoundingClientRect().height)).toBeGreaterThan(1);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    const labelGap = await node.evaluate((element) => {
      const disc = element.querySelector('circle')!.getBoundingClientRect();
      return element.querySelector('text')!.getBoundingClientRect().y - (disc.y + disc.height / 2);
    });
    const before = await body.getAttribute("transform");
    const light = await node.locator('[data-pebble-light]').getAttribute("fx");
    const contact = await node.locator('[data-pebble-contact]').getAttribute("opacity");
    const box = await node.locator('[data-pebble-bounds]').evaluate((element) => element.getBoundingClientRect().toJSON());
    await page.mouse.move(box!.x + box!.width * 0.78, box!.y + box!.height * 0.4);
    await expect.poll(() => body.getAttribute("transform")).not.toBe(before);
    await expect.poll(() => node.locator('[data-pebble-light]').getAttribute("fx")).not.toBe(light);
    await expect.poll(() => node.locator('[data-pebble-contact]').getAttribute("opacity")).not.toBe(contact);
    {
      const gap = await node.evaluate((element) => {
        const disc = element.querySelector('circle')!.getBoundingClientRect();
        return element.querySelector('text')!.getBoundingClientRect().y - (disc.y + disc.height / 2);
      });
      expect(Math.abs(gap - labelGap)).toBeLessThan(1.5);
      await expect(node.locator('[data-map-label]')).toHaveCount(1);
    }
    const pose = (await body.getAttribute("transform"))!.match(/-?[\d.]+/g)!.map(Number);
    expect(Math.abs(pose[0]!)).toBeLessThanOrEqual(12);
    expect(pose[1]!).toBeGreaterThanOrEqual(0.92);
    expect(pose[1]!).toBeLessThanOrEqual(1.16);
    // The SVG normal-map light is part of the live material, rather than a static bitmap.
    await expect(node.locator('feSpecularLighting')).toHaveCount(1);
  });

  test(`${view} drag deforms the pebble and release restores its silhouette without selecting`, async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await page.goto(`/design/${view}`);
    const node = page.locator(view === "context" ? '[data-record-id="r01"]' : '[data-node-id="headache"]');
    const body = node.locator('[data-pebble-body]');
    const object = node.locator('[data-pebble-object]');
    await expect(body).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await expect.poll(() => node.locator('[data-pebble-bounds]').evaluate((element) => element.getBoundingClientRect().width)).toBeGreaterThan(1);
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    const box = await node.locator('[data-pebble-bounds]').evaluate((element) => element.getBoundingClientRect().toJSON());
    const x = box.x + box.width / 2, y = box.y + box.height / 2;
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 60, y + 8, { steps: 12 });
    await expect(object).toHaveAttribute("data-pebble-pose", "drag");
    const stretch = async () => Number((await body.getAttribute("transform"))?.match(/matrix\(([-\d.]+)/)?.[1] ?? 1) - Number(await object.getAttribute('data-pebble-scale') ?? 1) + 1;
    await expect.poll(stretch).toBeGreaterThan(1.005);
    expect(await stretch()).toBeLessThanOrEqual(1.03);
    await page.mouse.up();
    await page.mouse.move(1, 1);
    await expect(object).not.toHaveAttribute("data-pebble-pose", "drag");
    await expect.poll(async () => {
      const matrix = (await body.getAttribute("transform"))?.match(/matrix\(([^)]+)\)/)?.[1]?.split(/\s+/).map(Number) ?? [1, 0, 0, 1];
      return Math.abs(matrix[0]! - matrix[3]!) + Math.abs(matrix[1]!) + Math.abs(matrix[2]!);
    }).toBeLessThan(0.001);
    await expect(view === "context" ? node.locator("[data-map-object-id]") : node).toHaveAttribute("aria-pressed", "false");
  });
}
