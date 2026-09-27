import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./oidc", () => ({
  currentAccessToken: vi.fn(async () => "access-token-123"),
}));

import { getAuthConfig, isOidcMode, oidcConfigured } from "./auth-config";
import { getApiClient } from "./api";
import { getAuthToken, getSession, setSession, type Session } from "./session";

class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.get(key) ?? null;
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

Object.defineProperty(window, "sessionStorage", {
  value: new MemoryStorage(),
  configurable: true,
});

// openapi-fetch captures fetch when the (singleton) client is created, so install
// one stub up front and vary its response per test.
const seen: Request[] = [];
let respond: () => Response = () => new Response("[]", { status: 200 });
globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
  seen.push(input as Request);
  return respond();
}) as typeof fetch;

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const OIDC = {
  mode: "oidc" as const,
  issuer: "https://auth.example",
  clientId: "client-1",
};

const SESSION: Session = {
  issuer: "https://auth.example",
  subject: "zitadel-sub",
  patientId: "p-1",
  actorType: "controller",
  onboarded: true,
  displayName: "Ben",
};

describe("auth mode", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    delete window.__WELLBE_AUTH_CONFIG__;
    vi.unstubAllEnvs();
    seen.length = 0;
    respond = () => json(200, []);
  });

  afterEach(() => {
    delete window.__WELLBE_AUTH_CONFIG__;
  });

  it("defaults to dev mode with no runtime or build config", () => {
    expect(getAuthConfig().mode).toBe("dev");
    expect(isOidcMode()).toBe(false);
    expect(oidcConfigured()).toBe(false);
  });

  it("prefers the runtime config published by /auth-config.js", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_AUTH_MODE", "dev");
    window.__WELLBE_AUTH_CONFIG__ = OIDC;
    expect(getAuthConfig()).toEqual(OIDC);
    expect(oidcConfigured()).toBe(true);
  });

  it("oidc mode without issuer/client id is not considered configured", () => {
    window.__WELLBE_AUTH_CONFIG__ = { mode: "oidc", issuer: "", clientId: "" };
    expect(isOidcMode()).toBe(true);
    expect(oidcConfigured()).toBe(false);
  });

  it("dev mode keeps the session in localStorage and sends no bearer token", async () => {
    setSession(SESSION);
    expect(window.localStorage.getItem("wellbe.session")).not.toBeNull();
    expect(await getAuthToken()).toBeNull();
  });

  it("oidc mode keeps the session in sessionStorage and returns the access token", async () => {
    window.__WELLBE_AUTH_CONFIG__ = OIDC;
    setSession(SESSION);
    expect(window.localStorage.getItem("wellbe.session")).toBeNull();
    expect(window.sessionStorage.getItem("wellbe.session")).not.toBeNull();
    expect(getSession()?.subject).toBe("zitadel-sub");
    expect(await getAuthToken()).toBe("access-token-123");
  });

  it("oidc mode sends the bearer token and no X-Wellbe identity headers", async () => {
    window.__WELLBE_AUTH_CONFIG__ = OIDC;
    setSession(SESSION);
    await getApiClient().GET("/v1/threads");
    expect(seen).toHaveLength(1);
    const headers = seen[0]!.headers;
    expect(headers.get("Authorization")).toBe("Bearer access-token-123");
    for (const name of [
      "X-Wellbe-Issuer",
      "X-Wellbe-Subject",
      "X-Wellbe-Actor-Id",
      "X-Wellbe-Patient-Id",
      "X-Wellbe-Actor-Type",
    ]) {
      expect(headers.get(name)).toBeNull();
    }
  });

  it("oidc mode drops back to onboarding on onboarding_required", async () => {
    window.__WELLBE_AUTH_CONFIG__ = OIDC;
    setSession(SESSION);
    respond = () => json(403, { code: "onboarding_required" });
    await getApiClient().GET("/v1/threads");
    expect(getSession()?.onboarded).toBe(false);
    expect(getSession()?.patientId).toBeNull();
  });

  it("dev mode still sends the X-Wellbe identity headers", async () => {
    setSession(SESSION);
    await getApiClient().GET("/v1/threads");
    const headers = seen[0]!.headers;
    expect(headers.get("X-Wellbe-Actor-Id")).toBe("p-1");
    expect(headers.get("Authorization")).toBeNull();
  });
});
