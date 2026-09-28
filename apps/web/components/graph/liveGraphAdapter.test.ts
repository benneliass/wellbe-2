import { describe, expect, it } from "vitest";
import { toThreadSummary } from "@/lib/adapters";
import { buildLiveGraph, buildTimeline, layersWithData, type LiveGraphInput, weightToScore } from "./liveGraphAdapter";
import fixture from "./liveGraph.fixture.json";

/** Real /v1 + /v2 payloads for the seeded demo patient (captured 2026-09-27). */
function realInput(): LiveGraphInput {
  return {
    threads: fixture.threads.map((t) => toThreadSummary(t as never)),
    graphs: fixture.graphs as never,
    memories: fixture.memories as never,
    pending: fixture.pending as never,
    patterns: fixture.patterns as never,
    results: fixture.results as never,
    investigations: fixture.investigations as never,
  };
}

const FIXTURE_LABELS = ["MRI referral", "Late caffeine", "Light sensitivity", "Screen time", "Headaches", "Digestive"];

describe("buildLiveGraph on the real demo payloads", () => {
  const model = buildLiveGraph(realInput());
  const byLabel = (l: string) => model.nodes.find((n) => n.label === l)!;
  const threadId = (title: string) => fixture.threads.find((t) => t.title === title)!.thread_id;

  it("turns every thread into a concern cluster linking to its page", () => {
    expect(model.kind).toBe("live");
    expect(model.clusters.map((c) => c.label)).toEqual(fixture.threads.map((t) => t.title));
    expect(model.clusters[0]!.href).toBe(`/threads/${fixture.threads[0]!.thread_id}`);
    expect(new Set(model.clusters.map((c) => c.hue)).size).toBe(model.clusters.length);
    expect(model.clusters.find((c) => c.label === "Cough")!.statusLabel).toBe("Waiting for a result");
  });

  it("never invents nodes or edges", () => {
    const apiNodeIds = new Set(fixture.graphs.flatMap((g) => g.nodes.map((n) => n.id)));
    const pendingIds = new Set(fixture.pending.map((p) => `pending:${p.pending_item_id}`));
    for (const n of model.nodes) expect(apiNodeIds.has(n.id) || pendingIds.has(n.id)).toBe(true);
    const apiEdgeIds = new Set(fixture.graphs.flatMap((g) => g.edges.map((e) => e.id)));
    for (const e of model.edges) expect(apiEdgeIds.has(e.id!)).toBe(true);
    expect(model.nodes).toHaveLength(apiNodeIds.size + pendingIds.size);
    expect(model.edges).toHaveLength(apiEdgeIds.size);
    for (const l of FIXTURE_LABELS) expect(model.nodes.some((n) => n.label === l)).toBe(false);
  });

  it("uses in_thread for membership: a concept belongs to its own concern only", () => {
    const cough = byLabel("Cough");
    expect(cough.cluster).toBe(threadId("Cough"));
    expect(cough.bridge).toBeUndefined();
    expect(cough.type).toBe("symptom");
    expect(cough.typeLabel).toBe("Symptom");
    for (const l of ["Fatigue", "Hemoglobin A1c", "Blood pressure"]) {
      expect(byLabel(l).cluster).toBeUndefined();
      expect(byLabel(l).primary).toBe(false);
    }
    expect(byLabel("Blood pressure").type).toBe("vital");
  });

  it("marks theories and investigations shared by two concerns as investigation-layer bridges", () => {
    const theory = model.nodes.find((n) => n.type === "theory")!;
    expect(theory.layer).toBe("investigation");
    expect(theory.lensRole).toBe("theory");
    expect(new Set(theory.bridge)).toEqual(new Set([threadId("Cough"), threadId("Vitamin D (25-OH)")]));
    const inv = model.nodes.find((n) => n.type === "investigation")!;
    expect(inv.label).toMatch(/^Could the morning cough/);
    const hyp = model.edges.filter((e) => e.f === "hypothesis");
    expect(hyp.length).toBeGreaterThan(0);
    expect(hyp.every((e) => e.layer === "investigation")).toBe(true);
  });

  it("attaches real sources: memory facts to concepts and result observations to labs", () => {
    const cough = byLabel("Cough");
    expect(cough.evidence).toHaveLength(2);
    expect(cough.evidence!.every((s) => s.displayLabel === "Fact from what you added" && s.component === "c5")).toBe(true);
    expect(cough.ev).toBe(2);
    expect(cough.captures).toHaveLength(2);

    const a1c = byLabel("Hemoglobin A1c");
    expect(a1c.evidence).toHaveLength(1);
    expect(a1c.evidence![0]).toMatchObject({ displayLabel: "Entered by you", component: "c2", kind: "lab", reviewMarkers: ["patient-entered"] });
    expect(a1c.evidence![0]!.excerpt).toContain("Hemoglobin A1c: 5.4 %");

    const vitD = byLabel("Vitamin D (25-OH)");
    expect(vitD.evidence!.map((s) => s.displayLabel)).toEqual(expect.arrayContaining(["Fact from what you added", "Entered by you"]));
  });

  it("turns open pending items into open-loop ghosts inside their concern", () => {
    const loop = model.nodes.find((n) => n.ghost)!;
    expect(loop.label).toBe("Waiting for a result: Cough");
    expect(loop.cluster).toBe(threadId("Cough"));
    expect(loop.layer).toBe("continuity");
    expect(loop.statusNote).toMatch(/^Check back Oct/);
    expect(loop.evidence).toEqual([]);
  });

  it("maps edge weight to strong vs candidate links and keeps the pattern caveat", () => {
    const strong = model.edges.find((e) => e.id === "30801dd3-1c84-4827-9d26-c392ebf23468")!; // cough–pain 0.9
    expect(strong.s).toBe(6);
    expect(strong.f).toBe("co");
    expect(strong.phrase).toBe("appears with");
    expect(strong.note).toMatch(/not a cause, and not a diagnosis/);
    expect(strong.alternatives!.length).toBeGreaterThan(0);
    expect(strong.evidence!.length).toBeGreaterThan(0);
    const weak = model.edges.filter((e) => e.s <= 2 && e.f !== "hypothesis");
    expect(weak.length).toBeGreaterThan(0);
    expect(weak.every((e) => e.f === "cand")).toBe(true);
    expect(model.edges.some((e) => e.f === "conflict" || e.f === "user")).toBe(false);
  });

  it("reports empty layers honestly", () => {
    expect(layersWithData(model)).toEqual({
      observation: true,
      concept: true,
      thread: true,
      continuity: true,
      correction: false,
      investigation: true,
      external: false,
    });
    expect(model.comparisonAvailable).toBe(false);
    expect(model.canAuthorLinks).toBe(false);
    expect(model.actions.map((a) => a.id)).not.toContain("link");
  });

  it("collapses Replay to one bucket when everything was first noted the same day", () => {
    expect(model.timeline.labels).toHaveLength(1);
    expect(model.timeline.valueTexts[0]).toMatch(/first noted September 27, 2026/);
    expect(model.nodes.every((n) => n.week === 0)).toBe(true);
  });
});

describe("buildLiveGraph edge cases", () => {
  const thread = (id: string, title: string) =>
    toThreadSummary({ thread_id: id, title, status: "active_unresolved", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" } as never);
  const node = (id: string, label: string, extra: Record<string, unknown> = {}) => ({ id, type: "Symptom", label, status: "active", attributes: { first_seen_at: "2026-03-01T00:00:00Z", ...extra } });

  it("flags contradictions and user-authored links, and skips edges to unknown nodes", () => {
    const model = buildLiveGraph({
      threads: [thread("t1", "Sleep")],
      graphs: [
        {
          thread_id: "t1",
          schema_version: "c13.graph.subgraph.v2",
          nodes: [node("a", "poor sleep", { in_thread: true }), node("b", "caffeine", { in_thread: true })],
          edges: [
            { id: "e1", source: "a", target: "b", relation: "contradicts", evidence_weight: 0.5 },
            { id: "e2", source: "b", target: "a", relation: "co_occurs_with", evidence_weight: 0.7, attributes: { origin: "user" } },
            { id: "e3", source: "a", target: "ghost", relation: "co_occurs_with", evidence_weight: 0.9 },
          ],
        },
      ],
    });
    expect(model.edges.map((e) => [e.id, e.f])).toEqual([
      ["e1", "conflict"],
      ["e2", "user"],
    ]);
    expect(model.edges[1]!.layer).toBe("correction");
    expect(layersWithData(model).correction).toBe(true);
  });

  it("treats a node without in_thread as a member and bridges nodes in two concerns", () => {
    const shared = node("s", "dizziness");
    const model = buildLiveGraph({
      threads: [thread("t1", "Headaches"), thread("t2", "Sleep")],
      graphs: [
        { thread_id: "t1", schema_version: "c13.graph.subgraph.v2", nodes: [shared], edges: [] },
        { thread_id: "t2", schema_version: "c13.graph.subgraph.v2", nodes: [shared], edges: [] },
      ],
    });
    expect(model.nodes[0]!.bridge).toEqual(["t1", "t2"]);
  });

  it("keeps clusters when a thread's graph failed to load", () => {
    const model = buildLiveGraph({ threads: [thread("t1", "Cough")], graphs: [undefined] });
    expect(model.clusters).toHaveLength(1);
    expect(model.nodes).toHaveLength(0);
  });

  it("adds external context only from real investigation refs", () => {
    const model = buildLiveGraph({
      threads: [thread("t1", "Cough")],
      graphs: [
        {
          thread_id: "t1",
          schema_version: "c13.graph.subgraph.v2",
          nodes: [{ id: "inv", type: "Investigation", label: "Is it seasonal?", status: "active", attributes: { in_thread: true } }],
          edges: [],
        },
      ],
      investigations: [
        { investigation_id: "i1", primary_question: "Is it seasonal?", health_thread_ids: ["t1"], external_context_refs: ["ref-1", "ref-2"], created_at: "2026-03-01T00:00:00Z", updated_at: "2026-03-02T00:00:00Z" } as never,
      ],
    });
    const ext = model.nodes.find((n) => n.type === "external")!;
    expect(ext.label).toBe("External context (2)");
    expect(ext.evidence!.every((s) => s.component === "c16")).toBe(true);
    expect(model.edges).toEqual([expect.objectContaining({ a: ext.id, b: "inv", f: "relevance", layer: "external" })]);
  });
});

describe("weightToScore", () => {
  it("maps 0..1 onto the 1..7 score scale", () => {
    expect(weightToScore(0.9)).toBe(6);
    expect(weightToScore(0.6)).toBe(4);
    expect(weightToScore(0.3)).toBe(2);
    expect(weightToScore(0)).toBe(1);
    expect(weightToScore(1)).toBe(7);
    expect(weightToScore(Number.NaN)).toBe(1);
  });
});

describe("buildTimeline", () => {
  it("splits a real date span into at most six buckets, oldest first", () => {
    const t = buildTimeline(["2026-01-05T00:00:00Z", "2026-02-10T00:00:00Z", "2026-03-20T00:00:00Z", "2026-06-01T00:00:00Z"]);
    expect(t.labels).toHaveLength(4);
    expect(t.bucketOf("2026-01-05T00:00:00Z")).toBe(0);
    expect(t.bucketOf("2026-06-01T00:00:00Z")).toBe(3);
    expect(t.bucketOf(undefined)).toBe(0);
    expect(t.valueTexts.at(-1)).toBe("Now, everything so far");
  });

  it("handles no dates", () => {
    expect(buildTimeline([]).labels).toEqual(["Now"]);
  });
});
