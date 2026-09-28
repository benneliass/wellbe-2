import { expect, test } from "@playwright/test";
import { injectSession } from "./_session";

/**
 * Nav smoke (Track G, WEL-158/WEL-159): from the workspace, each enabled nav
 * view is reachable and renders its page. Guards that the nav links are not
 * inert — on the desktop rail and on the mobile bottom nav.
 *
 * The workspace shell is session-guarded (WEL-151), so a session is injected first.
 */

test.beforeEach(async ({ page }) => {
  await injectSession(page);
});

const NAV: { label: string; path: string; heading?: string }[] = [
  { label: "Packets", path: "/prepare", heading: "Prepare for appointment" },
  { label: "Memory", path: "/memory" },
  { label: "Results", path: "/results" },
  { label: "Documents", path: "/documents" },
  { label: "Appointments", path: "/appointments" },
  { label: "Graph", path: "/graph", heading: "Open the graph" },
];

for (const item of NAV) {
  test(`nav "${item.label}" routes to ${item.path}`, async ({ page }) => {
    await page.goto("/workspace");
    await page.getByRole("link", { name: item.label }).click();
    await expect(page).toHaveURL(new RegExp(`${item.path}$`));
    await expect(
      page.getByRole("heading", { name: item.heading ?? item.label, exact: true }),
    ).toBeVisible();
  });
}

type Box = { x: number; y: number; width: number; height: number };
const intersects = (a: Box, b: Box) =>
  a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;

/**
 * Launcher (`/`) on desktop: no separate nav (its own actions and Full View reach
 * every destination), the column fits the viewport, and the signals chip stays
 * under Full View.
 */
for (const [width, height] of [
  [1024, 583],
  [1440, 900],
] as const) {
  test.describe(`launcher at ${width}x${height}`, () => {
    test.use({ viewport: { width, height } });

    test(`has no desktop nav and keeps the header in place`, async ({ page }) => {
      await page.goto("/");
      const ask = page.locator("form").filter({ has: page.getByLabel("Ask WellBe") });
      await expect(ask).toBeVisible();
      await expect(page.getByRole("navigation", { name: "Primary" })).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Menu" })).toHaveCount(0);

      const pills = await page.locator("main main button[class*='pill']").all();
      expect(pills).toHaveLength(6);
      const targets: Box[] = [];
      for (const pill of pills) {
        const box = (await pill.boundingBox())!;
        expect(box.width).toBe(148);
        targets.push(box);
      }
      const askBox = (await ask.boundingBox())!;
      const stripBox = (await page.locator("main main [class*='continuity']").first().boundingBox())!;
      targets.push(askBox, stripBox);
      expect(stripBox.y + stripBox.height).toBeLessThanOrEqual(height);

      const { scrollWidth, innerWidth } = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      }));
      expect(scrollWidth).toBeLessThanOrEqual(innerWidth);

      // The signals chip sits directly under Full View, right edges aligned — a
      // named grid cell, so sibling width changes can't slide it sideways.
      const full = (await page.getByRole("button", { name: /Full View/ }).boundingBox())!;
      const chip = (await page.locator('button[aria-controls="launcher-signals-panel"]').boundingBox())!;
      expect(chip.y).toBeGreaterThanOrEqual(full.y + full.height);
      expect(chip.y - (full.y + full.height)).toBeLessThan(32);
      expect(Math.abs(chip.x + chip.width - (full.x + full.width))).toBeLessThanOrEqual(2);
      for (const box of targets) expect(intersects(chip, box)).toBe(false);

      await page.getByRole("button", { name: /Log something/ }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
    });
  });
}

test.describe("mobile bottom nav", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the launcher scrolls in a frame that ends above the bar", async ({ page }) => {
    await page.goto("/");
    const bar = (await page.getByRole("navigation", { name: "Primary" }).boundingBox())!;
    const frame = (await page.locator("#main").boundingBox())!;
    expect(frame.y + frame.height).toBeLessThanOrEqual(bar.y);
  });

  test("shows the five destinations and routes Packets to /prepare", async ({ page }) => {
    await page.goto("/workspace");
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav).toBeVisible();
    for (const label of ["Home", "Threads", "Packets", "Memory"]) {
      await expect(nav.getByRole("link", { name: label })).toBeVisible();
    }
    await expect(nav.getByRole("button", { name: "Capture" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Threads" })).toHaveAttribute("aria-current", "page");
    await nav.getByRole("link", { name: "Packets" }).click();
    await expect(page).toHaveURL(/\/prepare$/);
  });

  test("Capture opens the capture modal", async ({ page }) => {
    await page.goto("/workspace");
    await page.getByRole("navigation", { name: "Primary" }).getByRole("button", { name: "Capture" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });
});
