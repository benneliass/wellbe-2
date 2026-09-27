import { defineConfig, devices } from "@playwright/test";

/**
 * Live e2e suite: drives the real web UI against a deployed WellBe (web + API)
 * with the seeded demo patient. Kept separate from playwright.config.ts so the
 * CI cluster smoke (which has no seeded API) never picks these specs up.
 *
 *   E2E_BASE_URL   web origin (default: the homeserver deployment)
 *   E2E_API_URL    API origin (default: the homeserver API)
 *   E2E_SCREENSHOT_DIR  where full-page route screenshots are written
 *
 * When E2E_BASE_URL is a localhost URL, a local `next dev` is started against
 * E2E_API_URL, and the specs proxy API calls through Playwright (the live API's
 * CORS policy only admits the deployed web origin). This is how web-side fixes
 * are verified before they are deployed.
 */
const baseURL = process.env.E2E_BASE_URL ?? "https://wellbe.tail9c487a.ts.net";
const apiURL = process.env.E2E_API_URL ?? "https://wellbe-api.tail9c487a.ts.net";
const local = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/.test(baseURL);
const localPort = local ? new URL(baseURL).port || "3000" : "";

export const DEMO_PATIENT_ID = "de7a0000-0000-4000-8000-000000000001";

export default defineConfig({
  testDir: "./e2e-live",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "test-results/live-report" }]],
  outputDir: "test-results/live-artifacts",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "live-chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: local
    ? {
        command: `npx next dev -p ${localPort}`,
        url: baseURL,
        reuseExistingServer: true,
        timeout: 180_000,
        env: {
          NEXT_PUBLIC_WELLBE_API_URL: apiURL,
          NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID: DEMO_PATIENT_ID,
          NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID: DEMO_PATIENT_ID,
          NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE: "controller",
        },
      }
    : undefined,
});
