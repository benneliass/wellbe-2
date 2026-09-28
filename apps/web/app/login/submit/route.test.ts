import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const signInWithPassword = vi.fn();
vi.mock("@/lib/server/zitadel-login", () => ({
  loginConfigFromEnv: () => ({ apiUrl: "http://z", instanceHost: "", token: "t" }),
  signInWithPassword: (...args: unknown[]) => signInWithPassword(...args),
}));

const { POST } = await import("./route");

const ORIGIN = "https://wellbe.example";
const body = { authRequestId: "V2_42", loginName: " ben ", password: "pw" };

function req(payload: unknown, headers: Record<string, string> = {}) {
  return new Request(`${ORIGIN}/login/submit`, {
    method: "POST",
    headers: { "content-type": "application/json", origin: ORIGIN, ...headers },
    body: JSON.stringify(payload),
  });
}

describe("POST /login/submit", () => {
  beforeEach(() => {
    process.env["WELLBE_WEB_ORIGIN"] = ORIGIN;
    signInWithPassword.mockResolvedValue({ kind: "ok", callbackUrl: "https://auth/cb" });
  });
  afterEach(() => {
    delete process.env["WELLBE_WEB_ORIGIN"];
    signInWithPassword.mockReset();
  });

  it("passes trimmed credentials through and returns the callback", async () => {
    const res = await POST(req(body));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ kind: "ok", callbackUrl: "https://auth/cb" });
    expect(signInWithPassword).toHaveBeenCalledWith(expect.anything(), {
      authRequestId: "V2_42",
      loginName: "ben",
      password: "pw",
      newPassword: undefined,
    });
  });

  it("rejects cross-origin and origin-less posts", async () => {
    expect((await POST(req(body, { origin: "https://evil.example" }))).status).toBe(403);
    const noOrigin = new Request(`${ORIGIN}/login/submit`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    expect((await POST(noOrigin)).status).toBe(403);
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("rejects form posts and malformed input", async () => {
    expect((await POST(req(body, { "content-type": "text/plain" }))).status).toBe(415);
    expect((await POST(req({ ...body, authRequestId: "../admin" }))).status).toBe(400);
    expect((await POST(req({ ...body, password: "" }))).status).toBe(400);
    expect((await POST(req({ ...body, newPassword: 5 }))).status).toBe(400);
    expect(signInWithPassword).not.toHaveBeenCalled();
  });

  it("answers a wrong password with 200 and its kind", async () => {
    signInWithPassword.mockResolvedValue({ kind: "invalid_credentials" });
    const res = await POST(req(body));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ kind: "invalid_credentials" });
  });
});
