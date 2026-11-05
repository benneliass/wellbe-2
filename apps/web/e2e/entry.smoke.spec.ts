import { expect, test } from "@playwright/test";

/**
 * Guided first-run is off by default (NEXT_PUBLIC_WELLBE_EXPERIENCE).
 * A dev deployment with the seeded workspace opens it directly: no front door,
 * and /onboarding does not show the wizard. Set the flag to on to restore both.
 * OIDC sign-in is unchanged and is covered by the live suite.
 */

test("root opens the seeded workspace without the front door", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
  await expect(page.getByText("New to WellBe")).toHaveCount(0);
});

test("onboarding redirects home while the guided experience is off", async ({ page }) => {
  await page.goto("/onboarding");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Welcome to WellBe/ })).toHaveCount(0);
});

test("a workspace route opens without a prior sign-in click", async ({ page }) => {
  await page.goto("/workspace");
  await expect(page).toHaveURL(/\/workspace$/);
  await expect(page.getByRole("heading", { name: "Carrying forward" })).toBeVisible();
});
