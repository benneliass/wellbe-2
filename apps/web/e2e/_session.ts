import type { Page } from "@playwright/test";

/**
 * Inject an onboarded session before the app loads. There is no auto-login
 * (WEL-151), so workspace/launcher smoke flows must establish a session first.
 * This mirrors what the Dev workspace sign-in produces, but is build-arg
 * independent so it works against any deployed web image.
 */
const DEV_PATIENT_ID = "de7a0000-0000-4000-8000-000000000001";

export async function injectSession(page: Page): Promise<void> {
  await page.addInitScript((patientId) => {
    window.localStorage.setItem(
      "wellbe.session",
      JSON.stringify({
        issuer: "dev-local",
        subject: "dev-controller",
        patientId,
        actorType: "controller",
        onboarded: true,
        displayName: "Dev workspace",
      }),
    );
  }, DEV_PATIENT_ID);
}
