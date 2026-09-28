import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toThreadSummary } from "@/lib/adapters";
import { GraphLive } from "./GraphLive";
import { positionsKey } from "./graphDrag";
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

  it("moves focus between nodes with Alt + arrow keys", async () => {
    render(<GraphLive model={model} />);
    const first = within(map()).getByRole("button", { name: /^Cough, Symptom/ });
    first.focus();
    for (const key of ["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"]) {
      await userEvent.keyboard(`{Alt>}{${key}}{/Alt}`);
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

const PATIENT = "de7a0000-0000-4000-8000-000000000001";
const COUGH = /^Cough, Symptom/;

function nodeEl(name: RegExp) {
  return within(map()).getByRole("button", { name });
}
/** Centre of a node's disc as drawn (the focus ring shares it). */
function centre(el: HTMLElement) {
  const c = el.querySelector("circle")!;
  return { x: Number(c.getAttribute("cx")), y: Number(c.getAttribute("cy")) };
}
function drag(el: Element, from: { x: number; y: number }, to: { x: number; y: number }) {
  fireEvent.pointerDown(el, { pointerId: 1, pointerType: "mouse", button: 0, clientX: from.x, clientY: from.y });
  fireEvent.pointerMove(el, { pointerId: 1, pointerType: "mouse", clientX: (from.x + to.x) / 2, clientY: (from.y + to.y) / 2 });
  fireEvent.pointerMove(el, { pointerId: 1, pointerType: "mouse", clientX: to.x, clientY: to.y });
  fireEvent.pointerUp(el, { pointerId: 1, pointerType: "mouse", clientX: to.x, clientY: to.y });
  fireEvent.click(el);
}
function saved() {
  return JSON.parse(window.localStorage.getItem(positionsKey(PATIENT)) ?? "{}") as Record<string, Record<string, [number, number]>>;
}

describe("GraphLive dragging", () => {
  beforeEach(() => window.localStorage.clear());

  it("drags a node, its links follow, and the drag doesn't open the inspector", () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const cough = nodeEl(COUGH);
    const before = centre(cough);
    const edgesBefore = Array.from(map().querySelectorAll("path")).map((p) => p.getAttribute("d"));
    drag(cough, { x: 200, y: 200 }, { x: 260, y: 230 });
    expect(centre(nodeEl(COUGH))).toEqual({ x: before.x + 60, y: before.y + 30 });
    const edgesAfter = Array.from(map().querySelectorAll("path")).map((p) => p.getAttribute("d"));
    expect(edgesAfter).not.toEqual(edgesBefore);
    expect(edgesAfter.some((d) => d?.startsWith(`M${before.x + 60},${before.y + 30}`) || d?.endsWith(`${before.x + 60},${before.y + 30}`))).toBe(true);
    expect(within(screen.getByRole("complementary", { name: "Details" })).queryByText("Cough", { selector: "p" })).not.toBeInTheDocument();
  });

  it("still opens the inspector on a press that moves less than the threshold", () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const cough = nodeEl(COUGH);
    const before = centre(cough);
    drag(cough, { x: 200, y: 200 }, { x: 202, y: 201 });
    expect(centre(nodeEl(COUGH))).toEqual(before);
    expect(within(screen.getByRole("complementary", { name: "Details" })).getByText("Cough", { selector: "p" })).toBeInTheDocument();
  });

  it("never pans the canvas while dragging a node", () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const layer = map().querySelector("g[transform^='translate']")!;
    const transform = layer.getAttribute("transform");
    drag(nodeEl(COUGH), { x: 200, y: 200 }, { x: 320, y: 280 });
    expect(layer.getAttribute("transform")).toBe(transform);
  });

  it("drags a concern title together with its concepts", () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const cough = model.clusters.find((c) => c.label === "Cough")!;
    const title = map().querySelector(`[data-cluster-drag="${cough.id}"]`)!;
    const text = title.querySelector("text")!;
    const tx = Number(text.getAttribute("x"));
    const nodeBefore = centre(nodeEl(COUGH));
    const shared = nodeEl(/^Hemoglobin A1c, Lab result/);
    const sharedBefore = centre(shared);
    drag(title, { x: 100, y: 100 }, { x: 60, y: 140 });
    expect(Number(map().querySelector(`[data-cluster-drag="${cough.id}"] text`)!.getAttribute("x"))).toBe(tx - 40);
    expect(centre(nodeEl(COUGH))).toEqual({ x: nodeBefore.x - 40, y: nodeBefore.y + 40 });
    expect(centre(nodeEl(/^Hemoglobin A1c, Lab result/))).toEqual(sharedBefore);
  });

  it("nudges the focused node with arrow keys, further with Shift", async () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const before = centre(nodeEl(COUGH));
    nodeEl(COUGH).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(centre(nodeEl(COUGH))).toEqual({ x: before.x + 8, y: before.y });
    await userEvent.keyboard("{Shift>}{ArrowUp}{/Shift}");
    expect(centre(nodeEl(COUGH))).toEqual({ x: before.x + 8, y: before.y - 40 });
    expect(document.activeElement).toBe(nodeEl(COUGH));
  });

  it("remembers moved nodes per patient and restores them on the next visit", () => {
    const first = render(<GraphLive model={model} patientId={PATIENT} />);
    const before = centre(nodeEl(COUGH));
    drag(nodeEl(COUGH), { x: 200, y: 200 }, { x: 250, y: 200 });
    const views = saved();
    const id = nodeEl(COUGH).getAttribute("data-node-id")!;
    expect(Object.values(views)[0]![id]).toEqual([before.x + 50, before.y]);
    first.unmount();

    render(<GraphLive model={model} patientId={PATIENT} />);
    expect(centre(nodeEl(COUGH))).toEqual({ x: before.x + 50, y: before.y });
  });

  it("ignores saved ids that are no longer on the map", () => {
    const cough = model.nodes.find((n) => n.label === "Cough")!;
    window.localStorage.setItem(positionsKey(PATIENT), JSON.stringify({ "860x686": { gone: [1, 1] } }));
    render(<GraphLive model={model} patientId={PATIENT} />);
    expect(centre(nodeEl(COUGH)).x).not.toBe(1);
    expect(screen.queryByRole("button", { name: "Reset layout" })).not.toBeInTheDocument();
    expect(cough).toBeDefined();
  });

  it("puts everything back with Reset layout", async () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const before = centre(nodeEl(COUGH));
    expect(screen.queryByRole("button", { name: "Reset layout" })).not.toBeInTheDocument();
    drag(nodeEl(COUGH), { x: 200, y: 200 }, { x: 280, y: 260 });
    await userEvent.click(screen.getByRole("button", { name: "Reset layout" }));
    expect(centre(nodeEl(COUGH))).toEqual(before);
    expect(window.localStorage.getItem(positionsKey(PATIENT))).toBeNull();
    expect(screen.queryByRole("button", { name: "Reset layout" })).not.toBeInTheDocument();
  });
});

describe("GraphLive design preview", () => {
  it("is clearly labelled as sample data", () => {
    render(<GraphLive model={DESIGN_PREVIEW_MODEL} />);
    expect(screen.getByText("Design preview with sample data — not your records.")).toBeInTheDocument();
    expect(screen.getAllByText("Headaches").length).toBeGreaterThan(0);
  });
});
