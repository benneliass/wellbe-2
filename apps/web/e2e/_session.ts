import type { Page } from "@playwright/test";

/**
 * Inject an onboarded session before the app loads.
 * With the guided experience off, a build that has the seeded patient id also
 * signs that workspace in. This injection keeps smoke flows independent of
 * that build arg, and matches the Dev workspace sign-in.
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
