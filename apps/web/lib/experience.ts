import { isOidcMode } from "./auth-config";
import { devWorkspaceAvailable, signInDev, type Session } from "./session";

/**
 * Guided first-run: the front door and the onboarding wizard.
 *
 * On unless NEXT_PUBLIC_WELLBE_EXPERIENCE is "off", "0", or "false".
 * On, the front door stays up so a person can choose New to WellBe, the
 * seeded Dev workspace, or Try the demo. Off, the dev workspace opens directly.
 * OIDC sign-in is never skipped. A new OIDC identity still finishes onboarding,
 * because the API refuses a workspace until that account is finalized.
 */
export function guidedExperienceEnabled(): boolean {
  const raw = process.env.NEXT_PUBLIC_WELLBE_EXPERIENCE?.trim().toLowerCase();
  return raw !== "off" && raw !== "0" && raw !== "false";
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
