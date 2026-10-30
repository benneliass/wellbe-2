import { act, fireEvent, render, screen, within } from "@testing-library/react";
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

  it.each(['release', 'leave', 'cancel', 'pinch'] as const)('keeps queued pan updates safe when the gesture ends by %s', (ending) => {
    render(<GraphLive model={model} />);
    const svg = map();
    vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({ x: 0, y: 0, left: 0, top: 0, right: 860, bottom: 686, width: 860, height: 686, toJSON: () => ({}) });
    const camera = svg.querySelector('[data-map-camera]')!;
    const before = camera.getAttribute('transform')!.match(/-?[\d.]+/g)!.map(Number);
    act(() => {
      fireEvent.pointerDown(svg, { clientX: 100, clientY: 100 });
      fireEvent.pointerMove(svg, { clientX: 120, clientY: 110 });
      fireEvent.pointerMove(svg, { clientX: 140, clientY: 130 });
      if (ending === 'pinch') fireEvent.touchStart(svg, { touches: [{ clientX: 100, clientY: 100 }, { clientX: 160, clientY: 100 }] });
      else if (ending === 'release') fireEvent.pointerUp(svg);
      else if (ending === 'cancel') fireEvent.pointerCancel(svg);
      else fireEvent.pointerLeave(svg);
    });
    const after = camera.getAttribute('transform')!.match(/-?[\d.]+/g)!.map(Number);
    expect(after[0]).toBeCloseTo(before[0]! + 40);
    expect(after[1]).toBeCloseTo(before[1]! + 30);
    expect(after[2]).toBe(before[2]);
    fireEvent.pointerMove(svg, { clientX: 300, clientY: 300 });
    expect(camera.getAttribute('transform')!.match(/-?[\d.]+/g)!.map(Number)).toEqual(after);
  });

  it("drags a node, its links follow, and the drag doesn't open the inspector", () => {
    render(<GraphLive model={model} patientId={PATIENT} />);
    const cough = nodeEl(COUGH);
    const before = centre(cough);
    const edgesBefore = Array.from(map().querySelectorAll("path")).map((p) => p.getAttribute("d"));
    drag(cough, { x: 200, y: 200 }, { x: 260, y: 230 });
    expect(centre(nodeEl(COUGH))).toEqual({ x: before.x + 60, y: before.y + 30 });
    const edgesAfter = Array.from(map().querySelectorAll("path")).map((p) => p.getAttribute("d"));
    expect(edgesAfter).not.toEqual(edgesBefore);
    // Links now meet the porcelain rim, rather than running through the center.
    const movedCenter = centre(nodeEl(COUGH));
    const rimEndpoints = edgesAfter.flatMap((d) => {
      const numbers = d?.match(/-?\d+(?:\.\d+)?/g)?.map(Number) ?? [];
      return numbers.length >= 4 ? [{ x: numbers[0]!, y: numbers[1]! }, { x: numbers.at(-2)!, y: numbers.at(-1)! }] : [];
    });
    expect(rimEndpoints.some((point) => Math.hypot(point.x - movedCenter.x, point.y - movedCenter.y) < 30)).toBe(true);
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
    const moved = centre(nodeEl(COUGH));
    expect(moved.x).toBeCloseTo(nodeBefore.x - 40, 8);
    expect(moved.y).toBeCloseTo(nodeBefore.y + 40, 8);
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

  it('preserves quick actions, hiding, restore, manual linking and dispute', async () => {
    render(<GraphLive model={DESIGN_PREVIEW_MODEL} />);
    const headache = () => within(map()).getByRole('button', { name: /^Headache, Symptom/ });
    fireEvent.contextMenu(headache());
    const menu = screen.getByRole('menu', { name: 'Quick actions' });
    const hide = within(menu).getByRole('menuitem', { name: /Hide/ });
    await userEvent.click(hide);
    expect(within(map()).queryByRole('button', { name: /^Headache, Symptom/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: /1 hidden · restore/ }));
    await userEvent.click(headache());
    await userEvent.click(screen.getByRole('button', { name: 'Link to…' }));
    await userEvent.click(within(map()).getByRole('button', { name: /^Diet change, Personal context/ }));
    expect(map().querySelector('[data-connection][data-source="headache"][data-target="diet"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Your links' })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(headache());
    await userEvent.click(screen.getByRole('button', { name: 'Why is Headache connected to Poor sleep?' }));
    await userEvent.click(screen.getByRole('button', { name: 'Dispute this connection' }));
    expect(screen.queryByRole('button', { name: 'Dispute this connection' })).toBeNull();
  });

  it('preserves narration, lens, comparison consent, replay and sharing selection', async () => {
    render(<GraphLive model={DESIGN_PREVIEW_MODEL} />);
    await userEvent.click(screen.getByRole('button', { name: 'Explain' }));
    expect(screen.getByText('Explain my graph')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Close narration' }));
    await userEvent.click(screen.getByRole('button', { name: 'Lens' }));
    expect(within(map()).getByRole('button', { name: /^Tension-pattern theory/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Lens' }));
    expect(within(map()).queryByRole('button', { name: /^Hydration,/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Compare' }));
    expect(within(map()).queryByRole('button', { name: /^Hydration,/ })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Turn on' }));
    expect(within(map()).getByRole('button', { name: /^Hydration,/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Compare' }));
    const replay = screen.getByRole('slider', { name: 'Replay timeline' });
    fireEvent.change(replay, { target: { value: '0' } });
    expect(within(map()).queryByRole('button', { name: /^Diet change,/ })).toBeNull();
    fireEvent.change(replay, { target: { value: String(DESIGN_PREVIEW_MODEL.timeline.labels.length - 1) } });
    expect(within(map()).getByRole('button', { name: /^Diet change,/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Share' }));
    await userEvent.click(within(map()).getByRole('button', { name: /^Headache, Symptom/ }));
    expect(screen.getByText('Select concepts to share — 1 selected.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Export 1 to visit packet' }));
    expect(push).toHaveBeenCalledWith('/prepare');
  });
});

describe("GraphLive source orbits and related concepts", () => {
  it("keeps sources orbiting while related concepts expand and collapse through one control", async () => {
    const evidence = DESIGN_PREVIEW_MODEL.nodes.find((node) => node.id === 'headache')!.evidence;
    const mixed = { ...DESIGN_PREVIEW_MODEL, nodes: DESIGN_PREVIEW_MODEL.nodes.map((node) => node.id === 'diet' ? { ...node, evidence } : node) };
    render(<GraphLive model={mixed} />);
    const parent = within(map()).getByRole('button', { name: /^Diet change, Personal context/ });
    const sourceIds = () => [...parent.querySelectorAll('[data-orbit-kind="source"]')].map((item) => item.getAttribute('data-orbit-item'));
    const sources = sourceIds();
    expect(sources).toHaveLength(5);
    expect(parent.querySelectorAll('[data-orbit-kind="concept"]')).toHaveLength(3);
    await userEvent.click(parent);
    expect(sourceIds()).toEqual(sources);
    expect(parent.querySelectorAll('[data-orbit-kind="concept"]')).toHaveLength(0);
    expect(within(map()).getByRole('button', { name: /^Weight log, Personal context/ })).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: /^Collapse on map$/ }));
    expect(sourceIds()).toEqual(sources);
    expect(parent.querySelectorAll('[data-orbit-kind="concept"]')).toHaveLength(3);
    expect(within(map()).queryByRole('button', { name: /^Weight log, Personal context/ })).toBeNull();
    expect(map().querySelector('[data-source-marker]')).toBeNull();
  });
});
