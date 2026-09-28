import { describe, expect, it } from "vitest";
import {
  demoLoginNameFromEnv,
  loginConfigFromEnv,
  signInAsDemo,
  signInWithPassword,
  type LoginServerConfig,
} from "./zitadel-login";

const config: LoginServerConfig = {
  apiUrl: "http://zitadel:8090",
  instanceHost: "auth.example",
  token: "login-pat",
};
const input = { authRequestId: "V2_1", loginName: "ben", password: "old-Secret1" };

type Route = (body: unknown) => { status: number; body?: unknown };

/** A fake ZITADEL keyed by "METHOD path"; records every call. */
function fakeZitadel(routes: Record<string, Route>) {
  const calls: { key: string; body: unknown; headers: Record<string, string> }[] = [];
  const impl = (async (url: string, init: RequestInit) => {
    const key = `${init.method} ${new URL(url).pathname}`;
    const body = init.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ key, body, headers: init.headers as Record<string, string> });
    const route = routes[key];
    const res = route ? route(body) : { status: 404, body: { message: "not found" } };
    return new Response(res.body === undefined ? "" : JSON.stringify(res.body), {
      status: res.status,
    });
  }) as unknown as typeof fetch;
  return { impl, calls };
}

const happy = (changeRequired = false): Record<string, Route> => ({
  "GET /v2/oidc/auth_requests/V2_1": () => ({ status: 200, body: { authRequest: { id: "V2_1" } } }),
  "POST /v2/sessions": () => ({ status: 201, body: { sessionId: "s1", sessionToken: "t1" } }),
  "GET /v2/sessions/s1": () => ({
    status: 200,
    body: { session: { factors: { user: { id: "u1" } } } },
  }),
  "GET /v2/users/u1": () => ({
    status: 200,
    body: { user: { human: changeRequired ? { passwordChangeRequired: true } : {} } },
  }),
  "POST /v2/oidc/auth_requests/V2_1": () => ({
    status: 200,
    body: { callbackUrl: "https://auth.example/oauth/v2/authorize/callback?id=V2_1" },
  }),
  "GET /v2/settings/password/complexity": () => ({
    status: 200,
    body: { settings: { minLength: "8", requiresUppercase: true, requiresNumber: true } },
  }),
});

describe("signInWithPassword", () => {
  it("checks the password and finalizes the auth request with the session", async () => {
    const z = fakeZitadel(happy());
    const result = await signInWithPassword(config, input, z.impl);
    expect(result).toEqual({
      kind: "ok",
      callbackUrl: "https://auth.example/oauth/v2/authorize/callback?id=V2_1",
    });
    expect(z.calls.find((c) => c.key === "POST /v2/sessions")?.body).toEqual({
      checks: { user: { loginName: "ben" }, password: { password: "old-Secret1" } },
    });
    expect(z.calls.at(-1)?.body).toEqual({ session: { sessionId: "s1", sessionToken: "t1" } });
    for (const call of z.calls) {
      expect(call.headers["Authorization"]).toBe("Bearer login-pat");
      expect(call.headers["x-zitadel-instance-host"]).toBe("auth.example");
    }
  });

  it("does not distinguish an unknown login name from a wrong password", async () => {
    for (const status of [400, 404]) {
      const z = fakeZitadel({
        ...happy(),
        "POST /v2/sessions": () => ({ status, body: { message: "Errors.User.NotFound" } }),
      });
      expect(await signInWithPassword(config, input, z.impl)).toEqual({ kind: "invalid_credentials" });
    }
  });

  it("reports a locked login", async () => {
    const z = fakeZitadel({
      ...happy(),
      "POST /v2/sessions": () => ({ status: 412, body: { message: "Errors.User.Locked" } }),
    });
    expect(await signInWithPassword(config, input, z.impl)).toEqual({ kind: "locked" });
  });

  it("treats an unknown auth request as expired before checking credentials", async () => {
    const z = fakeZitadel({ ...happy(), "GET /v2/oidc/auth_requests/V2_1": () => ({ status: 404 }) });
    expect(await signInWithPassword(config, input, z.impl)).toEqual({ kind: "expired" });
    expect(z.calls.map((c) => c.key)).toEqual(["GET /v2/oidc/auth_requests/V2_1"]);
  });

  it("asks for a new password when ZITADEL requires one, without finalizing", async () => {
    const z = fakeZitadel(happy(true));
    const result = await signInWithPassword(config, input, z.impl);
    expect(result).toEqual({
      kind: "password_change_required",
      rules: {
        minLength: 8,
        requiresUppercase: true,
        requiresLowercase: false,
        requiresNumber: true,
        requiresSymbol: false,
      },
    });
    expect(z.calls.some((c) => c.key === "POST /v2/oidc/auth_requests/V2_1")).toBe(false);
  });

  it("changes the password, re-checks the session and finalizes", async () => {
    const z = fakeZitadel({
      ...happy(true),
      "POST /v2/users/u1/password": () => ({ status: 200, body: {} }),
      "PATCH /v2/sessions/s1": () => ({ status: 200, body: { sessionToken: "t2" } }),
    });
    const result = await signInWithPassword(config, { ...input, newPassword: "New-Secret2" }, z.impl);
    expect(result.kind).toBe("ok");
    expect(z.calls.find((c) => c.key === "POST /v2/users/u1/password")?.body).toEqual({
      newPassword: { password: "New-Secret2", changeRequired: false },
      currentPassword: "old-Secret1",
    });
    expect(z.calls.at(-1)?.body).toEqual({ session: { sessionId: "s1", sessionToken: "t2" } });
  });

  it("returns the rules when the new password is rejected by policy", async () => {
    const z = fakeZitadel({
      ...happy(true),
      "POST /v2/users/u1/password": () => ({
        status: 400,
        body: { code: 3, message: "Password is too short (DOMAIN-HuJf6)" },
      }),
    });
    const result = await signInWithPassword(config, { ...input, newPassword: "weak" }, z.impl);
    expect(result.kind).toBe("weak_password");
  });

  it("maps outages to unavailable", async () => {
    const z = fakeZitadel({ ...happy(), "POST /v2/sessions": () => ({ status: 503 }) });
    expect(await signInWithPassword(config, input, z.impl)).toEqual({ kind: "unavailable" });
    const down = (async () => {
      throw new TypeError("fetch failed");
    }) as unknown as typeof fetch;
    expect(await signInWithPassword(config, input, down)).toEqual({ kind: "unavailable" });
  });
});

describe("loginConfigFromEnv", () => {
  it("needs the API URL and the token", () => {
    expect(loginConfigFromEnv({ WELLBE_ZITADEL_API_URL: "http://z" })).toBeNull();
    expect(
      loginConfigFromEnv({
        WELLBE_ZITADEL_API_URL: "http://z:8090/",
        WELLBE_ZITADEL_LOGIN_TOKEN: " pat\n",
        WELLBE_ZITADEL_INSTANCE_HOST: "auth.example",
      }),
    ).toEqual({ apiUrl: "http://z:8090", token: "pat", instanceHost: "auth.example" });
  });
});

describe("signInAsDemo", () => {
  const demo = { authRequestId: "V2_1", loginName: "demo" };

  it("finalizes the auth request with a user-only session for the demo login", async () => {
    const z = fakeZitadel(happy());
    expect(await signInAsDemo(config, demo, z.impl)).toEqual({
      kind: "ok",
      callbackUrl: "https://auth.example/oauth/v2/authorize/callback?id=V2_1",
    });
    expect(z.calls.map((c) => c.key)).toEqual([
      "GET /v2/oidc/auth_requests/V2_1",
      "POST /v2/sessions",
      "POST /v2/oidc/auth_requests/V2_1",
    ]);
    expect(z.calls[1]?.body).toEqual({ checks: { user: { loginName: "demo" } } });
    expect(z.calls[2]?.body).toEqual({ session: { sessionId: "s1", sessionToken: "t1" } });
    expect(z.calls[0]?.headers["Authorization"]).toBe("Bearer login-pat");
  });

  it("reports an expired or used auth request", async () => {
    const gone = fakeZitadel({ ...happy(), "GET /v2/oidc/auth_requests/V2_1": () => ({ status: 404 }) });
    expect(await signInAsDemo(config, demo, gone.impl)).toEqual({ kind: "expired" });
    const used = fakeZitadel({ ...happy(), "POST /v2/oidc/auth_requests/V2_1": () => ({ status: 404 }) });
    expect(await signInAsDemo(config, demo, used.impl)).toEqual({ kind: "expired" });
  });

  it("maps a missing demo user or an outage to unavailable", async () => {
    const missing = fakeZitadel({ ...happy(), "POST /v2/sessions": () => ({ status: 400 }) });
    expect(await signInAsDemo(config, demo, missing.impl)).toEqual({ kind: "unavailable" });
    const bad = fakeZitadel({
      ...happy(),
      "POST /v2/oidc/auth_requests/V2_1": () => ({ status: 200, body: { callbackUrl: "javascript:x" } }),
    });
    expect(await signInAsDemo(config, demo, bad.impl)).toEqual({ kind: "unavailable" });
  });
});

describe("demoLoginNameFromEnv", () => {
  it("is off unless enabled, and defaults the login name to demo", () => {
    expect(demoLoginNameFromEnv({})).toBeNull();
    expect(demoLoginNameFromEnv({ WELLBE_DEMO_LOGIN_ENABLED: "false", WELLBE_DEMO_LOGIN_NAME: "demo" })).toBeNull();
    expect(demoLoginNameFromEnv({ WELLBE_DEMO_LOGIN_ENABLED: "true" })).toBe("demo");
    expect(demoLoginNameFromEnv({ WELLBE_DEMO_LOGIN_ENABLED: "true", WELLBE_DEMO_LOGIN_NAME: " sample " })).toBe("sample");
  });
});
