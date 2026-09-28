/**
 * Server side of WellBe's own sign-in screens (/login).
 *
 * ZITADEL redirects an OIDC authorize request to /login?authRequest=V2_…; the page
 * posts the credentials to /login/submit, which uses the login-client service
 * token (instance role IAM_LOGIN_CLIENT) to check them with the v2 session API and
 * finish the auth request. The browser then follows the returned callback URL,
 * which lands on /auth/callback with the authorization code as before.
 *
 * Only import from route handlers: the service token must never reach the client.
 */

export interface LoginServerConfig {
  /** In-cluster ZITADEL base URL, e.g. http://zitadel:8090. */
  apiUrl: string;
  /** ZITADEL instance domain; required when apiUrl is not the public host. */
  instanceHost: string;
  /** Personal access token of the login-client machine user. */
  token: string;
}

export interface SignInInput {
  authRequestId: string;
  loginName: string;
  password: string;
  /** Present on the second step, when ZITADEL requires a new password. */
  newPassword?: string;
}

export type PasswordRules = {
  minLength: number;
  requiresUppercase: boolean;
  requiresLowercase: boolean;
  requiresNumber: boolean;
  requiresSymbol: boolean;
};

export type SignInResult =
  | { kind: "ok"; callbackUrl: string }
  | { kind: "password_change_required"; rules: PasswordRules | null }
  | { kind: "weak_password"; rules: PasswordRules | null }
  | { kind: "invalid_credentials" }
  | { kind: "locked" }
  | { kind: "expired" }
  | { kind: "unavailable" };

type Fetch = typeof fetch;

class ZitadelHttpError extends Error {
  constructor(
    readonly status: number,
    readonly body: string,
  ) {
    super(`zitadel ${status}`);
  }
}

export function loginConfigFromEnv(env: Record<string, string | undefined> = process.env): LoginServerConfig | null {
  const apiUrl = env["WELLBE_ZITADEL_API_URL"] ?? "";
  const token = env["WELLBE_ZITADEL_LOGIN_TOKEN"] ?? "";
  if (!apiUrl || !token) return null;
  return {
    apiUrl: apiUrl.replace(/\/+$/, ""),
    instanceHost: env["WELLBE_ZITADEL_INSTANCE_HOST"] ?? "",
    token: token.trim(),
  };
}

function client(config: LoginServerConfig, fetchImpl: Fetch) {
  return async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${config.token}`,
      Accept: "application/json",
    };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (config.instanceHost) headers["x-zitadel-instance-host"] = config.instanceHost;
    const res = await fetchImpl(`${config.apiUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
    const text = await res.text();
    if (!res.ok) throw new ZitadelHttpError(res.status, text);
    return (text ? JSON.parse(text) : {}) as T;
  };
}

const isLocked = (err: ZitadelHttpError) => /locked/i.test(err.body);
// The current password was verified just before, so an invalid-argument answer to
// setting the new one means the new password was refused. The messages are
// localized ("Password is too short"), hence no text matching.
const isPolicyViolation = (err: ZitadelHttpError) => err.status === 400;

async function passwordRules(call: ReturnType<typeof client>): Promise<PasswordRules | null> {
  try {
    const res = await call<{ settings?: Partial<Record<keyof PasswordRules, unknown>> }>(
      "GET",
      "/v2/settings/password/complexity",
    );
    const s = res.settings ?? {};
    return {
      minLength: Number(s.minLength ?? 0),
      requiresUppercase: Boolean(s.requiresUppercase),
      requiresLowercase: Boolean(s.requiresLowercase),
      requiresNumber: Boolean(s.requiresNumber),
      requiresSymbol: Boolean(s.requiresSymbol),
    };
  } catch {
    return null;
  }
}

/**
 * Check the credentials and finish the auth request. Every failure the user can
 * act on maps to a result kind; wrong login name and wrong password are
 * deliberately indistinguishable.
 */
export async function signInWithPassword(
  config: LoginServerConfig,
  input: SignInInput,
  fetchImpl: Fetch = fetch,
): Promise<SignInResult> {
  const call = client(config, fetchImpl);
  const authRequest = encodeURIComponent(input.authRequestId);

  try {
    await call("GET", `/v2/oidc/auth_requests/${authRequest}`);
  } catch (err) {
    if (err instanceof ZitadelHttpError && (err.status === 404 || err.status === 400)) {
      return { kind: "expired" };
    }
    return { kind: "unavailable" };
  }

  let session: { sessionId: string; sessionToken: string };
  try {
    session = await call("POST", "/v2/sessions", {
      checks: {
        user: { loginName: input.loginName },
        password: { password: input.password },
      },
    });
  } catch (err) {
    if (!(err instanceof ZitadelHttpError) || err.status >= 500) return { kind: "unavailable" };
    return isLocked(err) ? { kind: "locked" } : { kind: "invalid_credentials" };
  }

  try {
    const { session: detail } = await call<{
      session?: { factors?: { user?: { id?: string } } };
    }>("GET", `/v2/sessions/${encodeURIComponent(session.sessionId)}`);
    const userId = detail?.factors?.user?.id;
    if (!userId) return { kind: "unavailable" };

    const { user } = await call<{ user?: { human?: { passwordChangeRequired?: boolean } } }>(
      "GET",
      `/v2/users/${encodeURIComponent(userId)}`,
    );
    if (user?.human?.passwordChangeRequired) {
      if (!input.newPassword) {
        return { kind: "password_change_required", rules: await passwordRules(call) };
      }
      try {
        await call("POST", `/v2/users/${encodeURIComponent(userId)}/password`, {
          newPassword: { password: input.newPassword, changeRequired: false },
          currentPassword: input.password,
        });
      } catch (err) {
        if (err instanceof ZitadelHttpError && isPolicyViolation(err)) {
          return { kind: "weak_password", rules: await passwordRules(call) };
        }
        throw err;
      }
      session = {
        sessionId: session.sessionId,
        ...(await call<{ sessionToken: string }>(
          "PATCH",
          `/v2/sessions/${encodeURIComponent(session.sessionId)}`,
          {
            sessionToken: session.sessionToken,
            checks: { password: { password: input.newPassword } },
          },
        )),
      };
    }

    const { callbackUrl } = await call<{ callbackUrl?: string }>(
      "POST",
      `/v2/oidc/auth_requests/${authRequest}`,
      { session: { sessionId: session.sessionId, sessionToken: session.sessionToken } },
    );
    if (!callbackUrl || !/^https?:\/\//.test(callbackUrl)) return { kind: "unavailable" };
    return { kind: "ok", callbackUrl };
  } catch (err) {
    if (err instanceof ZitadelHttpError && err.status === 404) return { kind: "expired" };
    return { kind: "unavailable" };
  }
}

export type DemoSignInResult = Extract<SignInResult, { kind: "ok" | "expired" | "unavailable" }>;

/**
 * Login name of the shared demo user, or null when the demo sign-in is off.
 * Server config only: the browser never chooses which user the demo signs in.
 */
export function demoLoginNameFromEnv(env: Record<string, string | undefined> = process.env): string | null {
  if (env["WELLBE_DEMO_LOGIN_ENABLED"] !== "true") return null;
  return (env["WELLBE_DEMO_LOGIN_NAME"] ?? "").trim() || "demo";
}

/**
 * Finish the auth request as the shared demo user without a password: the login
 * client may finalize with a session that only has a user check. The resulting
 * tokens carry no `amr`, since no factor was verified.
 */
export async function signInAsDemo(
  config: LoginServerConfig,
  input: { authRequestId: string; loginName: string },
  fetchImpl: Fetch = fetch,
): Promise<DemoSignInResult> {
  const call = client(config, fetchImpl);
  const authRequest = encodeURIComponent(input.authRequestId);

  try {
    await call("GET", `/v2/oidc/auth_requests/${authRequest}`);
  } catch (err) {
    if (err instanceof ZitadelHttpError && (err.status === 404 || err.status === 400)) {
      return { kind: "expired" };
    }
    return { kind: "unavailable" };
  }

  try {
    const session = await call<{ sessionId: string; sessionToken: string }>("POST", "/v2/sessions", {
      checks: { user: { loginName: input.loginName } },
    });
    const { callbackUrl } = await call<{ callbackUrl?: string }>(
      "POST",
      `/v2/oidc/auth_requests/${authRequest}`,
      { session: { sessionId: session.sessionId, sessionToken: session.sessionToken } },
    );
    if (!callbackUrl || !/^https?:\/\//.test(callbackUrl)) return { kind: "unavailable" };
    return { kind: "ok", callbackUrl };
  } catch (err) {
    if (err instanceof ZitadelHttpError && err.status === 404) return { kind: "expired" };
    return { kind: "unavailable" };
  }
}
