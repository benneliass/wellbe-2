import type { APIRequestContext, Page } from "@playwright/test";
import { API_URL, DEMO_HEADERS, expect, expectCleanPage, snap, test } from "./fixtures";
import { expectSignedIn, OIDC, signInThroughLoginScreen } from "./oidc-login";
import type { PendingItemV2 } from "@/lib/pending";
import { openPendingItems } from "@/lib/pending";

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

  // Memories are the "Your story" lanes; a long story is previewed behind "Show all".
  const story = page.getByRole("region", { name: "Your story" });
  await expect(story).toBeVisible();
  await expect(story.getByText(`${memories.length} kept`)).toBeVisible();
  const showAll = story.getByRole("button", { name: /Show all/ });
  if (await showAll.count()) await showAll.click();
  for (const m of memories) {
    await expect(story.getByText(new RegExp(escapeRe(m.title || "Untitled entry"), "i")).first()).toBeVisible();
  }

  // Connections sit behind a disclosure (L4).
  await page.getByRole("button", { name: "Explore connections" }).click();
  const g = page.locator("section", {
    has: page.getByRole("heading", { name: "Connected in your records" }),
  });
  await expect(g.first()).toBeVisible();
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

const GRAPH_FIXTURE_LABELS = ["MRI referral", "Late caffeine", "Light sensitivity", "Screen time"];

/** Pairs of on-canvas labels (node labels + concern titles) whose boxes intersect. */
async function overlappingGraphLabels(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const els = Array.from(
      document.querySelectorAll<SVGTextElement>('svg [class*="nodeLabel"], svg [class*="clusterLabel"]'),
    );
    const boxes = els.map((el) => ({ text: el.textContent ?? "", r: el.getBoundingClientRect() }));
    const out: string[] = [];
    for (let i = 0; i < boxes.length; i++)
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i]!.r, b = boxes[j]!.r;
        if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) {
          out.push(`${boxes[i]!.text} × ${boxes[j]!.text}`);
        }
      }
    return out;
  });
}

test("Graph renders the patient's real data in the cockpit", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  const labels = new Set<string>();
  const investigative = new Set<string>();
  for (const t of threads) {
    const g = await apiGet<{ nodes: { label: string; type: string }[] }>(request, `/v2/graph/threads/${t.thread_id}`);
    g.nodes.forEach((n) => (n.type === "Theory" || n.type === "Investigation" ? investigative : labels).add(n.label));
  }
  expect(labels.size).toBeGreaterThan(0);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/graph");
  await expect(page.getByRole("heading", { name: "Open the graph" })).toBeVisible();
  const map = page.getByRole("group", { name: /Map of your concerns/ });
  await expect(map).toBeVisible();
  for (const t of threads) await expect(map.getByText(t.title, { exact: true }).first()).toBeVisible();
  for (const l of labels) {
    await expect(map.getByRole("button", { name: new RegExp(`^${escapeRe(l)}, `, "i") })).toBeVisible();
  }
  // No sample-fixture concepts leak into the person's graph.
  for (const l of GRAPH_FIXTURE_LABELS) await expect(page.getByText(l)).toHaveCount(0);
  await expect(page.getByText(/Design preview/)).toHaveCount(0);

  for (const [w, h] of [[1440, 900], [1024, 583], [390, 844]] as const) {
    await page.setViewportSize({ width: w, height: h });
    await expect(map).toBeVisible();
    await page.waitForTimeout(400);
    expect(await overlappingGraphLabels(page), `label overlap at ${w}x${h}`).toEqual([]);
    await snap(page, `09-graph-${w}x${h}`, { fullPage: false });
  }
  await snap(page, "09-graph-390-full");
  await page.setViewportSize({ width: 1440, height: 900 });

  // Theories and investigations live in the Investigation layer (off by default).
  if (investigative.size) {
    await page.getByRole("button", { name: "Investigation", exact: true }).click();
    for (const l of investigative) {
      await expect(map.getByRole("button", { name: new RegExp(`^${escapeRe(l)}, `, "i") })).toBeVisible();
    }
    expect(await overlappingGraphLabels(page), "label overlap with the Investigation layer on").toEqual([]);
    await snap(page, "09-graph-investigation-1440x900", { fullPage: false });
    await page.getByRole("button", { name: "Investigation", exact: true }).click();
  }

  // A node's inspector shows its sources and opens the evidence drawer.
  const first = Array.from(labels)[0]!;
  await map.getByRole("button", { name: new RegExp(`^${escapeRe(first)}, `, "i") }).click();
  const details = page.getByRole("complementary", { name: "Details" });
  await expect(details).toContainText(new RegExp(escapeRe(first), "i"));
  await expect(details).toContainText("never a diagnosis");
  const withSources = map.getByRole("button", { name: /, [1-9]\d* sources?, / }).first();
  await withSources.click();
  await details.getByRole("button", { name: /Open evidence/ }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await snap(page, "09-graph-evidence", { fullPage: false });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await page.getByRole("tab", { name: "List" }).click();
  for (const t of threads) {
    await expect(page.getByRole("region", { name: t.title, exact: true })).toBeVisible();
  }
  await expectCleanPage(page);
  await page.getByRole("tab", { name: "Map" }).click();
  await snap(page, "09-graph");
});

test("Graph design preview is labelled as sample data", async ({ page }) => {
  await page.goto("/graph?preview=design");
  await expect(page.getByText("Design preview with sample data — not your records.").first()).toBeVisible();
  await snap(page, "09-graph-design-preview", { fullPage: false });
});

test("Memory groups the memories kept around each thread by type", async ({ page, request }) => {
  const threads = await apiGet<ThreadV1[]>(request, "/v1/threads");
  await page.goto("/memory");
  await expect(page.getByRole("heading", { name: "Memory", exact: true })).toBeVisible();
  await expect(page.getByRole("group", { name: "Show memory type" })).toBeVisible();
  for (const t of threads) {
    const memories = await apiGet<{ title: string }[]>(request, `/v2/threads/${t.thread_id}/memories`);
    for (const m of memories) await expect(page.getByText(m.title, { exact: true }).first()).toBeVisible();
    if (memories.length > 0) {
      await expect(page.locator(`a[href="/threads/${t.thread_id}"]`).first()).toBeVisible();
    }
  }
  await expectCleanPage(page);
  await snap(page, "11-memory");
});

test("Appointments shows the open follow-up items", async ({ page, request }) => {
  const items = openPendingItems(await apiGet<PendingItemV2[]>(request, "/v2/pending-items"));
  await page.goto("/appointments");
  await expect(page.getByRole("heading", { name: "Appointments", exact: true })).toBeVisible();
  for (const i of items) await expect(page.getByText(i.title).first()).toBeVisible();
  await expectCleanPage(page);
  await snap(page, "10-appointments");
});

const RECORD_PAGES: { path: string; heading: string; marker: RegExp; shot: string }[] = [
  { path: "/results", heading: "Results", marker: /Add a result/, shot: "12-results" },
  { path: "/documents", heading: "Documents", marker: /Add a document/, shot: "13-documents" },
  { path: "/triage", heading: "A calm check-in", marker: /Question 1 of \d+/, shot: "14-triage" },
];

for (const r of RECORD_PAGES) {
  test(`${r.path} renders its view`, async ({ page }) => {
    await page.goto(r.path);
    await expect(page.getByRole("heading", { name: r.heading, exact: true })).toBeVisible();
    await expect(page.getByText(r.marker).first()).toBeVisible();
    await expect(page.getByText("In progress")).toHaveCount(0);
    await expectCleanPage(page);
    await snap(page, r.shot);
  });
}

test.describe("signed out", () => {
  test.use({ devSession: false });

  test("front door signs in through the WellBe login screen", async ({ page }) => {
    test.skip(!OIDC, "dev-headers deployment: covered by the Dev workspace test");
    await signInThroughLoginScreen(page, "definitely-not-the-password-1A!");
    await expect(page.getByText("That login name and password don't match")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
    await snap(page, "00-login-wrong-password", { fullPage: false });
    await signInThroughLoginScreen(page);
    await expectSignedIn(page);
    await expectCleanPage(page);

    await page.getByRole("button", { name: /^Your account:/ }).first().click();
    await page.getByRole("button", { name: "Sign out" }).click();
    await page.waitForURL((u) => u.pathname === "/", { timeout: 30_000 });
    await expect(page.getByRole("button", { name: /Sign in/ })).toBeVisible();
  });

  test("front door offers the Dev workspace and signs in to the launcher", async ({ page }) => {
    test.skip(OIDC, "OIDC deployment: no dev identities");
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Your private health workspace/ })).toBeVisible();
    await snap(page, "00-entry");
    await page.getByRole("button", { name: /Dev workspace/ }).click();
    await expect(page.getByRole("heading", { name: /What do you need/ })).toBeVisible();
    await expectCleanPage(page);
  });

  test("onboarding renders its first step", async ({ page }) => {
    test.skip(OIDC, "needs a fresh identity; scripts/qa/journey.py onboards one");
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
