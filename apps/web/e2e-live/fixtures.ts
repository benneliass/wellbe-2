import fs from "node:fs";
import path from "node:path";
import { test as base, expect, type Page, type Response } from "@playwright/test";
import { accessTokenOf, loadAuthState, type StorageDump } from "./oidc-login";

export const BASE_URL = process.env.E2E_BASE_URL ?? "https://wellbe.tail9c487a.ts.net";
export const API_URL = (process.env.E2E_API_URL ?? "https://wellbe-api.tail9c487a.ts.net").replace(
  /\/$/,
  "",
);
export const DEMO_PATIENT_ID = "de7a0000-0000-4000-8000-000000000001";
export const SCREENSHOT_DIR =
  process.env.E2E_SCREENSHOT_DIR ?? path.join(__dirname, "..", "test-results", "live-screens");

const LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/.test(BASE_URL);

export interface ApiCall {
  method: string;
  url: string;
  status: number;
  body?: string;
}

export interface Monitor {
  /** Every API response seen by the page, in order. */
  calls: ApiCall[];
  /** Mark a 4xx as expected for this test (method + path regex + status). */
  allow(method: string, pathRe: RegExp, status: number): void;
  consoleErrors: string[];
  pageErrors: string[];
}

/** The identity the Dev workspace sign-in produces (see lib/session.ts signInDev). */
export const DEV_SESSION = {
  issuer: "dev-local",
  subject: "dev-controller",
  patientId: DEMO_PATIENT_ID,
  actorType: "controller",
  onboarded: true,
  displayName: "Dev workspace",
};

export async function injectDevSession(page: Page): Promise<void> {
  await page.addInitScript((session) => {
    window.localStorage.setItem("wellbe.session", JSON.stringify(session));
  }, DEV_SESSION);
}

/** OIDC mode: the signed-in tab state saved by global-setup.ts, or null in dev mode. */
const AUTH_STATE = loadAuthState();

async function injectOidcSession(page: Page, state: StorageDump): Promise<void> {
  await page.addInitScript((entries) => {
    for (const [key, value] of Object.entries(entries)) window.sessionStorage.setItem(key, value);
  }, state);
}

/**
 * The live API only admits the deployed web origin via CORS. For a local dev
 * server, route API traffic through Playwright (server-side fetch) and answer
 * with permissive CORS headers so the browser accepts it.
 */
async function proxyApiForLocal(page: Page): Promise<void> {
  const origin = new URL(BASE_URL).origin;
  const cors = {
    "access-control-allow-origin": origin,
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS",
    "access-control-expose-headers": "*",
  };
  await page.context().route(`${API_URL}/**`, async (route) => {
    const req = route.request();
    if (req.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: cors });
      return;
    }
    const headers = { ...req.headers() };
    delete headers.origin;
    const resp = await route.fetch({ headers });
    await route.fulfill({ response: resp, headers: { ...resp.headers(), ...cors } });
  });
}

// Known-noisy console output that is not an app error.
const CONSOLE_NOISE = [
  /Download the React DevTools/,
  /\[Fast Refresh\]/,
  /\[HMR\]/,
];

export const test = base.extend<{ monitor: Monitor; devSession: boolean }>({
  devSession: [true, { option: true }],
  monitor: [
    async ({ page, devSession }, use) => {
      const allowed: { method: string; pathRe: RegExp; status: number }[] = [];
      const monitor: Monitor = {
        calls: [],
        consoleErrors: [],
        pageErrors: [],
        allow: (method, pathRe, status) => allowed.push({ method, pathRe, status }),
      };
      const pending: Promise<void>[] = [];

      page.on("console", (msg) => {
        if (msg.type() !== "error") return;
        const text = msg.text();
        if (CONSOLE_NOISE.some((re) => re.test(text))) return;
        monitor.consoleErrors.push(text);
      });
      page.on("pageerror", (err) => monitor.pageErrors.push(err.message));
      page.on("response", (resp: Response) => {
        const url = resp.url();
        if (!url.startsWith(API_URL)) return;
        const method = resp.request().method();
        if (method === "OPTIONS") return;
        const call: ApiCall = { method, url, status: resp.status() };
        monitor.calls.push(call);
        if (resp.status() >= 400) {
          pending.push(
            resp
              .text()
              .then((t) => {
                call.body = t.slice(0, 500);
              })
              .catch(() => {}),
          );
        }
      });

      if (LOCAL) await proxyApiForLocal(page);
      if (devSession) {
        if (AUTH_STATE) await injectOidcSession(page, AUTH_STATE);
        else await injectDevSession(page);
      }

      await use(monitor);

      await Promise.all(pending);
      const isAllowed = (c: ApiCall) =>
        allowed.some(
          (a) =>
            a.method === c.method && a.status === c.status && a.pathRe.test(new URL(c.url).pathname),
        );
      const failures = monitor.calls.filter(
        (c) => c.status >= 500 || (c.status >= 400 && !isAllowed(c)),
      );
      expect(
        failures.map((f) => `${f.method} ${new URL(f.url).pathname} -> ${f.status} ${f.body ?? ""}`),
        "API responses with unexpected 4xx/5xx",
      ).toEqual([]);
      expect(monitor.pageErrors, "uncaught page errors").toEqual([]);
      // A 4xx we explicitly allowed still logs "Failed to load resource" in Chrome.
      const allowedStatuses = new Set(
        monitor.calls.filter((c) => c.status >= 400 && isAllowed(c)).map((c) => c.status),
      );
      const unexpectedConsole = monitor.consoleErrors.filter((t) => {
        const m = /Failed to load resource: the server responded with a status of (\d+)/.exec(t);
        return !(m && allowedStatuses.has(Number(m[1])));
      });
      expect(unexpectedConsole, "console errors").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

const BAD_TEXT: { label: string; re: RegExp }[] = [
  { label: "'Something went wrong'", re: /Something went wrong/i },
  { label: "Next.js application error", re: /Application error: a (client|server)-side exception/i },
  { label: "Unhandled Runtime Error", re: /Unhandled Runtime Error/i },
  { label: "'Couldn't load'/'Couldn't reach'", re: /Couldn.t (load|reach|build)/i },
  { label: "raw 'undefined'", re: /\bundefined\b/ },
  { label: "raw 'NaN'", re: /\bNaN\b/ },
  { label: "'[object Object]'", re: /\[object Object\]/ },
  { label: "raw JSON", re: /\{\s*"[a-z_]+"\s*:/ },
  { label: "'Invalid Date'", re: /Invalid Date/ },
];

/** No error overlay / boundary and no leaked raw values anywhere on the page. */
export async function expectCleanPage(page: Page): Promise<void> {
  await expect(page.locator("nextjs-portal [data-nextjs-dialog]"), "Next.js error overlay").toHaveCount(0);
  const text = await page.locator("body").innerText();
  for (const { label, re } of BAD_TEXT) {
    expect(text, `page shows ${label}`).not.toMatch(re);
  }
}

/**
 * Full-page screenshot into the shared screenshot folder. The workspace shell
 * scrolls inside a fixed-height main column, so scroll containers are unrolled
 * first — otherwise "full page" is just the viewport.
 */
export async function snap(page: Page, name: string, opts: { fullPage?: boolean } = {}): Promise<string> {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const file = path.join(SCREENSHOT_DIR, `${name}.png`);
  if (opts.fullPage === false) {
    await page.screenshot({ path: file });
    return file;
  }
  await page.evaluate(() => {
    const main = document.querySelector("main");
    if (!main) return;
    for (let el: HTMLElement | null = main; el && el !== document.body; el = el.parentElement) {
      el.style.height = "auto";
      el.style.overflow = "visible";
    }
    main.querySelectorAll<HTMLElement>("*").forEach((el) => {
      const oy = getComputedStyle(el).overflowY;
      if ((oy === "auto" || oy === "scroll") && el.scrollHeight > el.clientHeight) {
        el.style.overflow = "visible";
        el.style.height = "auto";
        el.style.maxHeight = "none";
      }
    });
  });
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

/** Headers the web app sends as the demo patient — for read-only API lookups in specs. */
export const DEMO_HEADERS: Record<string, string> = AUTH_STATE
  ? { Authorization: `Bearer ${accessTokenOf(AUTH_STATE)}` }
  : {
      "X-Wellbe-Issuer": DEV_SESSION.issuer,
      "X-Wellbe-Subject": DEV_SESSION.subject,
      "X-Wellbe-Actor-Id": DEMO_PATIENT_ID,
      "X-Wellbe-Patient-Id": DEMO_PATIENT_ID,
      "X-Wellbe-Actor-Type": DEV_SESSION.actorType,
    };
