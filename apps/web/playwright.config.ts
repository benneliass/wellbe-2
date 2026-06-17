import { defineConfig, devices } from "@playwright/test";

/**
 * E2e harness for the web app (Track 0.5, WEL-155).
 *
 * Default target is a local dev server (http://localhost:3000) so the smoke
 * suite runs anywhere. The Track 0.6 cluster gate sets E2E_BASE_URL to the kind
 * ingress (http://app.localhost) to exercise the real deploy — when that is set,
 * Playwright does not start a dev server.
 */
const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const useExternalServer = Boolean(process.env.E2E_BASE_URL);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: useExternalServer
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
