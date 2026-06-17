import { expect, test } from "@playwright/test";

/**
 * Home smoke flow (Track 0.5, WEL-155): the front door loads and every launcher
 * pill routes to its honest destination. Guards the T0.1 routing fix end to end.
 */

const PILLS: { name: RegExp; path: string }[] = [
  { name: /Something feels off/, path: "/triage" },
  { name: /What changed\?/, path: "/delta" },
  { name: /Check my patterns/, path: "/patterns" },
  { name: /Prepare for appointment/, path: "/prepare" },
  { name: /Open the graph/, path: "/graph" },
];

test("Home loads with its prompt and all pills", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
  for (const pill of PILLS) {
    await expect(page.getByRole("button", { name: pill.name })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: /Log something/ })).toBeVisible();
});

for (const pill of PILLS) {
  test(`pill "${pill.name.source}" routes to ${pill.path}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: pill.name }).click();
    await expect(page).toHaveURL(new RegExp(`${pill.path}$`));
  });
}

test('"Log something" opens the capture modal instead of navigating', async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Log something/ }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("Ask WellBe carries the typed query to /ask", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Ask WellBe").fill("knee pain");
  await page.getByRole("button", { name: "Go" }).click();
  await expect(page).toHaveURL(/\/ask\?q=knee%20pain$/);
  await expect(page.getByText("knee pain")).toBeVisible();
});
