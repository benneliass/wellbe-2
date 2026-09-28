import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { toThreadSummary } from "@/lib/adapters";
import { GraphLive } from "./GraphLive";
import { DESIGN_PREVIEW_MODEL } from "./graphData";
import { buildLiveGraph } from "./liveGraphAdapter";
import fixture from "./liveGraph.fixture.json";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, back: vi.fn() }),
  usePathname: () => "/graph",
}));

const model = buildLiveGraph({
  threads: fixture.threads.map((t) => toThreadSummary(t as never)),
  graphs: fixture.graphs as never,
  memories: fixture.memories as never,
  pending: fixture.pending as never,
  patterns: fixture.patterns as never,
  results: fixture.results as never,
  investigations: fixture.investigations as never,
});

const FIXTURE_LABELS = ["MRI referral", "Late caffeine", "Light sensitivity", "Screen time"];

function map() {
  return screen.getByRole("group", { name: /Map of your concerns/ });
}

describe("GraphLive on the person's real data", () => {
  it("draws real concerns and concepts, never sample fixtures", () => {
    render(<GraphLive model={model} />);
    for (const t of fixture.threads) expect(within(map()).getAllByText(t.title).length).toBeGreaterThan(0);
    expect(within(map()).getByRole("button", { name: /^Cough, Symptom, 2 sources/ })).toBeInTheDocument();
    expect(within(map()).getByRole("button", { name: /^Waiting for a result: Cough, open loop, Check back/ })).toBeInTheDocument();
    for (const l of FIXTURE_LABELS) expect(screen.queryByText(l)).not.toBeInTheDocument();
    expect(screen.queryByText(/Design preview/)).not.toBeInTheDocument();
  });

  it("inspects a node with SourceMarkers that open the evidence drawer", async () => {
    render(<GraphLive model={model} />);
    await userEvent.click(within(map()).getByRole("button", { name: /^Hemoglobin A1c, Lab result/ }));
    const panel = screen.getByRole("complementary", { name: "Details" });
    expect(within(panel).getByText("Hemoglobin A1c", { selector: "p" })).toBeInTheDocument();
    expect(within(panel).getByText("Also in your records")).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: /Entered by you/ }));
    const dialog = screen.getByRole("dialog", { name: "Sources for Hemoglobin A1c" });
    expect(within(dialog).getByText(/Hemoglobin A1c: 5.4 %/)).toBeInTheDocument();
    expect(within(dialog).getByText("Your words")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("explains a link from the keyboard, with sources and the non-diagnostic caveat", async () => {
    render(<GraphLive model={model} />);
    const cough = within(map()).getByRole("button", { name: /^Cough, Symptom/ });
    cough.focus();
    await userEvent.keyboard("{Enter}");
    const panel = screen.getByRole("complementary", { name: "Details" });
    await userEvent.click(within(panel).getByRole("button", { name: "Why is Cough connected to Pain?" }));
    expect(within(panel).getByText("Why connected?")).toBeInTheDocument();
    expect(within(panel).getByText(/not a cause, and not a diagnosis/)).toBeInTheDocument();
    expect(within(panel).getByText("Two things appearing together can be coincidence.")).toBeInTheDocument();
    expect(within(panel).getAllByRole("button", { name: /Fact from what you added/ }).length).toBeGreaterThan(0);
  });

  it("moves focus between nodes with the arrow keys", async () => {
    render(<GraphLive model={model} />);
    const first = within(map()).getByRole("button", { name: /^Cough, Symptom/ });
    first.focus();
    for (const key of ["{ArrowDown}", "{ArrowUp}", "{ArrowLeft}", "{ArrowRight}"]) {
      await userEvent.keyboard(key);
      if (document.activeElement !== first) break;
    }
    expect(document.activeElement).not.toBe(first);
    expect(document.activeElement?.getAttribute("data-node")).not.toBeNull();
  });

  it("shows calm empty states for layers and modes without real data", async () => {
    render(<GraphLive model={model} />);
    await userEvent.click(screen.getByRole("button", { name: "External" }));
    expect(screen.getByText("No external context is linked to your records yet.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Your links" }));
    expect(screen.getByText(/You haven't linked anything yourself yet/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Compare" }));
    await userEvent.click(screen.getByRole("button", { name: "Turn on" }));
    expect(screen.getByText(/No aggregate comparison data is available yet/)).toBeInTheDocument();
    expect(screen.getByText(/Replay · Everything, first noted/)).toBeInTheDocument();
  });

  it("offers a List view grouped by concern with links to each thread", async () => {
    render(<GraphLive model={model} />);
    await userEvent.click(screen.getByRole("tab", { name: "List" }));
    for (const t of fixture.threads) {
      const region = screen.getByRole("region", { name: t.title });
      expect(within(region).getByRole("link", { name: t.title })).toHaveAttribute("href", `/threads/${t.thread_id}`);
    }
    expect(screen.getByRole("region", { name: "Also in your records" })).toHaveTextContent("Blood pressure");
  });

  it("routes quick actions to real destinations", async () => {
    render(<GraphLive model={model} />);
    await userEvent.click(within(map()).getByRole("button", { name: /^Cough, Symptom/ }));
    await userEvent.click(screen.getByRole("button", { name: "Open concern" }));
    expect(push).toHaveBeenCalledWith(`/threads/${fixture.threads.find((t) => t.title === "Cough")!.thread_id}`);
    expect(screen.queryByRole("button", { name: "Link to…" })).not.toBeInTheDocument();
  });

  it("keeps 'links are not causes, never a diagnosis' visible", () => {
    render(<GraphLive model={model} />);
    expect(screen.getByText(/Links are not causes, and never a diagnosis/)).toBeInTheDocument();
  });
});

describe("GraphLive design preview", () => {
  it("is clearly labelled as sample data", () => {
    render(<GraphLive model={DESIGN_PREVIEW_MODEL} />);
    expect(screen.getByText("Design preview with sample data — not your records.")).toBeInTheDocument();
    expect(screen.getAllByText("Headaches").length).toBeGreaterThan(0);
  });
});
