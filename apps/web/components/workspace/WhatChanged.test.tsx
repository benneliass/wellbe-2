import { screen } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { LAST_VISIT_KEY } from "@/lib/home-continuity";
import { clearSession } from "@/lib/session";
import { WhatChanged } from "./WhatChanged";

const SINCE = "2026-09-20T09:00:00.000Z";

const pending = [
  {
    schema_version: "c13.pending_item.v2" as const,
    pending_item_id: "p1",
    primary_thread_id: "t-ferritin",
    item_type: "repeat_test_due",
    status: "due",
    title: "Repeat ferritin test",
    due_at: "2099-01-01T00:00:00Z",
    due_precision: "date",
    blocks_closure: false,
    created_at: "2026-09-21T00:00:00Z",
    updated_at: "2026-09-21T00:00:00Z",
  },
];

// The API client is a singleton bound to the first fetch stub, so every test
// swaps handlers in this one shared route table instead of re-stubbing fetch.
const routes: Parameters<typeof mockFetch>[0] = {};
let fetchMock: ReturnType<typeof mockFetch>;

function useRoutes(next: Parameters<typeof mockFetch>[0]) {
  for (const key of Object.keys(routes)) delete routes[key];
  Object.assign(routes, next);
}

describe("WhatChanged", () => {
  beforeAll(() => {
    fetchMock = mockFetch(routes);
  });
  afterAll(() => vi.unstubAllGlobals());
  beforeEach(() => {
    signIn();
    // A visit long ago started the current one: the window opens at SINCE.
    window.localStorage.setItem(LAST_VISIT_KEY, JSON.stringify({ previous: null, current: SINCE }));
  });
  afterEach(() => {
    clearSession();
    window.localStorage.removeItem(LAST_VISIT_KEY);
    fetchMock.mockClear();
  });

  it("opens with a calm since-last-visit headline and links changes to their thread", async () => {
    useRoutes({
      "GET /v2/delta": () =>
        json({
          schema_version: "c13.delta.v2",
          window_since: SINCE,
          window_label: "since 2026-09-20",
          not_diagnosis: true,
          note: "",
          events: [
            {
              id: "pending:p1",
              category: "open_loop",
              title: "Repeat ferritin test",
              ranking_reason: "New open item",
              detail: null,
              occurred_at: "2026-09-21T00:00:00Z",
              source: { ref_type: "pending_item", source_id: "p1", label: "Repeat ferritin test" },
            },
          ],
        }),
      "GET /v2/results": () =>
        json({
          schema_version: "c13.results.v2",
          analytes: [
            {
              analyte: "Ferritin",
              latest: {
                value: "18",
                observed_at: "2026-09-22T00:00:00Z",
                range_note: "",
                source: { capture_id: "c", display_label: "Lab", kind: "lab", review_marker: "patient-entered" },
              },
            },
          ],
        }),
    });

    renderWithQuery(<WhatChanged pending={pending} />);
    expect(
      await screen.findByRole("heading", {
        name: "Since Sep 20: 1 new result, 1 open loop due soon, 1 new open loop",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("One thing needs a look. Everything else is steady.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /new open loop.*repeat ferritin test/i })).toHaveAttribute(
      "href",
      "/threads/t-ferritin",
    );
    expect(screen.getByRole("link", { name: /everything that changed/i })).toHaveAttribute("href", "/delta");

    const deltaUrl = fetchMock.mock.calls
      .map(([input]) => (input instanceof Request ? input.url : String(input)))
      .find((u) => u.includes("/v2/delta"));
    expect(new URL(deltaUrl ?? "http://x").searchParams.get("since")).toBe(SINCE);
  });

  it("keeps the status line when the digest can't load", async () => {
    useRoutes({ "GET /v2/delta": () => json({ detail: "down" }, 500) });
    renderWithQuery(<WhatChanged pending={[]} />);
    expect(await screen.findByRole("heading", { name: "Here's where things stand" })).toBeInTheDocument();
    expect(screen.getByText(/Nothing needs your attention right now/)).toBeInTheDocument();
  });
});
