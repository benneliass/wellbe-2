import type { User } from "oidc-client-ts";
import { getApiClient } from "./api";
import { isOidcMode } from "./auth-config";
import { endOidcSession, hasOidcUser } from "./oidc";
import { clearSession, getSession, setSession, type Session } from "./session";

/**
 * Turn a completed ZITADEL login into the app session. The account state comes
 * from the API (the token identity is authoritative there): an active account
 * lands in the workspace, anything else goes through onboarding.
 */
export async function establishOidcSession(user: User): Promise<Session> {
  const { data, error } = await getApiClient().GET("/v1/onboarding");
  if (error || !data) throw new Error("onboarding_state_unavailable");
  const active = data.status === "active";
  const profileName = user.profile.name || user.profile.preferred_username || null;
  const session: Session = {
    issuer: user.profile.iss,
    subject: user.profile.sub,
    patientId: active ? (data.controller_patient_id ?? null) : null,
    actorType: "controller",
    onboarded: active,
    displayName: data.display_name || profileName,
  };
  setSession(session);
  return session;
}

/** Drop an app session whose OIDC login is gone (expired, or signed out elsewhere). */
export async function reconcileOidcSession(): Promise<void> {
  if (!isOidcMode() || !getSession()) return;
  if (!(await hasOidcUser())) clearSession();
}

/** Sign out: clear the app session and, in OIDC mode, end the ZITADEL session. */
export async function signOut(): Promise<void> {
  clearSession();
  if (isOidcMode()) {
    try {
      await endOidcSession();
    } catch {
      /* the local session is already gone; the front door is shown regardless */
    }
  }
}
