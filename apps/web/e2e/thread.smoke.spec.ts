import { expect, test, type Page } from "@playwright/test";
import { injectSession } from "./_session";

/**
 * Thread Detail smoke: the live page for a real thread id, with the API stubbed
 * from payloads shaped like the dev workspace's "Cough" thread. Guards the
 * progressive-disclosure contract: L0–L2 (rail, next action, clarify, story)
 * visible without scrolling on a 390px phone, timeline/connections collapsed.
 */

const THREAD = "48d96d5d-bbb1-4e49-961b-77222e3e9974";
const PATIENT = "de7a0000-0000-4000-8000-000000000001";
const FACT = "feeacba0-43e8-558c-b2bf-3b2ef9f24d2e";
const CAPTURE = "6a1c0000-0000-4000-8000-00000000c0de";
const NODE = "11ff1252-58ee-42d6-9a86-6ea850a3bf4e";

const API: Record<string, unknown> = {
  [`/v1/threads/${THREAD}`]: {
    schema_version: "c13.health_thread.v1",
    thread_id: THREAD,
    patient_id: PATIENT,
    title: "Cough",
    status: "waiting_for_result",
    status_version: 3,
    created_at: "2026-09-27T10:12:36.562408Z",
    updated_at: "2026-09-27T10:12:36.653907Z",
  },
  [`/v2/threads/${THREAD}/memories`]: [
    {
      schema_version: "c13.memory_entry.v2",
      memory_entry_id: "cc7fc41d-408e-410d-9a37-73ccd4ecf892",
      memory_type: "clinical",
      lifecycle_state: "visible",
      title: "cough",
      thread_id: THREAD,
      authorship_mode: "system_derived",
      source_refs: [
        { source_ref_id: FACT, source_ref_type: "c4_extracted_fact", link_role: "primary" },
        { source_ref_id: NODE, source_ref_type: "c6_kg_node", link_role: "primary" },
      ],
      resolved_overlays: [],
      projection_stale: false,
      created_at: "2026-09-27T11:17:19.111475Z",
    },
  ],
  [`/v2/threads/${THREAD}/timeline`]: {
    schema_version: "c13.thread_timeline.v2",
    thread_id: THREAD,
    status: "waiting_for_result",
    status_history: ["draft", "active_unresolved", "waiting_for_result"],
    events: [
      { event_id: `thread:${THREAD}`, kind: "thread_started", occurred_at: "2026-09-27T10:12:36Z", title: "WellBe started this thread from what you added", actor: "wellbe", source_ref_ids: [] },
      { event_id: "transition:1", kind: "status_changed", occurred_at: "2026-09-27T10:12:36.6Z", title: "Status changed", from_status: "draft", to_status: "active_unresolved", actor: "wellbe", source_ref_ids: [] },
      { event_id: "transition:2", kind: "status_changed", occurred_at: "2026-09-27T10:12:36.65Z", title: "Status changed", from_status: "active_unresolved", to_status: "waiting_for_result", actor: "you", source_ref_ids: [] },
      { event_id: `capture:${CAPTURE}`, kind: "capture", occurred_at: "2026-09-27T11:17:00Z", title: "You described how you feel", detail: "Picked out: cough, fatigue", actor: "you", source_ref_ids: [CAPTURE] },
      { event_id: "pending:p1", kind: "open_loop", occurred_at: "2026-09-27T11:17:19Z", title: "Waiting for a result: Cough", item_type: "result_pending", item_status: "scheduled", due_at: "2026-10-04T11:17:19Z", source_ref_ids: [] },
    ],
    sources: [
      { source_ref_id: CAPTURE, source_ref_type: "c2_capture", component: "c2", kind: "entered_by_you", display_label: "Entered by you", date: "2026-09-27T11:17:00Z", review_marker: "patient-entered", capture_id: CAPTURE },
      { source_ref_id: FACT, source_ref_type: "c4_extracted_fact", component: "c5", kind: "extracted_fact", display_label: "cough", date: "2026-09-27T11:17:00Z", confidence: 0.86, confidence_basis: "How clearly WellBe picked this out of what you added", review_marker: "patient-entered", capture_id: CAPTURE },
      { source_ref_id: NODE, source_ref_type: "c6_kg_node", component: "c5", kind: "linked_concept", display_label: "cough", date: "2026-09-27T10:12:26Z", review_marker: "AI-summarized" },
    ],
  },
  [`/v2/graph/threads/${THREAD}`]: {
    schema_version: "c13.graph.subgraph.v2",
    thread_id: THREAD,
    nodes: [
      { id: NODE, type: "Symptom", label: "cough", status: "active", attributes: { first_seen_at: "2026-09-27T10:12:26Z", in_thread: true } },
      { id: "79675d10-78e3-415f-b563-d12fa721c599", type: "Symptom", label: "fatigue", status: "active", attributes: { first_seen_at: "2026-09-27T10:12:30Z", in_thread: false } },
    ],
    edges: [{ id: "e1", source: NODE, target: "79675d10-78e3-415f-b563-d12fa721c599", relation: "co_occurs_with", evidence_weight: 0.6, attributes: {} }],
  },
  "/v2/pending-items": [
    { schema_version: "c13.pending_item.v2", pending_item_id: "p1", primary_thread_id: THREAD, item_type: "result_pending", status: "scheduled", title: "Waiting for a result: Cough", due_at: "2026-10-04T11:17:19Z", due_precision: "relative_policy", investigation_ids: [], blocks_closure: false },
  ],
  "/v2/investigations": [
    { investigation_id: "3aa892c2-ace6-4b69-ad90-1fa707552a60", health_thread_ids: [THREAD], primary_question: "Could the morning cough, afternoon fatigue, and low vitamin D be connected?", status: "open", missing_context_items: [] },
  ],
  "/v2/investigations/3aa892c2-ace6-4b69-ad90-1fa707552a60/theories": [
    { theory_id: "cf8183a9-e039-41be-8609-d254e98548df", investigation_id: "3aa892c2-ace6-4b69-ad90-1fa707552a60", health_thread_id: "", label: "The ongoing fatigue may relate to the low vitamin D result.", proposed_by: { actor_id: PATIENT }, status: "unreviewed", evidence_for: [], evidence_against: [], missing_data: [], not_diagnosis: true, created_at: "2026-09-27T10:12:36Z", updated_at: "2026-09-27T10:12:36Z", version: 1, latest_evaluation: null },
  ],
};

async function stubApi(page: Page) {
  // Match by path, not host: the kind build bakes an empty NEXT_PUBLIC_WELLBE_API_URL,
  // so the client calls the API same-origin rather than on api.localhost.
  await page.route((url) => /^\/v[12]\//.test(url.pathname), async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path in API ? API[path] : [];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
}

test.use({ viewport: { width: 390, height: 844 } });

test.beforeEach(async ({ page }) => {
  await injectSession(page);
  await stubApi(page);
});

test("L0–L2 are visible without scrolling on a 390px phone", async ({ page }) => {
  await page.goto(`/threads/${THREAD}`);
  const rail = page.getByRole("navigation", { name: "Thread journey" });
  await expect(rail).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your story" })).toBeVisible();
  await page.screenshot({ path: "test-results/thread-mobile-fold.png" });
  await expect(rail.getByText("Waiting for a result", { exact: true })).toBeInViewport();
  await expect(page.getByRole("link", { name: /See what's pending/ })).toBeInViewport();
  await expect(page.getByRole("region", { name: "One question for you" })).toBeInViewport();
  await expect(page.getByRole("heading", { name: "Your story" })).toBeInViewport();
  await expect(page.getByRole("list", { name: "Thread timeline" })).toHaveCount(0);
});

test("a source marker opens the evidence drawer", async ({ page }) => {
  await page.goto(`/threads/${THREAD}`);
  await page.getByRole("button", { name: /cough.*Open evidence/ }).first().click();
  const drawer = page.getByRole("dialog", { name: "Sources" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText("Well supported")).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: "test-results/thread-mobile-drawer.png" });
});

test("the timeline opens on request, in order", async ({ page }) => {
  await page.goto(`/threads/${THREAD}`);
  await page.getByRole("button", { name: "Show timeline" }).click();
  const tl = page.getByRole("list", { name: "Thread timeline" });
  const events = tl.locator(":scope > li");
  await expect(events).toHaveCount(5);
  await expect(events.nth(2)).toContainText("Now: waiting for a result");
  await tl.scrollIntoViewIfNeeded();
  await page.screenshot({ path: "test-results/thread-mobile-timeline.png", fullPage: true });
});
