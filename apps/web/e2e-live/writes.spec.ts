import { API_URL, DEMO_HEADERS, expect, expectCleanPage, snap, test } from "./fixtures";

/**
 * UI write flows. These act on the demo patient's REAL data, so they are kept
 * minimal and clearly labelled:
 *  - one text note per run, "E2E browser check <timestamp>";
 *  - reviewing a Thing noticed only touches a candidate whose title starts with
 *    "E2E", unless E2E_REVIEW_ANY_CANDIDATE=1 explicitly allows dismissing a
 *    seeded one (dismissal is permanent).
 */

test.describe.configure({ mode: "serial" });

interface Candidate {
  candidate_id: string;
  title: string;
  status: string;
  confidence?: number | null;
}

test("submitting a text note from the UI is acknowledged", async ({ page, monitor }) => {
  const text = `E2E browser check ${new Date().toISOString()}`;
  await page.goto("/workspace");
  await page.getByRole("button", { name: "Capture", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Capture" });
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: /Write a note/ }).click();
  await dialog.getByLabel("Your note").fill(text);
  await expectCleanPage(page);

  const posted = page.waitForResponse(
    (r) => r.url() === `${API_URL}/v1/capture` && r.request().method() === "POST",
  );
  await dialog.getByRole("button", { name: "Add to memory" }).click();
  const resp = await posted;
  expect(resp.status(), await resp.text()).toBeLessThan(300);
  const body = (await resp.json()) as { capture_id: string; status: string };
  expect(body.capture_id).toBeTruthy();
  const req = resp.request().postDataJSON() as { capture_type: string; payload: { text: string } };
  expect(req.capture_type).toBe("note");
  expect(req.payload.text).toBe(text);
  expect(resp.request().headers()["idempotency-key"]).toMatch(/[0-9a-f-]{36}/);

  await expect(dialog.getByRole("status")).toContainText("Added to your memory");
  await snap(page, "20-capture-acknowledged", { fullPage: false });
  await dialog.getByRole("button", { name: "Done" }).click();
  await expect(dialog).toBeHidden();
  expect(monitor.calls.some((c) => c.method === "POST" && c.url.endsWith("/v1/capture"))).toBe(true);
});

test("a Thing noticed can be dismissed from the workspace", async ({ page, request }) => {
  const list = (await (
    await request.get(`${API_URL}/v1/things-noticed`, { headers: DEMO_HEADERS })
  ).json()) as Candidate[];
  const pending = list.filter((c) => c.status === "pending");
  const labelled = pending.find((c) => /^E2E/i.test(c.title));
  const allowAny = process.env.E2E_REVIEW_ANY_CANDIDATE === "1";
  const target =
    labelled ??
    (allowAny ? [...pending].sort((a, b) => (a.confidence ?? 0) - (b.confidence ?? 0))[0] : undefined);
  test.skip(
    !target,
    "no E2E-labelled candidate to review; set E2E_REVIEW_ANY_CANDIDATE=1 to dismiss a seeded one",
  );

  await page.goto("/workspace");
  const section = page.getByRole("region", { name: "Things noticed" });
  await expect(section.getByText(target!.title, { exact: true })).toBeVisible();
  await expect(section.getByRole("button", { name: `Confirm ${target!.title}` })).toBeEnabled();

  const dismissed = page.waitForResponse(
    (r) =>
      r.url() === `${API_URL}/v1/things-noticed/${target!.candidate_id}/dismiss` &&
      r.request().method() === "POST",
  );
  await section.getByRole("button", { name: `Dismiss ${target!.title}` }).click();
  expect((await dismissed).status()).toBe(200);
  await expect(section.getByText(target!.title, { exact: true })).toHaveCount(0);
  await expectCleanPage(page);
});

test("a visit packet can be shared, opened by the recipient, and revoked", async ({ page }) => {
  await page.goto("/prepare");
  await page.getByRole("button", { name: "Build packet" }).click();
  await expect(page.getByText(/\d+ of \d+ items included/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Approve and continue" }).click();

  await page.getByPlaceholder(/Dr\. Jane Smith/).fill(`E2E browser check ${new Date().toISOString()}`);
  await page.getByLabel("Access expires").selectOption({ label: "In 24 hours" });
  await page.getByRole("button", { name: "Create link" }).click();

  const created = page.getByRole("region", { name: "Share link created" });
  await expect(created).toBeVisible({ timeout: 30_000 });
  const url = (await created.locator("code").innerText()).trim();
  expect(url).toMatch(/\/shared\/[^/]+$/);
  await snap(page, "21-share-link-created", { fullPage: false });

  const recipient = await page.context().newPage();
  await recipient.goto(new URL(url).pathname);
  await expect(recipient.getByRole("heading", { level: 1, name: "Visit packet" })).toBeVisible();
  await expect(recipient.getByText(/Access expires/)).toBeVisible();
  await expectCleanPage(recipient);
  await snap(recipient, "17-shared-packet");

  await created.getByRole("button", { name: "Revoke access" }).click();
  await expect(created.getByText("Access revoked")).toBeVisible();

  const after = await page.context().newPage();
  await after.goto(new URL(url).pathname);
  await expect(after.getByText(/revoked or expired/)).toBeVisible();
  await expect(after.getByRole("heading", { level: 1, name: "Visit packet" })).toHaveCount(0);
});
