import { expect, test } from "@playwright/test";

/**
 * Front-door smoke (WEL-151 / WEL-181 / WEL-184): with no session, the root shows
 * the explicit entry screen (never an auto-login), and choosing "New to WellBe"
 * leads into onboarding. A fresh context has empty storage, so no session exists.
 */

test("root shows the front door when there is no session", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Your private health workspace/ }),
  ).toBeVisible();
  await expect(page.getByText("New to WellBe")).toBeVisible();
});

test("starting as a new user enters onboarding", async ({ page }) => {
  await page.goto("/");
  await page.getByText("New to WellBe").click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: /Welcome to WellBe/ })).toBeVisible();
});

test("a guarded workspace route redirects to the front door without a session", async ({
  page,
}) => {
  await page.goto("/workspace");
  await expect(
    page.getByRole("heading", { name: /Your private health workspace/ }),
  ).toBeVisible();
});
