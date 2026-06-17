/**
 * Frontend session source (T0.4 / WEL-151).
 *
 * Today the API authenticates via the dev header contract
 * (X-Wellbe-Actor-Id / X-Wellbe-Patient-Id, see backend resolve_principal) rather
 * than full ZITADEL OIDC. This module is the single place that resolves "who is
 * acting", so swapping the dev headers for a real OIDC token later (WEL-151) is a
 * one-file change — every caller goes through getSession()/getAuthToken().
 *
 * The dev identity is supplied via NEXT_PUBLIC env so no real id is ever hardcoded
 * or committed. With no env set, there is no session and the UI shows a calm
 * sign-in state instead of pretending data exists.
 */

export interface Session {
  actorId: string;
  patientId: string;
  actorType: string;
}

export function getSession(): Session | null {
  const actorId = process.env.NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID ?? "";
  if (!actorId) return null;
  return {
    actorId,
    patientId: process.env.NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID || actorId,
    actorType: process.env.NEXT_PUBLIC_WELLBE_DEV_ACTOR_TYPE || "controller",
  };
}

/** True when an identity is configured — surfaced so the UI can prompt sign-in. */
export function hasSession(): boolean {
  return getSession() !== null;
}

/**
 * Bearer token for the API client's getToken hook. No OIDC yet, so this is null
 * in dev; reachability comes from the X-Wellbe-* headers. ZITADEL (WEL-151) wires
 * a real token here.
 */
export async function getAuthToken(): Promise<string | null> {
  return null;
}
