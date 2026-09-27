import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { clearSession } from "@/lib/session";
import { ThingsNoticed } from "./ThingsNoticed";

const DIZZY = "11111111-1111-4111-8111-111111111111";
const COUGH = "22222222-2222-4222-8222-222222222222";

function candidate(id: string, title: string, over: Record<string, unknown> = {}) {
  return {
    schema_version: "c13.thing_noticed.v1",
    candidate_id: id,
    title,
    candidate_type: "symptom",
    status: "pending",
    seen_count: 3,
    confidence: 0.62,
    reason_code: "default_candidate_pending_classification",
    first_seen_at: "2026-09-18T09:00:00Z",
    last_seen_at: "2026-09-26T09:00:00Z",
    promoted_thread_id: null,
    source_capture_count: 3,
    source_fact_count: 2,
    snoozed_until: null,
    ignored_at: null,
    ...over,
  };
}

let list: ReturnType<typeof candidate>[];
const calls: { path: string; body: unknown }[] = [];

// The API client is a singleton bound to the first fetch stub, so every test
// swaps handlers in this one shared route table instead of re-stubbing fetch.
const routes: Parameters<typeof mockFetch>[0] = {};

function setup() {
  list = [candidate(DIZZY, "Morning dizziness"), candidate(COUGH, "Dry cough", { seen_count: 1 })];
  calls.length = 0;
  const record = (status: string) => async (req: Request) => {
    const path = new URL(req.url).pathname;
    const id = path.split("/")[3] ?? "";
    const text = await req.text();
    calls.push({ path, body: text ? JSON.parse(text) : null });
    list = list.filter((c) => c.candidate_id !== id);
    return json({ ...candidate(id, "x"), status });
  };
  for (const key of Object.keys(routes)) delete routes[key];
  Object.assign(routes, {
    "GET /v1/things-noticed": () => json(list),
    [`POST /v1/things-noticed/${DIZZY}/confirm`]: async (req: Request) => {
      calls.push({ path: new URL(req.url).pathname, body: null });
      list = list.filter((c) => c.candidate_id !== DIZZY);
      return json({ schema_version: "c13.thing_noticed_confirm.v1", candidate_id: DIZZY, thread_id: "t-new", status: "promoted" });
    },
    [`POST /v1/things-noticed/${DIZZY}/dismiss`]: record("dismissed"),
    [`POST /v1/things-noticed/${DIZZY}/ignore`]: record("pending"),
    [`POST /v1/things-noticed/${DIZZY}/snooze`]: record("pending"),
    [`POST /v1/things-noticed/${COUGH}/dismiss`]: () => json({ detail: "boom" }, 500),
  });
}

function card(title: RegExp) {
  return screen.getByRole("article", { name: title });
}

describe("ThingsNoticed", () => {
  beforeAll(() => {
    mockFetch(routes);
  });
  afterAll(() => vi.unstubAllGlobals());
  beforeEach(() => {
    signIn();
    setup();
  });
  afterEach(() => clearSession());

  it("renders each candidate as a 'may relate' card with sources, confidence and four actions", async () => {
    renderWithQuery(<ThingsNoticed />);
    const dizzy = await screen.findByRole("article", { name: /may relate to morning dizziness/i });
    expect(dizzy).toHaveTextContent("3 recent entries may relate to Morning dizziness");
    expect(dizzy).toHaveTextContent(/mentioned this 3 times since Sep 18/);
    expect(within(dizzy).getByText("3 entries you logged")).toBeInTheDocument();
    expect(within(dizzy).getByText("2 details picked out")).toBeInTheDocument();
    expect(within(dizzy).getByText(/moderate/i)).toBeInTheDocument();
    for (const name of ["Accept", "Reject", "Ignore for now", "Remind me later"]) {
      expect(within(dizzy).getByRole("button", { name })).toBeInTheDocument();
    }
    expect(card(/something you logged may relate to dry cough/i)).toBeInTheDocument();
  });

  it("remind later snoozes a week out and hides the card until then", async () => {
    renderWithQuery(<ThingsNoticed />);
    const dizzy = await screen.findByRole("article", { name: /morning dizziness/i });
    const before = Date.now();
    fireEvent.click(within(dizzy).getByRole("button", { name: "Remind me later" }));

    await waitFor(() => expect(screen.queryByRole("article", { name: /morning dizziness/i })).toBeNull());
    expect(await screen.findByRole("status")).toHaveTextContent(/We'll bring “Morning dizziness” back on/);
    const call = calls.find((c) => c.path.endsWith("/snooze"));
    const until = new Date((call?.body as { until: string }).until).getTime();
    expect(until - before).toBeGreaterThan(6 * 86_400_000);
    expect(until - before).toBeLessThan(8 * 86_400_000);
  });

  it("maps reject to dismiss and ignore to ignore", async () => {
    renderWithQuery(<ThingsNoticed />);
    const dizzy = await screen.findByRole("article", { name: /morning dizziness/i });
    fireEvent.click(within(dizzy).getByRole("button", { name: "Ignore for now" }));
    await waitFor(() => expect(calls.map((c) => c.path)).toContain(`/v1/things-noticed/${DIZZY}/ignore`));
    expect(await screen.findByRole("status")).toHaveTextContent(/comes back only if it's noticed again/);
  });

  it("accept opens a thread and links to it", async () => {
    renderWithQuery(<ThingsNoticed />);
    const dizzy = await screen.findByRole("article", { name: /morning dizziness/i });
    fireEvent.click(within(dizzy).getByRole("button", { name: "Accept" }));
    const link = await screen.findByRole("link", { name: "Open it" });
    expect(link).toHaveAttribute("href", "/threads/t-new");
  });

  it("puts the card back when an action fails", async () => {
    renderWithQuery(<ThingsNoticed />);
    const cough = await screen.findByRole("article", { name: /dry cough/i });
    fireEvent.click(within(cough).getByRole("button", { name: "Reject" }));
    expect(await screen.findByText(/didn't go through/)).toBeInTheDocument();
    expect(await screen.findByRole("article", { name: /dry cough/i })).toBeInTheDocument();
  });
});
