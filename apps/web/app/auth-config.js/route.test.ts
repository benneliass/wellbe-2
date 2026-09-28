import { afterEach, describe, expect, it } from "vitest";
import { GET } from "./route";

const ENV = [
  "NEXT_PUBLIC_WELLBE_AUTH_MODE",
  "WELLBE_DEMO_LOGIN_ENABLED",
  "WELLBE_ZITADEL_API_URL",
  "WELLBE_ZITADEL_LOGIN_TOKEN",
];

async function config(): Promise<Record<string, unknown>> {
  const text = await GET().text();
  return JSON.parse(text.replace(/^window\.__WELLBE_AUTH_CONFIG__ = /, "").replace(/;\n$/, ""));
}

describe("GET /auth-config.js", () => {
  afterEach(() => {
    for (const name of ENV) delete process.env[name];
  });

  it("publishes demo only when enabled and the login client is configured", async () => {
    process.env["NEXT_PUBLIC_WELLBE_AUTH_MODE"] = "oidc";
    expect((await config())["demo"]).toBe(false);
    process.env["WELLBE_DEMO_LOGIN_ENABLED"] = "true";
    expect((await config())["demo"]).toBe(false);
    process.env["WELLBE_ZITADEL_API_URL"] = "http://zitadel:8090";
    process.env["WELLBE_ZITADEL_LOGIN_TOKEN"] = "pat";
    const cfg = await config();
    expect(cfg).toMatchObject({ mode: "oidc", demo: true });
    expect(JSON.stringify(cfg)).not.toContain("pat");
  });
});
