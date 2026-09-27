import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThreadDetailLive } from "./ThreadDetailLive";

const get = vi.fn();
const post = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ GET: get, POST: post }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/threads/thread-1",
}));

const THREAD = "thread-1";
const PATIENT = "patient-1";
const FACT = "fact-1";
const CAPTURE = "capture-1";

type Overrides = Partial<Record<string, unknown>>;

const MEMORIES = [
  {
    memory_entry_id: "m1",
    memory_type: "clinical",
    lifecycle_state: "visible",
    title: "cough",
    thread_id: THREAD,
    authorship_mode: "system_derived",
    source_refs: [{ source_ref_type: "c4_extracted_fact", source_ref_id: FACT }],
    created_at: "2026-09-14T08:00:00Z",
  },
];

const TIMELINE = {
  schema_version: "c13.thread_timeline.v2",
  thread_id: THREAD,
  status: "waiting_for_result",
  status_history: ["draft", "active_unresolved", "waiting_for_result"],
  events: [
    {
      event_id: `thread:${THREAD}`,
      kind: "thread_started",
      occurred_at: "2026-09-01T10:00:00Z",
      title: "You started this thread",
      source_ref_ids: [],
    },
    {
      event_id: "transition:t1",
      kind: "status_changed",
      occurred_at: "2026-09-02T10:00:00Z",
      title: "Status changed",
      from_status: "draft",
      to_status: "active_unresolved",
      actor: "wellbe",
      source_ref_ids: [],
    },
    {
      event_id: `capture:${CAPTURE}`,
      kind: "capture",
      occurred_at: "2026-09-14T08:00:00Z",
      title: "You described how you feel",
      detail: "Picked out: cough",
      actor: "you",
      source_ref_ids: [CAPTURE],
    },
  ],
  sources: [
    {
      source_ref_id: FACT,
      source_ref_type: "c4_extracted_fact",
      component: "c5",
      kind: "extracted_fact",
      display_label: "Morning cough",
      date: "2026-09-14T08:00:00Z",
      confidence: 0.82,
      confidence_basis: "How clearly WellBe picked this out of what you added",
      review_marker: "patient-entered",
    },
    {
      source_ref_id: CAPTURE,
      source_ref_type: "c2_capture",
      component: "c2",
      kind: "entered_by_you",
      display_label: "Entered by you",
      date: "2026-09-14T08:00:00Z",
      review_marker: "patient-entered",
    },
  ],
};

function responses(path: string, o: Overrides) {
  if (path in o) return o[path];
  switch (path) {
    case "/v1/threads/{thread_id}":
      return {
        thread_id: THREAD,
        patient_id: PATIENT,
        title: "Cough",
        status: "waiting_for_result",
        status_version: 3,
        created_at: "2026-09-01T10:00:00Z",
        updated_at: "2026-09-10T10:00:00Z",
      };
    case "/v2/threads/{thread_id}/memories":
      return MEMORIES;
    case "/v2/threads/{thread_id}/timeline":
      return TIMELINE;
    case "/v2/graph/threads/{thread_id}":
      return {
        thread_id: THREAD,
        nodes: [
          { id: "n1", type: "Symptom", label: "Cough", status: "active", attributes: { in_thread: true } },
          { id: "n2", type: "Symptom", label: "Poor sleep", status: "active", attributes: { in_thread: false } },
        ],
        edges: [{ id: "e1", source: "n1", target: "n2", relation: "co_occurs_with", evidence_weight: 0.6 }],
      };
    case "/v2/pending-items":
      return [
        {
          pending_item_id: "p1",
          primary_thread_id: THREAD,
          item_type: "result_pending",
          status: "scheduled",
          title: "Waiting for a result: Cough",
          due_at: "2026-10-04T11:00:00Z",
        },
      ];
    case "/v2/investigations":
      return [];
    default:
      throw new Error(`unexpected GET ${path}`);
  }
}

function setup(overrides: Overrides = {}) {
  get.mockImplementation(async (path: string) => ({ data: responses(path, overrides), error: null }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrap = (ui: ReactNode) => <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
  return render(wrap(<ThreadDetailLive id={THREAD} />));
}

describe("ThreadDetailLive", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
  });

  it("shows the journey rail from real status history with what we're waiting on", async () => {
    setup();
    const rail = await screen.findByRole("navigation", { name: "Thread journey" });
    await waitFor(() => expect(within(rail).getByText("Started")).toBeInTheDocument());
    expect(within(rail).getByText("Open")).toBeInTheDocument();
    const current = rail.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("In motion");
    expect(current).toHaveTextContent("Waiting for a result");
    expect(within(rail).getByText(/You described how you feel · Sep 14/)).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: /See what's pending/ })).toHaveAttribute("href", "#open-loops");
  });

  it("puts derived memories in the WellBe summaries lane with honest review markers", async () => {
    setup();
    const lane = (await screen.findByRole("heading", { name: "WellBe summaries" })).closest("section")!;
    expect(within(lane).getByText("Cough")).toBeInTheDocument();
    expect(within(lane).getByText("WellBe summary")).toBeInTheDocument();
    expect(within(lane).getByText("Not clinician-reviewed")).toBeInTheDocument();
    expect(within(lane).queryByText("Your words")).not.toBeInTheDocument();
  });

  it("keeps the user's own words verbatim in the Voice lane", async () => {
    setup({
      "/v2/threads/{thread_id}/memories": [
        { ...MEMORIES[0], memory_entry_id: "m2", memory_type: "story", title: "coughing most mornings", authorship_mode: "controller_authored" },
      ],
    });
    const lane = (await screen.findByRole("heading", { name: "Your voice" })).closest("section")!;
    expect(within(lane).getByText("coughing most mornings")).toBeInTheDocument();
    expect(within(lane).getByText("Your words")).toBeInTheDocument();
  });

  it("never shows an entry without stored authorship as the user's words", async () => {
    setup({
      "/v2/threads/{thread_id}/memories": [{ ...MEMORIES[0], authorship_mode: null }],
    });
    const lane = (await screen.findByRole("heading", { name: "WellBe summaries" })).closest("section")!;
    expect(within(lane).getByText("Not clinician-reviewed")).toBeInTheDocument();
    expect(within(lane).queryByText("WellBe summary")).not.toBeInTheDocument();
    expect(within(lane).queryByText("Your words")).not.toBeInTheDocument();
  });

  it("opens the evidence drawer from a memory's source marker", async () => {
    setup();
    const lane = (await screen.findByRole("heading", { name: "WellBe summaries" })).closest("section")!;
    fireEvent.click(await within(lane).findByRole("button", { name: /Morning cough.*Open evidence/ }));
    const drawer = await screen.findByRole("dialog", { name: "Where this came from" });
    expect(within(drawer).getByText("Morning cough")).toBeInTheDocument();
    expect(within(drawer).getByText("Well supported")).toBeInTheDocument();
    expect(within(drawer).getByText("Your words")).toBeInTheDocument();
  });

  it("asks one gentle question when nothing is in the user's own words, attached to this thread", async () => {
    post.mockResolvedValue({ data: { capture_id: "c-new", processing: "pending" }, error: null });
    setup();
    const strip = await screen.findByRole("region", { name: "One question for you" });
    expect(within(strip).getByText("In your own words, how has your cough been?")).toBeInTheDocument();
    fireEvent.click(within(strip).getByRole("button", { name: "Answer in your words" }));
    fireEvent.change(await screen.findByLabelText("In your own words"), {
      target: { value: "Worse at night." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save in my words" }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    const [path, init] = post.mock.calls[0]!;
    expect(path).toBe("/v1/capture");
    expect(init.body).toMatchObject({ capture_type: "note", payload: { text: "Worse at night." }, thread_id: THREAD });
  });

  it("hides the clarify strip when there is nothing real to ask", async () => {
    setup({
      "/v2/threads/{thread_id}/memories": [{ ...MEMORIES[0], authorship_mode: "controller_confirmed" }],
    });
    await screen.findByRole("heading", { name: "Your voice" });
    expect(screen.queryByRole("region", { name: "One question for you" })).not.toBeInTheDocument();
  });

  it("asks about an investigation's missing context first", async () => {
    setup({
      "/v2/investigations": [
        {
          investigation_id: "inv-1",
          health_thread_ids: [THREAD],
          primary_question: "Could the cough and fatigue be connected?",
          missing_context_items: ["When did the cough start?"],
        },
      ],
      "/v2/investigations/{investigation_id}/theories": [],
    });
    const strip = await screen.findByRole("region", { name: "One question for you" });
    expect(within(strip).getByText("When did the cough start?")).toBeInTheDocument();
  });

  it("keeps the timeline and connections collapsed until asked", async () => {
    setup();
    await screen.findByRole("navigation", { name: "Thread journey" });
    expect(screen.queryByRole("list", { name: "Thread timeline" })).not.toBeInTheDocument();
    expect(screen.queryByText("Poor sleep")).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "Show timeline" }));
    const tl = await screen.findByRole("list", { name: "Thread timeline" });
    expect(within(tl).getByText("Now: open and unresolved")).toBeInTheDocument();
    expect(within(tl).getByText("Picked out: cough")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Explore connections" }));
    expect((await screen.findAllByText("Poor sleep")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/elsewhere in your records/)).toHaveLength(1);
    expect(screen.getByText("Moderate")).toBeInTheDocument();
  });

  it("opens the timeline when a traveled rail stage is tapped", async () => {
    setup();
    const rail = await screen.findByRole("navigation", { name: "Thread journey" });
    const open = await within(rail).findByRole("button", { name: /Open, visited/ });
    fireEvent.click(open);
    expect(await screen.findByRole("list", { name: "Thread timeline" })).toBeInTheDocument();
  });

  it("shows theory support in words with review and source markers", async () => {
    setup({
      "/v2/investigations": [
        { investigation_id: "inv-1", health_thread_ids: [THREAD], primary_question: "Why the cough?", missing_context_items: [] },
      ],
      "/v2/investigations/{investigation_id}/theories": [
        {
          theory_id: "th-1",
          investigation_id: "inv-1",
          label: "The cough may relate to poor sleep",
          status: "unreviewed",
          proposed_by: { actor_id: PATIENT },
          evidence_for: [],
          latest_evaluation: null,
        },
      ],
    });
    const item = (await screen.findByText("The cough may relate to poor sleep")).closest("li")!;
    expect(within(item).getByText("Not weighed against your data yet")).toBeInTheDocument();
    expect(within(item).getByText("Your words")).toBeInTheDocument();
    fireEvent.click(within(item).getByRole("button", { name: /No sources cited yet/ }));
    const drawer = await screen.findByRole("dialog", { name: "Evidence for this theory" });
    expect(within(drawer).getByText("No sources are attached to this yet.")).toBeInTheDocument();
  });
});
