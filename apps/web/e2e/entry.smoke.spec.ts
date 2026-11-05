import { expect, test } from "@playwright/test";

/**
 * Guided first-run is on unless NEXT_PUBLIC_WELLBE_EXPERIENCE is off.
 * The front door offers New to WellBe and the seeded Dev workspace. Choosing
 * the Dev workspace is explicit. OIDC "Try the demo" is covered by the live suite.
 */

test("root shows the front door and the seeded profile", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Your private health workspace/ })).toBeVisible();
  await expect(page.getByText("New to WellBe")).toBeVisible();
  await expect(page.getByRole("button", { name: /Dev workspace/ })).toBeVisible();
});

test("choosing the Dev workspace opens the launcher", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Dev workspace/ }).click();
  await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
});

test("starting as a new user enters the welcome step", async ({ page }) => {
  await page.goto("/");
  await page.getByText("New to WellBe").click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: /Welcome to WellBe/ })).toBeVisible();
});

test("a guarded workspace route returns to the front door without a session", async ({ page }) => {
  await page.goto("/workspace");
  await expect(page.getByRole("heading", { name: /Your private health workspace/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Dev workspace/ })).toBeVisible();
});
