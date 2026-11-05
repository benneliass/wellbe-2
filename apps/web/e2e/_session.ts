import type { Page } from "@playwright/test";

/**
 * Inject an onboarded session before the app loads. The guided experience is
 * on, so the front door does not sign anyone in. This matches the Dev workspace
 * choice and keeps smoke flows independent of that build arg.
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
