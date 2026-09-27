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

test.describe("mobile bottom nav", () => {
  test.use({ viewport: { width: 390, height: 844 } });

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
