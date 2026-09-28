import fs from "node:fs";
import path from "node:path";
import { chromium, type FullConfig } from "@playwright/test";
import { AUTH_STATE_FILE, expectSignedIn, OIDC, signInThroughLoginScreen } from "./oidc-login";

/** OIDC mode only: sign in once and save the tab's sessionStorage for every spec. */
export default async function globalSetup(config: FullConfig): Promise<void> {
  if (!OIDC) return;
  const baseURL = config.projects[0]?.use.baseURL;
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ baseURL });
    await signInThroughLoginScreen(page);
    await expectSignedIn(page);
    const state = await page.evaluate(() => {
      const out: Record<string, string> = {};
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i)!;
        out[key] = sessionStorage.getItem(key)!;
      }
      return out;
    });
    fs.mkdirSync(path.dirname(AUTH_STATE_FILE), { recursive: true });
    fs.writeFileSync(AUTH_STATE_FILE, JSON.stringify(state), { mode: 0o600 });
  } finally {
    await browser.close();
  }
}
