import { describe, expect, it } from "vitest";
import { toThreadSummary } from "@/lib/adapters";
import type { GraphModel, GraphNode } from "./graphData";
import { buildLiveGraph } from "./liveGraphAdapter";
import { denseModel } from "./denseGraph.fixture";
import { boxesOverlap, clusterLabelBox, COMPACT_VIEW, defaultVisible, edgeCrossings, edgePathD, layoutGraph, nodeBox, type ViewBox, WIDE_VIEW } from "./liveGraphLayout";
import fixture from "./liveGraph.fixture.json";

function realModel(): GraphModel {
  return buildLiveGraph({
    threads: fixture.threads.map((t) => toThreadSummary(t as never)),
    graphs: fixture.graphs as never,
    memories: fixture.memories as never,
    pending: fixture.pending as never,
    patterns: fixture.patterns as never,
    results: fixture.results as never,
    investigations: fixture.investigations as never,
  });
}

function overlaps(model: GraphModel): string[] {
  const boxes = [
    ...model.nodes.map(nodeBox),
    ...model.clusters.map((c) => clusterLabelBox(c, c.labelX!, c.labelY!)),
  ];
  const out: string[] = [];
  for (let i = 0; i < boxes.length; i++)
    for (let j = i + 1; j < boxes.length; j++) if (boxesOverlap(boxes[i]!, boxes[j]!)) out.push(`${boxes[i]!.id} × ${boxes[j]!.id}`);
  return out;
}

describe.each<[string, ViewBox]>([
  ["wide", WIDE_VIEW],
  ["compact", COMPACT_VIEW],
])("layoutGraph on the real data set (%s)", (_name, view) => {
  const { model, extent } = layoutGraph(realModel(), view);

  it("fits in the view without growing the canvas", () => {
    expect(extent).toEqual({ width: view.width, height: view.height - view.gutter });
    for (const n of model.nodes) {
      const b = nodeBox(n);
      expect(b.x - b.hw).toBeGreaterThanOrEqual(0);
      expect(b.x + b.hw).toBeLessThanOrEqual(view.width);
      expect(b.y - b.up).toBeGreaterThanOrEqual(0);
      expect(b.y + b.down).toBeLessThanOrEqual(view.height - view.gutter);
    }
  });

  it("keeps every node label and concern title clear of each other", () => {
    expect(overlaps(model)).toEqual([]);
  });

  it("routes no link shown by default through a node or label it doesn't belong to", () => {
    expect(edgeCrossings(defaultVisible(model))).toEqual([]);
  });

  it("wraps each concern's own concepts inside its halo", () => {
    for (const c of model.clusters) {
      for (const n of model.nodes.filter((x) => x.cluster === c.id && !x.bridge)) {
        const dx = (n.x - c.cx) / c.rx;
        const dy = (n.y - c.cy) / c.ry;
        expect(dx * dx + dy * dy).toBeLessThanOrEqual(1.05);
      }
    }
  });

  it("is deterministic", () => {
    const again = layoutGraph(realModel(), view).model;
    expect(again.nodes.map((n) => [n.x, n.y])).toEqual(model.nodes.map((n) => [n.x, n.y]));
  });
});

describe.each<[string, ViewBox]>([
  ["wide", WIDE_VIEW],
  ["compact", COMPACT_VIEW],
])("layoutGraph on a dense demo-like graph (%s)", (_name, view) => {
  const dense = denseModel();
  const started = performance.now();
  const { model, extent } = layoutGraph(dense, view);
  const ms = performance.now() - started;

  it("is dense enough to matter", () => {
    expect(dense.nodes.length).toBeGreaterThanOrEqual(40);
    expect(dense.nodes.filter((n) => n.bridge).length).toBeGreaterThanOrEqual(8);
    expect(dense.edges.length).toBeGreaterThan(dense.nodes.length);
  });

  it("routes no link through a node or label it doesn't belong to", () => {
    expect(edgeCrossings(model)).toEqual([]);
  });

  it("keeps every node label and concern title clear of each other", () => {
    expect(overlaps(model)).toEqual([]);
  });

  it("grows the canvas instead of cramming, and stays quick", () => {
    expect(extent.width).toBeGreaterThan(view.width);
    expect(ms).toBeLessThan(3000);
  });

  it("bends links between concerns and keeps links inside a concern straight", () => {
    const byId = new Map(model.nodes.map((n) => [n.id, n]));
    const owners = (id: string) => byId.get(id)!.bridge ?? (byId.get(id)!.cluster ? [byId.get(id)!.cluster!] : []);
    const intra = model.edges.filter((e) => owners(e.a).some((c) => owners(e.b).includes(c)));
    const inter = model.edges.filter((e) => !owners(e.a).some((c) => owners(e.b).includes(c)));
    expect(intra.filter((e) => e.bend === 0).length).toBeGreaterThan(intra.length * 0.8);
    expect(inter.filter((e) => e.bend !== 0).length).toBeGreaterThan(inter.length * 0.8);
  });

  it("is deterministic", () => {
    const again = layoutGraph(denseModel(), view).model;
    expect(again.nodes.map((n) => [n.x, n.y])).toEqual(model.nodes.map((n) => [n.x, n.y]));
    expect(again.edges.map((e) => e.bend)).toEqual(model.edges.map((e) => e.bend));
  });
});

describe("edge geometry", () => {
  it("draws straight links as a segment and routed links as a quadratic curve", () => {
    expect(edgePathD({ x: 0, y: 0 }, { x: 100, y: 0 }, 0)).toBe("M0,0 L100,0");
    expect(edgePathD({ x: 0, y: 0 }, { x: 100, y: 0 }, 20)).toBe("M0,0 Q50.0,20.0 100,0");
  });

  it("flags a link that runs straight through a third node", () => {
    const base = realModel();
    const t = base.nodes[0]!;
    const nodes = [
      { ...t, id: "a", label: "A", x: 100, y: 100, bridge: undefined },
      { ...t, id: "b", label: "B", x: 400, y: 100, bridge: undefined },
      { ...t, id: "c", label: "C", x: 250, y: 102, bridge: undefined },
    ];
    const edges = [{ a: "a", b: "b", s: 4, f: "co" as const, layer: "concept" as const, week: 0, bend: 0 }];
    const model = { ...base, clusters: [], nodes, edges };
    expect(edgeCrossings(model)).toEqual(["a→b × c"]);
    expect(edgeCrossings({ ...model, edges: [{ ...edges[0]!, bend: -120 }] })).toEqual([]);
  });
});

describe("layoutGraph at scale", () => {
  it("lays out ~200 nodes quickly and grows the virtual canvas instead of stacking labels", () => {
    const base = realModel();
    const nodes: GraphNode[] = Array.from({ length: 200 }, (_, i) => ({
      ...base.nodes[0]!,
      id: `n${i}`,
      label: `Item number ${i}`,
      cluster: base.clusters[i % base.clusters.length]!.id,
      bridge: undefined,
    }));
    const edges = nodes.slice(1).map((n, i) => ({ id: `e${i}`, a: nodes[i]!.id, b: n.id, s: 4, f: "co" as const, layer: "concept" as const, week: 0 }));
    const started = performance.now();
    const { model, extent } = layoutGraph({ ...base, nodes, edges }, WIDE_VIEW);
    const ms = performance.now() - started;
    expect(ms).toBeLessThan(2000);
    expect(extent.width).toBeGreaterThan(WIDE_VIEW.width);
    expect(model.nodes.every((n) => Number.isFinite(n.x) && Number.isFinite(n.y))).toBe(true);
    const bad = overlaps(model).length;
    expect(bad).toBeLessThan(nodes.length * 0.02);
  });
});
