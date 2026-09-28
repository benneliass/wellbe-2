import fs from "node:fs";
import path from "node:path";
import { expect, type Page } from "@playwright/test";

/**
 * OIDC mode for the live suite: set E2E_LOGIN_PASSWORD (and E2E_LOGIN_NAME,
 * default "demo") and the specs sign in through WellBe's own /login screen instead
 * of injecting the dev identity, which an OIDC deployment rejects.
 */
export const LOGIN_NAME = process.env.E2E_LOGIN_NAME ?? "demo";
export const LOGIN_PASSWORD = process.env.E2E_LOGIN_PASSWORD ?? "";
export const OIDC = LOGIN_PASSWORD !== "";

/** sessionStorage of a signed-in tab (OIDC tokens + wellbe.session), saved by global setup. */
export const AUTH_STATE_FILE = path.join(__dirname, "..", "test-results", "live-auth.json");

export type StorageDump = Record<string, string>;

export function loadAuthState(): StorageDump | null {
  if (!OIDC || !fs.existsSync(AUTH_STATE_FILE)) return null;
  return JSON.parse(fs.readFileSync(AUTH_STATE_FILE, "utf8")) as StorageDump;
}

/** The access token oidc-client-ts stored under "oidc.user:<issuer>:<client id>". */
export function accessTokenOf(state: StorageDump): string {
  const key = Object.keys(state).find((k) => k.startsWith("oidc.user:"));
  const token = key ? (JSON.parse(state[key]!) as { access_token?: string }).access_token : undefined;
  if (!token) throw new Error(`no OIDC user in ${AUTH_STATE_FILE}`);
  return token;
}

/** Front door -> Sign in -> /login -> credentials -> back in the app. */
export async function signInThroughLoginScreen(page: Page, password = LOGIN_PASSWORD): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: /Sign in/ }).click();
  await page.waitForURL(/\/login\?authRequest=V2_\d+/);
  await expect(page.getByRole("heading", { name: "Sign in to WellBe" })).toBeVisible();
  await page.getByLabel("Email or username").fill(LOGIN_NAME);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: /^Sign in/ }).click();
}

export async function expectSignedIn(page: Page): Promise<void> {
  await page.waitForURL(
    (u) => !u.pathname.startsWith("/login") && !u.pathname.startsWith("/auth/"),
    { timeout: 30_000 },
  );
  await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
}
