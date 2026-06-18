import { expect, test } from "@playwright/test";
import { injectSession } from "./_session";

/**
 * Sidebar nav smoke (Track G, WEL-158/WEL-159): from the workspace, each enabled
 * nav view is reachable and renders its honest placeholder. Guards that the nav
 * links are no longer inert.
 *
 * The workspace shell is session-guarded (WEL-151), so a session is injected first.
 */

test.beforeEach(async ({ page }) => {
  await injectSession(page);
});

const NAV: { label: string; path: string }[] = [
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
    await expect(page.getByRole("heading", { name: item.label, exact: true })).toBeVisible();
  });
}
