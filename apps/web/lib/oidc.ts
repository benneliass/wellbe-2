import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";
import { getAuthConfig } from "./auth-config";

/**
 * Authorization Code + PKCE against ZITADEL (public client, no secret).
 *
 * Tokens and the in-flight PKCE state live in sessionStorage (per tab, cleared
 * when the tab closes) — never localStorage. With the offline_access scope
 * ZITADEL issues a refresh token, which automaticSilentRenew uses to refresh the
 * access token shortly before it expires.
 */

export const CALLBACK_PATH = "/auth/callback";

let manager: UserManager | null = null;

export function getUserManager(): UserManager {
  if (manager) return manager;
  const { issuer, clientId } = getAuthConfig();
  if (!issuer || !clientId) {
    throw new Error("OIDC sign-in is not configured (issuer / client id missing).");
  }
  const origin = window.location.origin;
  const store = new WebStorageStateStore({ store: window.sessionStorage });
  manager = new UserManager({
    authority: issuer,
    client_id: clientId,
    redirect_uri: `${origin}${CALLBACK_PATH}`,
    post_logout_redirect_uri: `${origin}/`,
    response_type: "code",
    scope: "openid profile email offline_access",
    userStore: store,
    stateStore: store,
    automaticSilentRenew: true,
    loadUserInfo: false,
  });
  return manager;
}

const DEMO_INTENT_KEY = "wellbe.demoSignIn";
const DEMO_INTENT_TTL_MS = 10 * 60 * 1000;

/**
 * Redirect to the ZITADEL login. With `demo`, the /login page this tab comes back
 * to opens the shared demo workspace instead of asking for credentials.
 */
export async function beginSignIn(options: { demo?: boolean } = {}): Promise<void> {
  if (options.demo) window.sessionStorage.setItem(DEMO_INTENT_KEY, String(Date.now()));
  else window.sessionStorage.removeItem(DEMO_INTENT_KEY);
  await getUserManager().signinRedirect();
}

/** Whether this tab just chose "Try the demo". Consumed on read. */
export function takeDemoSignInIntent(): boolean {
  const at = Number(window.sessionStorage.getItem(DEMO_INTENT_KEY));
  window.sessionStorage.removeItem(DEMO_INTENT_KEY);
  return at > 0 && Date.now() - at < DEMO_INTENT_TTL_MS;
}

let callbackOnce: Promise<User | undefined> | null = null;

/** Complete the redirect (or silent-renew iframe) callback. Safe to call twice —
 * the authorization code is single-use, so React strict-mode re-runs share it. */
export function completeSignIn(): Promise<User | undefined> {
  if (!callbackOnce) callbackOnce = getUserManager().signinCallback();
  return callbackOnce;
}

/** A usable access token, refreshing via the refresh token when it has expired. */
export async function currentAccessToken(): Promise<string | null> {
  const um = getUserManager();
  let user = await um.getUser();
  if (user?.expired && user.refresh_token) {
    try {
      user = await um.signinSilent();
    } catch {
      user = null;
    }
  }
  if (!user || user.expired) return null;
  return user.access_token;
}

/** Whether a live (or refreshable) OIDC user is present in this tab. */
export async function hasOidcUser(): Promise<boolean> {
  const user = await getUserManager().getUser();
  return !!user && (!user.expired || !!user.refresh_token);
}

export async function endOidcSession(): Promise<void> {
  const um = getUserManager();
  const user = await um.getUser();
  await um.removeUser();
  if (user) {
    await um.signoutRedirect({ id_token_hint: user.id_token });
  }
}
