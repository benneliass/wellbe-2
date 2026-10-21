import { describe, expect, it } from "vitest";
import { generateTopology } from "../src/generate.js";
import { RawContextLab } from "../src/router.js";
import type { TerminalReason, VaultEvent } from "../src/types.js";

const REASONS: TerminalReason[] = [
  "supported_leaf",
  "approximate_frontier_exhausted",
  "budget_exhausted",
  "policy_blocked",
  "authorization_changed",
  "stale_snapshot",
  "dependency_unavailable",
  "insufficient_independent_evidence",
];

function event(id: string, text: string): VaultEvent {
  return {
    id,
    personId: "p1",
    capturedAt: "2024-02-01T00:00:00.000Z",
    sourceType: "note",
    text,
    contentHash: id,
    lineageId: id,
    documentId: null,
  };
}

describe("bounded navigation", () => {
  it("continues a saved frontier without a new candidate search", () => {
    const lab = generateTopology({ count: 20, kind: "sparse", seed: 4, pageSize: 3, hopLimit: 12 });
    const searchesBefore = lab.hnswSearchCount;
    const first = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      anchorId: "n0",
    });
    expect(first.routeHandle).toBeTruthy();
    expect(first.items.length).toBeLessThanOrEqual(5);
    expect(first.items.length).toBeGreaterThan(0);
    expect(first.nextRoutes.length).toBeGreaterThanOrEqual(2);
    expect(first.nextRoutes.length).toBeLessThanOrEqual(7);
    expect(first.nextRoutes.some((route) => route.kind === "fallback")).toBe(true);
    const searchesAfter = lab.hnswSearchCount;
    const second = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      routeHandle: first.routeHandle ?? "",
    });
    expect(lab.hnswSearchCount).toBe(searchesAfter);
    expect(searchesAfter).toBe(searchesBefore);
    const firstHandles = new Set(first.items.map((item) => item.excerpt));
    expect(second.items.every((item) => !firstHandles.has(item.excerpt))).toBe(true);
    expect(second.detail.toLowerCase()).not.toContain("no relevant context");
  });

  it("stops a cycle instead of walking it again", () => {
    const lab = generateTopology({ count: 12, kind: "cyclic", seed: 5, pageSize: 6, hopLimit: 30 });
    let response = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      anchorId: "n0",
    });
    for (let step = 0; step < 12 && response.routeHandle; step += 1) {
      response = lab.explore({
        personId: "synthetic-1",
        purpose: "nav",
        routeHandle: response.routeHandle,
      });
    }
    expect(response.terminalReason).not.toBeNull();
    expect(REASONS).toContain(response.terminalReason);
    expect(response.cycleCount).toBeGreaterThan(0);
  });

  it("invalidates a handle when the snapshot or authorization changes", () => {
    const lab = generateTopology({ count: 8, kind: "sparse", seed: 6, pageSize: 3, hopLimit: 20 });
    const first = lab.explore({ personId: "synthetic-1", purpose: "nav", anchorId: "n0" });
    const handle = first.routeHandle ?? "";
    const ad = lab.log.ads[0];
    expect(ad).toBeTruthy();
    lab.withdraw(ad.id);
    const stale = lab.explore({ personId: "synthetic-1", purpose: "nav", routeHandle: handle });
    expect(stale.terminalReason).toBe("stale_snapshot");
    expect(stale.items).toEqual([]);
    expect(lab.metrics.cacheClears).toBeGreaterThan(0);

    const fresh = lab.explore({ personId: "synthetic-1", purpose: "nav", anchorId: "n1" });
    lab.setAuthorizationEpoch(2);
    const denied = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      routeHandle: fresh.routeHandle ?? "",
    });
    expect(denied.terminalReason).toBe("authorization_changed");
  });

  it("expires a handle and enforces the use limit", () => {
    let now = 1_000;
    const lab = new RawContextLab({ now: () => now, handleTtlMs: 500, maxHandleUses: 1, hopLimit: 10, pageSize: 1 });
    lab.addFixture(event("a", "alpha"));
    lab.addFixture(event("b", "beta"));
    lab.addFixture(event("c", "gamma"));
    lab.addFixture(event("d", "delta"));
    lab.linkStructural("a", "b");
    lab.linkStructural("b", "c");
    lab.linkStructural("c", "d");
    const first = lab.explore({ personId: "p1", purpose: "nav", anchorId: "a" });
    now = 2_000;
    const expired = lab.explore({ personId: "p1", purpose: "nav", routeHandle: first.routeHandle ?? "" });
    expect(expired.terminalReason).toBe("policy_blocked");
    expect(expired.detail).toContain("expired");

    now = 1_000;
    const live = new RawContextLab({ now: () => now, handleTtlMs: 50_000, maxHandleUses: 1, hopLimit: 10, pageSize: 1 });
    live.addFixture(event("a", "alpha"));
    live.addFixture(event("b", "beta"));
    live.addFixture(event("c", "gamma"));
    live.addFixture(event("d", "delta"));
    live.linkStructural("a", "b");
    live.linkStructural("b", "c");
    live.linkStructural("c", "d");
    const started = live.explore({ personId: "p1", purpose: "nav", anchorId: "a" });
    live.explore({ personId: "p1", purpose: "nav", routeHandle: started.routeHandle ?? "" });
    const limited = live.explore({ personId: "p1", purpose: "nav", routeHandle: started.routeHandle ?? "" });
    expect(limited.detail).toContain("use limit");
  });

  it("names an exact leaf without calling it missing context", () => {
    const lab = new RawContextLab();
    lab.addFixture(event("alone", "lentil soup"));
    const response = lab.explore({ personId: "p1", purpose: "nav", anchorId: "alone" });
    expect(response.terminalReason).toBe("supported_leaf");
    expect(response.exhaustion).toBe("exact");
    expect(response.detail.toLowerCase()).not.toContain("no relevant context");
  });

  it("follows an advertised route and can stop on the fallback", () => {
    const lab = generateTopology({ count: 10, kind: "sparse", seed: 8, pageSize: 3, hopLimit: 20 });
    const first = lab.explore({ personId: "synthetic-1", purpose: "nav", anchorId: "n0" });
    const fallback = first.nextRoutes.find((route) => route.kind === "fallback");
    expect(fallback).toBeTruthy();
    const stopped = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      routeHandle: first.routeHandle ?? "",
      routeId: fallback?.routeId,
    });
    expect(stopped.terminalReason).toBe("supported_leaf");
  });

  it("replays a request id without advancing the frontier", () => {
    const lab = generateTopology({ count: 12, kind: "sparse", seed: 4, pageSize: 3, hopLimit: 12 });
    const first = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      anchorId: "n0",
      requestId: "page-1",
    });
    const replay = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      routeHandle: first.routeHandle ?? "",
      requestId: "page-1",
    });
    expect(replay.items.map((item) => item.excerpt)).toEqual(first.items.map((item) => item.excerpt));
    expect(replay.hopDepth).toBe(first.hopDepth);
    const next = lab.explore({
      personId: "synthetic-1",
      purpose: "nav",
      routeHandle: first.routeHandle ?? "",
      requestId: "page-2",
    });
    expect(next.hopDepth).toBeGreaterThan(first.hopDepth);
  });

  it("stops a hub expand when the expansion budget is spent", () => {
    const lab = generateTopology({
      count: 40,
      kind: "hub",
      seed: 3,
      pageSize: 10,
      hopLimit: 20,
      expansionBudget: 5,
    });
    const response = lab.explore({ personId: "synthetic-1", purpose: "nav", anchorId: "n0" });
    expect(response.terminalReason).toBe("budget_exhausted");
    expect(response.items.length).toBeLessThan(10);
  });

  it("unions an exact token and a graph neighbor with the index", () => {
    const lab = new RawContextLab();
    lab.addFixture(event("a", "zephyrquartz alpha only"));
    lab.addFixture(event("b", "broom closet"));
    lab.addFixture(event("c", "unrelated shelf"));
    lab.linkStructural("a", "b");
    const split = lab.candidateSplit("p1", "zephyrquartz alpha", "a");
    expect(split.exact).toContain("b");
    const byText = lab.candidateSplit("p1", "zephyrquartz alpha only", "");
    expect(byText.exact).toContain("a");
  });

  it("describes an opened trail with the same counts as an exploration", () => {
    const lab = new RawContextLab({ seed: 1, pageSize: 1 });
    lab.addFixture(event("a", "alpha fever"));
    lab.addFixture(event("b", "beta crp"));
    lab.addFixture(event("c", "gamma esr"));
    lab.linkStructural("a", "b", "recorded_association");
    lab.linkStructural("b", "c", "temporal_neighbour");
    const opened = lab.describeTrail("p1", ["a", "b", "c"]);
    expect(opened.page.hopDepth).toBe(2);
    expect(opened.counts.exploredCount).toBe(3);
    expect(opened.counts.reachableCount).toBe(3);
    expect(opened.page.directLinkCount).toBe(1);
    expect(opened.page.breadcrumb).toHaveLength(3);
    expect(opened.page.detail.toLowerCase()).not.toContain("no relevant context");
    const stopped = lab.describeTrail("p1", ["a", "c"]);
    expect(stopped.page.hopDepth).toBe(0);
    expect(stopped.counts.exploredCount).toBe(1);
  });
});
