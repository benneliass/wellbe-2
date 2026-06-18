/**
 * Frontend session (WEL-151).
 *
 * The session is established by an *explicit* sign-in — never baked in. There is
 * no auto-login. This is the single place that resolves "who is acting", modelled
 * on the OIDC (issuer, subject) federated identity the backend's resolve_identity
 * expects. Wiring real ZITADEL OIDC later is an adapter swap behind these same
 * functions (signIn* establish the session; getAuthToken returns the id-token).
 *
 * Identity is held client-side (localStorage) so a sign-in survives reloads but is
 * never persisted into the build. The NEXT_PUBLIC dev env is NOT an auto-session;
 * it only supplies the default patient id for the explicitly-chosen "Dev workspace".
 */

const STORAGE_KEY = "wellbe.session";
const EVENT = "wellbe:session";

export interface Session {
  /** OIDC issuer (dev adapter uses "dev-local"). */
  issuer: string;
  /** OIDC subject — the stable per-identity id. */
  subject: string;
  /** Controller/patient id, known only after onboarding (or for the dev identity). */
  patientId: string | null;
  actorType: string;
  onboarded: boolean;
  displayName: string | null;
}

const DEV_ISSUER = "dev-local";
const DEV_SUBJECT = "dev-controller";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

// Snapshot cache: useSyncExternalStore compares snapshots by reference, so
// getSession() MUST return a stable object while the stored value is unchanged.
// Re-parsing JSON on every call returns a fresh object each time, which makes the
// store think it changed on every render -> infinite re-render loop. Cache the
// parsed value keyed on the raw string and only re-parse when the raw changes.
let cachedRaw: string | null = null;
let cachedSession: Session | null = null;

export function getSession(): Session | null {
  if (!isBrowser()) return null;
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
  if (raw === cachedRaw) return cachedSession;
  cachedRaw = raw;
  try {
    cachedSession = raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    cachedSession = null;
  }
  return cachedSession;
}

function write(session: Session | null): void {
  if (!isBrowser()) return;
  // Keep the snapshot cache in lockstep so same-tab reads are immediately stable.
  if (session) {
    cachedRaw = JSON.stringify(session);
    window.localStorage.setItem(STORAGE_KEY, cachedRaw);
  } else {
    cachedRaw = null;
    window.localStorage.removeItem(STORAGE_KEY);
  }
  cachedSession = session;
  window.dispatchEvent(new Event(EVENT));
}

export function setSession(session: Session): void {
  write(session);
}

export function updateSession(patch: Partial<Session>): Session | null {
  const current = getSession();
  if (!current) return null;
  const next = { ...current, ...patch };
  write(next);
  return next;
}

export function clearSession(): void {
  write(null);
}

export function hasSession(): boolean {
  return getSession() !== null;
}

/** The default patient id for the explicitly-chosen Dev workspace (env-supplied). */
export function devPatientId(): string {
  return (
    process.env.NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID ||
    process.env.NEXT_PUBLIC_WELLBE_DEV_ACTOR_ID ||
    ""
  );
}

export function devWorkspaceAvailable(): boolean {
  return devPatientId() !== "";
}

/** Sign in as the seeded dev identity — a real, pre-onboarded, selectable workspace. */
export function signInDev(): Session | null {
  const patientId = devPatientId();
  if (!patientId) return null;
  const session: Session = {
    issuer: DEV_ISSUER,
    subject: DEV_SUBJECT,
    patientId,
    actorType: "controller",
    onboarded: true,
    displayName: "Dev workspace",
  };
  write(session);
  return session;
}

/** Begin a brand-new identity for onboarding. No patient id yet — onboarding mints it. */
export function signInNewUser(): Session {
  const session: Session = {
    issuer: DEV_ISSUER,
    subject: `user-${crypto.randomUUID()}`,
    patientId: null,
    actorType: "controller",
    onboarded: false,
    displayName: null,
  };
  write(session);
  return session;
}

/**
 * Bearer token for the API client. No OIDC yet, so null in the dev adapter;
 * reachability comes from the X-Wellbe-* headers. ZITADEL (WEL-151) returns the
 * real id-token here without touching any caller.
 */
export async function getAuthToken(): Promise<string | null> {
  return null;
}

/** Subscribe to session changes (storage events + same-tab writes). */
export function subscribeSession(cb: () => void): () => void {
  if (!isBrowser()) return () => {};
  const handler = () => cb();
  window.addEventListener(EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}
