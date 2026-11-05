import { expect, test } from "@playwright/test";

for (const width of [1774, 390]) {
  test(`map server output hydrates without geometry warnings at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    const warnings: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error' && /hydrat/i.test(message.text())) warnings.push(message.text());
    });
    for (const route of ['/design/graph', '/design/context']) {
      await page.goto(route);
      await expect(page.locator('[data-pebble-pose]').first()).toBeVisible();
      await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    }
    expect(warnings).toEqual([]);
  });
}

test("sample previews open without a session and never request personal records", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const personalRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/v2\//.test(request.url())) personalRequests.push(request.url());
  });
  await page.goto("/design/context");
  await expect(page.getByRole("button", { name: "Monday note", exact: true })).toBeVisible();
  await expect(page.getByText("Design preview · Sample records, not your data", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Monday note", exact: true }).click();
  await page.getByRole("button", { name: "Open r02", exact: true }).click();
  await expect(page.getByRole("button", { name: "Visit summary", exact: true })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("tab", { name: "Cluster detail", exact: true }).click();
  await expect(page).toHaveURL(/\/design\/graph/);
  await expect(page.locator('[data-node-id]').first()).toBeVisible();
  await page.getByRole("tab", { name: "Context map", exact: true }).click();
  await expect(page.getByRole("button", { name: "Monday note", exact: true })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("wellbe.session"))).toBeNull();
  expect(personalRequests).toEqual([]);
});

test("personal map routes open in the dev workspace while the guided experience is off", async ({ page }) => {
  for (const route of ["/context", "/graph"]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: "Open the graph" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Your private health workspace/ })).toHaveCount(0);
  }
  await page.goto("/graph?preview=design");
  await expect(page.getByText("Design preview with sample data — not your records.").first()).toBeVisible();
});
