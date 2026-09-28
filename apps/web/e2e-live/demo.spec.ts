import { expect, test } from "@playwright/test";
import { expectSignedIn } from "./oidc-login";

/**
 * "Try the demo" (auth.oidc.customLogin.demo): one click from the front door into
 * the shared demo workspace, with nothing typed. Uses a fresh tab, not the saved
 * sign-in state, and skips on deployments that don't offer the demo.
 */
test("Try the demo opens the shared demo workspace without typing", async ({ page }) => {
  await page.goto("/");
  const demo = await page.evaluate(() => window.__WELLBE_AUTH_CONFIG__?.demo === true);
  test.skip(!demo, "this deployment doesn't offer Try the demo");

  const button = page.getByRole("button", { name: /Try the demo/ });
  await expect(button).toContainText(/shared/i);
  await button.click();
  await page.waitForURL(/\/login\?authRequest=V2_\d+/);
  await expect(page.getByRole("heading", { name: /Opening the demo/ })).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toHaveCount(0);

  await expectSignedIn(page);
  const session = await page.evaluate(() => JSON.parse(sessionStorage.getItem("wellbe.session") ?? "null"));
  expect(session).toMatchObject({ displayName: "Demo", onboarded: true });
});
