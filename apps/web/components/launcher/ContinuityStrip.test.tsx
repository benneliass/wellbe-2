import { screen } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { clearSession } from "@/lib/session";
import { ContinuityStrip } from "./ContinuityStrip";

function thread(id: string, status: string) {
  return {
    schema_version: "c13.health_thread.v1",
    thread_id: id,
    patient_id: "p",
    title: `Thread ${id}`,
    status,
    status_version: 1,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-20T00:00:00Z",
  };
}

// The API client is a singleton bound to the first fetch stub, so every test
// swaps handlers in this one shared route table instead of re-stubbing fetch.
const routes: Parameters<typeof mockFetch>[0] = {};
let fetchMock: ReturnType<typeof mockFetch>;

function useRoutes(next: Parameters<typeof mockFetch>[0]) {
  for (const key of Object.keys(routes)) delete routes[key];
  Object.assign(routes, next);
}

describe("ContinuityStrip", () => {
  beforeAll(() => {
    fetchMock = mockFetch(routes);
  });
  afterAll(() => vi.unstubAllGlobals());
  beforeEach(() => signIn());
  afterEach(() => {
    clearSession();
    fetchMock.mockClear();
  });

  it("summarises what is carried forward and links to Full View", async () => {
    useRoutes({
      "GET /v1/threads": () =>
        json([thread("1", "active_unresolved"), thread("2", "waiting_for_result"), thread("3", "closed")]),
      "GET /v2/pending-items": () =>
        json([
          {
            schema_version: "c13.pending_item.v2",
            pending_item_id: "p1",
            primary_thread_id: "1",
            item_type: "repeat_test_due",
            status: "due",
            title: "Repeat ferritin test",
            due_at: "2026-09-30T00:00:00Z",
            due_precision: "date",
            blocks_closure: false,
            created_at: "2026-09-01T00:00:00Z",
            updated_at: "2026-09-01T00:00:00Z",
          },
        ]),
      "GET /v1/things-noticed": () =>
        json([
          {
            schema_version: "c13.thing_noticed.v1",
            candidate_id: "c1",
            title: "Morning dizziness",
            candidate_type: "symptom",
            status: "pending",
            seen_count: 2,
            first_seen_at: "2026-09-18T00:00:00Z",
            last_seen_at: "2026-09-26T00:00:00Z",
            source_capture_count: 2,
            source_fact_count: 0,
          },
        ]),
    });
    renderWithQuery(<ContinuityStrip />);
    const link = await screen.findByRole("link", { name: /carrying forward/i });
    expect(link).toHaveAttribute("href", "/workspace");
    expect(link).toHaveTextContent("2 threads carrying forward · 1 open loop · 1 thing noticed");
    expect(link).toHaveTextContent("Full View");
  });

  it("reserves its space and shows nothing when threads can't load", async () => {
    useRoutes({ "GET /v1/threads": () => json({ detail: "down" }, 500) });
    const { container } = renderWithQuery(<ContinuityStrip />);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByRole("link")).toBeNull();
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
  });
});
