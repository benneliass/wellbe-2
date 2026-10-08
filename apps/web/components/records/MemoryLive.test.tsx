import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createWellBeClient } from "@wellbe/api-client";
import { TEST_PATIENT, json, mockFetch, renderWithQuery, signIn } from "@/lib/records-test-utils";
import { MemoryLive } from "./MemoryLive";

vi.mock("@/lib/api", () => ({
  getApiClient: () => createWellBeClient({ baseUrl: "http://api.test" }),
}));

const HEADACHE = "8c26f338-35d7-4db6-ac75-48de1f1e74b1";
const COUGH = "48d96d5d-bbb1-4e49-961b-77222e3e9974";
const LDL = "c2b8ed07-e837-44a4-8ebd-dd1fc5f0879b";

function thread(thread_id: string, title: string, status = "active_unresolved") {
  return {
    schema_version: "c13.health_thread.v1",
    thread_id,
    patient_id: TEST_PATIENT,
    title,
    status,
    status_version: 2,
    created_at: "2026-09-27T10:12:36.791002Z",
    updated_at: "2026-09-27T10:12:36.805894Z",
  };
}

/** Shape of a live /v2/threads/{id}/memories row (no authorship_mode today). */
function memory(over: Record<string, unknown>) {
  return {
    schema_version: "c13.memory_entry.v2",
    memory_entry_id: "2fa6450b-cead-4c99-8bd6-4b0781579e81",
    memory_type: "clinical",
    lifecycle_state: "visible",
    title: "cough",
    thread_id: COUGH,
    source_refs: [
      { source_ref_id: "a0865ca4-fde9-5d06-a7c7-2a7a63921ca8", source_ref_type: "c4_extracted_fact", link_role: "primary" },
      { source_ref_id: "11ff1252-58ee-42d6-9a86-6ea850a3bf4e", source_ref_type: "c6_kg_node", link_role: "primary" },
    ],
    resolved_overlays: [],
    projection_stale: false,
    created_at: "2026-09-27T11:17:19.111475Z",
    audit_refs: [],
    ...over,
  };
}

const COUGH_CLINICAL = memory({});
const HEADACHE_CLINICAL = memory({
  memory_entry_id: "m-headache-clinical",
  title: "headache",
  thread_id: HEADACHE,
});
const HEADACHE_STORY = memory({
  memory_entry_id: "m-headache-story",
  memory_type: "story",
  authorship_mode: "controller_authored",
  title: "It starts behind my left eye after long screen days",
  thread_id: HEADACHE,
  source_refs: [{ source_ref_id: "cap-1", source_ref_type: "c3_capture" }],
});
const HEADACHE_STORY_NO_AUTHORSHIP = memory({
  memory_entry_id: "m-headache-story-2",
  memory_type: "story",
  title: "Worse in the afternoon",
  thread_id: HEADACHE,
  created_at: "2026-09-26T09:00:00Z",
});

function routes(memories: Record<string, unknown[] | number>) {
  const r: Record<string, () => Response> = {
    "GET /v1/threads": () =>
      json([thread(HEADACHE, "Headache"), thread(COUGH, "Cough", "waiting_for_result"), thread(LDL, "LDL cholesterol")]),
  };
  for (const [id, body] of Object.entries(memories)) {
    r[`GET /v2/threads/${id}/memories`] = () =>
      typeof body === "number" ? json({ detail: "unavailable" }, body) : json(body);
  }
  return r;
}

beforeEach(() => signIn());
afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
});

function section(name: string) {
  return screen.getByRole("region", { name });
}

describe("MemoryLive (Memory hub)", () => {
  it("groups real memories by type and shows derived ones as WellBe summaries", async () => {
    mockFetch(routes({ [HEADACHE]: [HEADACHE_CLINICAL], [COUGH]: [COUGH_CLINICAL], [LDL]: [] }));
    renderWithQuery(<MemoryLive />);

    const clinical = await screen.findByRole("region", { name: "Clinical" });
    expect(within(clinical).getByText("headache")).toBeInTheDocument();
    expect(within(clinical).getByText("cough")).toBeInTheDocument();

    const derivedLane = within(clinical).getByRole("region", { name: "WellBe summaries" });
    expect(within(derivedLane).getAllByText("WellBe summary")).toHaveLength(2);
    expect(within(derivedLane).getAllByText("Not clinician-reviewed")).toHaveLength(2);
    expect(within(clinical).getByText(/Nothing in your own words yet/)).toBeInTheDocument();

    expect(within(clinical).getByRole("link", { name: "Headache" })).toHaveAttribute("href", `/threads/${HEADACHE}`);
    expect(within(clinical).getByRole("link", { name: "Cough" })).toHaveAttribute("href", `/threads/${COUGH}`);

    // Only types that hold memories get a section; the rest are named quietly.
    expect(screen.queryByRole("region", { name: "Your story" })).not.toBeInTheDocument();
    expect(screen.getByText(/Not kept yet: Your story · Patterns · Decisions/)).toBeInTheDocument();
  });

  it("keeps authored words in the Voice lane and never infers authorship from type", async () => {
    mockFetch(
      routes({ [HEADACHE]: [HEADACHE_STORY, HEADACHE_STORY_NO_AUTHORSHIP], [COUGH]: [], [LDL]: [] }),
    );
    renderWithQuery(<MemoryLive />);

    const story = await screen.findByRole("region", { name: "Your story" });
    const voice = within(story).getByRole("region", { name: "Your voice" });
    const quote = within(voice).getByText("It starts behind my left eye after long screen days");
    expect(quote.closest("blockquote")).not.toBeNull();
    expect(within(voice).getByText("Your words")).toBeInTheDocument();

    const derived = within(story).getByRole("region", { name: "WellBe summaries" });
    expect(within(derived).getByText("Worse in the afternoon")).toBeInTheDocument();
    expect(within(voice).queryByText("Worse in the afternoon")).not.toBeInTheDocument();
  });

  it("filters by memory type with calm per-type empty states", async () => {
    mockFetch(routes({ [HEADACHE]: [HEADACHE_CLINICAL, HEADACHE_STORY], [COUGH]: [COUGH_CLINICAL], [LDL]: [] }));
    renderWithQuery(<MemoryLive />);

    const filters = await screen.findByRole("group", { name: "Show memory type" });
    const all = within(filters).getByRole("button", { name: "All, 3 memories" });
    expect(all).toHaveAttribute("aria-pressed", "true");
    expect(within(filters).getAllByRole("button")).toHaveLength(7);

    fireEvent.click(within(filters).getByRole("button", { name: "Your story, 1 memory" }));
    expect(section("Your story")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Clinical" })).not.toBeInTheDocument();

    fireEvent.click(within(filters).getByRole("button", { name: "Patterns, 0 memories" }));
    const patterns = section("Patterns");
    expect(within(patterns).getByText(/keeps what it noticed here for you to review/)).toBeInTheDocument();
    expect(within(patterns).queryByRole("region", { name: "Your voice" })).not.toBeInTheDocument();

    fireEvent.click(within(filters).getByRole("button", { name: "Access & context, 0 memories" }));
    expect(within(section("Access & context")).getByText(/only if you choose to add it/)).toBeInTheDocument();
  });

  it("marks lifecycle and corrections without hiding the entry", async () => {
    mockFetch(
      routes({
        [HEADACHE]: [
          memory({ memory_entry_id: "m-old", title: "Mild, weekly", thread_id: HEADACHE, lifecycle_state: "superseded_by_correction" }),
          memory({ memory_entry_id: "m-stale", title: "Most days", thread_id: HEADACHE, projection_stale: true }),
        ],
        [COUGH]: [],
        [LDL]: [],
      }),
    );
    renderWithQuery(<MemoryLive />);

    const clinical = await screen.findByRole("region", { name: "Clinical" });
    const old = within(clinical).getByText("Mild, weekly").closest("article")!;
    expect(old).toHaveAttribute("data-lifecycle", "superseded_by_correction");
    expect(within(clinical).getByText("Updating")).toBeInTheDocument();
  });

  it("opens the evidence drawer with plain source labels and the thread", async () => {
    mockFetch(routes({ [HEADACHE]: [], [COUGH]: [COUGH_CLINICAL], [LDL]: [] }));
    renderWithQuery(<MemoryLive />);

    const clinical = await screen.findByRole("region", { name: "Clinical" });
    fireEvent.click(within(clinical).getByRole("button", { name: /Open evidence/ }));

    const drawer = await screen.findByRole("dialog", { name: "Sources" });
    expect(within(drawer).getByText("Fact from what you added")).toBeInTheDocument();
    expect(within(drawer).getByText("Linked concept")).toBeInTheDocument();
    expect(within(drawer).getByRole("link", { name: "Cough" })).toHaveAttribute("href", `/threads/${COUGH}`);
    expect(drawer.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-/);
  });

  it("says calmly which threads' memories are unavailable", async () => {
    mockFetch(routes({ [HEADACHE]: [HEADACHE_CLINICAL], [COUGH]: 500, [LDL]: [] }));
    renderWithQuery(<MemoryLive />);

    expect(await screen.findByText(/Memories for Cough aren.t available right now/)).toBeInTheDocument();
    expect(section("Clinical")).toBeInTheDocument();
  });

  it("shows a calm empty state when nothing is kept yet", async () => {
    mockFetch(routes({ [HEADACHE]: [], [COUGH]: [], [LDL]: [] }));
    renderWithQuery(<MemoryLive />);

    expect(await screen.findByRole("heading", { name: "Nothing kept yet" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("group")).not.toBeInTheDocument());
  });
});
