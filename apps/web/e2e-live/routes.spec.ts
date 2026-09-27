import type { APIRequestContext } from "@playwright/test";
import { API_URL, DEMO_HEADERS, expect, expectCleanPage, snap, test } from "./fixtures";

/**
 * Every route, as the seeded demo patient, against the live deployment. Each test
 * asserts the route's key content is real data from the API (not a mock), the
 * page is clean (no error boundary / raw values), and — via the auto `monitor`
 * fixture — there are no console errors and no unexpected 4xx/5xx API responses.
 */

interface ThreadV1 {
  thread_id: string;
  title: string;
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function apiGet<T>(request: APIRequestContext, path: string): Promise<T> {
  const resp = await request.get(`${API_URL}${path}`, { headers: DEMO_HEADERS });
  expect(resp.status(), `GET ${path}`).toBe(200);
  return (await resp.json()) as T;
}

test("Home (launcher) shows real signals and the prompt", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
  const signals = page.getByRole("button", { name: /current in your records/ });
  await expect(signals).toBeVisible();
  await expect(signals).toContainText(/Recent data for \d+ of \d+ areas/);
  await signals.click();
  const breakdown = page.getByRole("region", { name: "Signal breakdown" });
  await expect(breakdown).toContainText("Cardiovascular");
  await expect(breakdown.getByText("Cardiovascular")).toBeInViewport();
  await expect(breakdown).toHaveCSS("opacity", "1");
  await expectCleanPage(page);
  await snap(page, "01-home");
  // The Ask box and footer must be reachable by scrolling on a 720px-tall screen.
  await signals.click();
  await page.mouse.move(640, 400);
  await page.mouse.wheel(0, 2000);
  await expect(page.getByLabel("Ask WellBe")).toBeInViewport();
  await expect(page.getByText(/Your data is private/)).toBeInViewport();
});

test("Workspace lists the demo patient's health threads", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  expect(threads.length).toBeGreaterThan(0);
  await page.goto("/workspace");
  await expect(page.getByRole("heading", { name: "Carrying forward" })).toBeVisible();
  for (const t of threads) {
    await expect(page.getByRole("link", { name: new RegExp(escapeRe(t.title)) }).first()).toBeVisible();
  }
  await expect(page.getByText(/\d+ open threads?/)).toBeVisible();
  await expectCleanPage(page);
  await snap(page, "02-workspace");
});

test("Workspace shows Things noticed candidates", async ({ page, request }) => {
  const candidates = await apiGet<{ title: string; status: string }[]>(request, "/v1/things-noticed");
  const pending = candidates.filter((c) => c.status === "pending");
  test.skip(pending.length === 0, "no pending candidates left for the demo patient");
  await page.goto("/workspace");
  const section = page.getByRole("region", { name: "Things noticed" });
  await expect(section).toBeVisible();
  for (const c of pending) {
    await expect(section.getByText(c.title, { exact: true })).toBeVisible();
  }
  await expectCleanPage(page);
});

test("Thread page shows its evidence, graph and memories", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  const headache = threads.find((t) => /headache/i.test(t.title)) ?? threads[0];
  if (!headache) throw new Error("demo patient has no threads");
  const memories = await apiGet<{ title: string }[]>(
    request,
    `/v2/threads/${headache.thread_id}/memories`,
  );
  const graph = await apiGet<{ nodes: { label: string }[] }>(
    request,
    `/v2/graph/threads/${headache.thread_id}`,
  );

  await page.goto("/workspace");
  await page.getByRole("link", { name: new RegExp(escapeRe(headache.title)) }).first().click();
  await expect(page).toHaveURL(new RegExp(`/threads/${headache.thread_id}$`));
  await expect(page.getByRole("heading", { name: headache.title, level: 1 })).toBeVisible();

  const mem = page.getByRole("region", { name: "Memories" });
  await expect(mem).toBeVisible();
  for (const m of memories) await expect(mem.getByText(m.title).first()).toBeVisible();

  const g = page.getByRole("region", { name: "Connected in your records" });
  await expect(g).toBeVisible();
  for (const n of graph.nodes) await expect(g.getByText(n.label).first()).toBeVisible();

  await expectCleanPage(page);
  await snap(page, "03-thread-detail");
});

test("Patterns lists non-diagnostic, source-linked patterns", async ({ page, request }) => {
  const resp = await apiGet<{ patterns: { subject_label: string; object_label: string }[] }>(
    request,
    "/v2/patterns",
  );
  await page.goto("/patterns");
  await expect(page.getByRole("heading", { name: "Check my patterns" })).toBeVisible();
  expect(resp.patterns.length).toBeGreaterThan(0);
  const cards = page.getByRole("listitem").filter({ hasText: "not a diagnosis" });
  await expect(cards).toHaveCount(resp.patterns.length);
  await expect(cards.first()).toContainText(resp.patterns[0]!.subject_label);
  await expect(page.getByText(/diagnos/i).first()).toBeVisible();
  await expectCleanPage(page);
  await snap(page, "04-patterns");
});

test("Delta lists what changed", async ({ page, request }) => {
  const resp = await apiGet<{ events: { title: string }[]; window_label: string }>(
    request,
    "/v2/delta",
  );
  expect(resp.events.length).toBeGreaterThan(0);
  await page.goto("/delta");
  await expect(page.getByRole("heading", { name: "What changed?" })).toBeVisible();
  for (const e of resp.events.slice(0, 5)) {
    await expect(page.getByText(e.title, { exact: true }).first()).toBeVisible();
  }
  await expectCleanPage(page);
  await snap(page, "05-delta");
});

test("Ask answers 'What is going on with my headaches?'", async ({ page }) => {
  await page.goto("/ask?q=" + encodeURIComponent("What is going on with my headaches?"));
  await expect(page.getByLabel("Ask WellBe")).toHaveValue("What is going on with my headaches?");
  const answer = page.locator("[data-mode]");
  await expect(answer).toBeVisible({ timeout: 45_000 });
  await expect(answer).toContainText(/headache/i);
  expect((await answer.innerText()).length).toBeGreaterThan(40);
  await expectCleanPage(page);
  await snap(page, "06-ask");
});

test("Prepare builds a visit packet with source-linked statements", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  await page.goto("/prepare");
  await expect(page.getByRole("heading", { name: "Prepare for appointment" })).toBeVisible();
  for (const t of threads) await expect(page.getByRole("button", { name: t.title })).toBeVisible();
  await snap(page, "07-prepare");
  // Building a packet persists a draft for the demo patient (no share, no export).
  await page.getByRole("button", { name: "Build packet" }).click();
  await expect(page.getByText(/\d+ of \d+ items included/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Source-linked summary")).toBeVisible();
  await expectCleanPage(page);
  await snap(page, "08-prepare-packet");
});

test("Graph renders the patient's real nodes", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  const labels = new Set<string>();
  for (const t of threads) {
    const g = await apiGet<{ nodes: { label: string }[] }>(request, `/v2/graph/threads/${t.thread_id}`);
    g.nodes.forEach((n) => labels.add(n.label));
  }
  expect(labels.size).toBeGreaterThan(0);
  await page.goto("/graph");
  await expect(page.getByRole("heading", { name: "Open the graph" })).toBeVisible();
  const map = page.getByRole("img", { name: /Map of your concerns/ });
  await expect(map).toBeVisible();
  for (const l of labels) {
    await expect(map.getByRole("button", { name: new RegExp(`^${escapeRe(l)}, `) })).toBeVisible();
  }
  // No sample-fixture concepts leak into the person's graph.
  await expect(page.getByText("MRI referral")).toHaveCount(0);
  const first = Array.from(labels)[0]!;
  await map.getByRole("button", { name: new RegExp(`^${escapeRe(first)}, `) }).click();
  await expect(page.getByRole("complementary", { name: "Details" })).toContainText(first);
  await page.getByRole("tab", { name: "List" }).click();
  for (const t of threads) {
    await expect(page.getByRole("region", { name: t.title, exact: true })).toBeVisible();
  }
  await expectCleanPage(page);
  await page.getByRole("tab", { name: "Map" }).click();
  await snap(page, "09-graph");
});

test("Memory lists the memories kept around each thread", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  await page.goto("/memory");
  await expect(page.getByRole("heading", { name: "Memory", exact: true })).toBeVisible();
  for (const t of threads) {
    const memories = await apiGet<{ title: string }[]>(request, `/v2/threads/${t.thread_id}/memories`);
    const group = page.getByRole("region", { name: `${t.title} memories` });
    await expect(group).toBeVisible();
    for (const m of memories) await expect(group.getByText(m.title).first()).toBeVisible();
  }
  await expectCleanPage(page);
  await snap(page, "11-memory");
});

test("Appointments shows the open follow-up items", async ({ page, request }) => {
  const items = await apiGet<{ title: string }[]>(request, "/v2/pending-items");
  await page.goto("/appointments");
  await expect(page.getByRole("heading", { name: "Appointments", exact: true })).toBeVisible();
  for (const i of items) await expect(page.getByText(i.title).first()).toBeVisible();
  await expectCleanPage(page);
  await snap(page, "10-appointments");
});

const PLACEHOLDERS: { path: string; heading: string; shot: string }[] = [
  { path: "/results", heading: "Results", shot: "12-results" },
  { path: "/documents", heading: "Documents", shot: "13-documents" },
  { path: "/triage", heading: "Something feels off", shot: "14-triage" },
];

for (const r of PLACEHOLDERS) {
  test(`${r.path} renders its view`, async ({ page }) => {
    await page.goto(r.path);
    await expect(page.getByRole("heading", { name: r.heading, exact: true })).toBeVisible();
    // Not built yet (product gap): the route is an honest "In progress" placeholder.
    await expect(page.getByText("In progress")).toBeVisible();
    test.info().annotations.push({ type: "product-gap", description: `${r.path} is a placeholder` });
    await expectCleanPage(page);
    await snap(page, r.shot);
  });
}

test.describe("signed out", () => {
  test.use({ devSession: false });

  test("front door offers the Dev workspace and signs in to the launcher", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Your private health workspace/ })).toBeVisible();
    await snap(page, "00-entry");
    await page.getByRole("button", { name: /Dev workspace/ }).click();
    await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
    await expectCleanPage(page);
  });

  test("onboarding renders its first step", async ({ page }) => {
    // Opening onboarding starts (or resumes) a pending draft. A fixed, labelled
    // subject keeps that idempotent instead of minting a new draft every run.
    await page.addInitScript(() => {
      window.localStorage.setItem(
        "wellbe.session",
        JSON.stringify({
          issuer: "dev-local",
          subject: "e2e-browser-check-onboarding",
          patientId: null,
          actorType: "controller",
          onboarded: false,
          displayName: null,
        }),
      );
    });
    await page.goto("/onboarding");
    await expect(page.getByRole("heading", { name: /Welcome to WellBe/ })).toBeVisible();
    await expectCleanPage(page);
    await snap(page, "15-onboarding");
  });

  test("an unknown share token shows a calm not-available state", async ({ page, monitor }) => {
    monitor.allow("GET", /^\/v2\/share\//, 404);
    monitor.allow("GET", /^\/v2\/share\//, 410);
    await page.goto("/shared/e2e-not-a-real-token");
    // The API answers 404 for missing, revoked, expired and passcode-gated links
    // alike (no information leak), so the page must cover both readings.
    await expect(page.getByRole("heading", { name: /passcode/i })).toBeVisible();
    await expect(page.getByText(/revoked or expired/)).toBeVisible();
    await expectCleanPage(page);
    await snap(page, "16-shared-invalid");
  });
});
