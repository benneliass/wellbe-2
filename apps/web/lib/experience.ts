import { isOidcMode } from "./auth-config";
import { devWorkspaceAvailable, signInDev, type Session } from "./session";

/**
 * Guided first-run: the front door and the onboarding wizard.
 *
 * Off unless NEXT_PUBLIC_WELLBE_EXPERIENCE is "on", "1", or "true".
 * Off in the dev workspace opens the seeded identity directly so technical
 * work is not gated on the welcome, consent, and baseline steps.
 * OIDC sign-in is never skipped. A new OIDC identity still finishes onboarding,
 * because the API refuses a workspace until that account is finalized.
 */
export function guidedExperienceEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_WELLBE_EXPERIENCE?.trim().toLowerCase();
  return raw === "on" || raw === "1" || raw === "true";
}

/** Dev workspace, guided flow off, and a seeded patient id to enter. */
export function skipGuidedExperience(): boolean {
  return !guidedExperienceEnabled() && !isOidcMode() && devWorkspaceAvailable();
}

/** Open the seeded dev workspace when the guided flow is off. */
export function enterTechnicalWorkspace(): Session | null {
  if (!skipGuidedExperience()) return null;
  return signInDev();
}
