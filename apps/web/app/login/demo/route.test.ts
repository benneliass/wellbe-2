import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const signInAsDemo = vi.fn();
vi.mock("@/lib/server/zitadel-login", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/server/zitadel-login")>()),
  loginConfigFromEnv: () => ({ apiUrl: "http://z", instanceHost: "", token: "t" }),
  signInAsDemo: (...args: unknown[]) => signInAsDemo(...args),
}));

const { POST } = await import("./route");

const ORIGIN = "https://wellbe.example";

function req(payload: unknown, headers: Record<string, string> = {}) {
  return new Request(`${ORIGIN}/login/demo`, {
    method: "POST",
    headers: { "content-type": "application/json", origin: ORIGIN, ...headers },
    body: JSON.stringify(payload),
  });
}

describe("POST /login/demo", () => {
  beforeEach(() => {
    process.env["WELLBE_WEB_ORIGIN"] = ORIGIN;
    process.env["WELLBE_DEMO_LOGIN_ENABLED"] = "true";
    signInAsDemo.mockResolvedValue({ kind: "ok", callbackUrl: "https://app/cb?code=c" });
  });
  afterEach(() => {
    delete process.env["WELLBE_WEB_ORIGIN"];
    delete process.env["WELLBE_DEMO_LOGIN_ENABLED"];
    delete process.env["WELLBE_DEMO_LOGIN_NAME"];
    signInAsDemo.mockReset();
  });

  it("signs in the configured demo login, never one from the body", async () => {
    process.env["WELLBE_DEMO_LOGIN_NAME"] = "sample";
    const res = await POST(req({ authRequestId: "V2_42", loginName: "admin" }));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ kind: "ok", callbackUrl: "https://app/cb?code=c" });
    expect(signInAsDemo).toHaveBeenCalledWith(expect.anything(), {
      authRequestId: "V2_42",
      loginName: "sample",
    });
  });

  it("does not exist unless enabled", async () => {
    delete process.env["WELLBE_DEMO_LOGIN_ENABLED"];
    expect((await POST(req({ authRequestId: "V2_42" }))).status).toBe(404);
    expect(signInAsDemo).not.toHaveBeenCalled();
  });

  it("rejects cross-origin posts, form posts and malformed ids", async () => {
    expect((await POST(req({ authRequestId: "V2_42" }, { origin: "https://evil.example" }))).status).toBe(403);
    expect((await POST(req({ authRequestId: "V2_42" }, { "content-type": "text/plain" }))).status).toBe(415);
    expect((await POST(req({ authRequestId: "../admin" }))).status).toBe(400);
    expect((await POST(req({}))).status).toBe(400);
    expect(signInAsDemo).not.toHaveBeenCalled();
  });

  it("answers an expired request with 200 and an outage with 502", async () => {
    signInAsDemo.mockResolvedValueOnce({ kind: "expired" });
    const expired = await POST(req({ authRequestId: "V2_42" }));
    expect(expired.status).toBe(200);
    expect(await expired.json()).toEqual({ kind: "expired" });
    signInAsDemo.mockResolvedValueOnce({ kind: "unavailable" });
    expect((await POST(req({ authRequestId: "V2_42" }))).status).toBe(502);
  });
});
