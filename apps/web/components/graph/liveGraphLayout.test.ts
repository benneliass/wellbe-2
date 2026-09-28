import { describe, expect, it } from "vitest";
import { toThreadSummary } from "@/lib/adapters";
import type { GraphModel, GraphNode } from "./graphData";
import { buildLiveGraph } from "./liveGraphAdapter";
import { boxesOverlap, clusterLabelBox, COMPACT_VIEW, layoutGraph, nodeBox, type ViewBox, WIDE_VIEW } from "./liveGraphLayout";
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
