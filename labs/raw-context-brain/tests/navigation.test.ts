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
    for (let step = 0; step < 12 && response.routeHandle && !response.terminalReason; step += 1) {
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

  it("refuses a guessed continuation id", () => {
    const lab = generateTopology({ count: 8, kind: "sparse", seed: 6, pageSize: 3, hopLimit: 20 });
    const first = lab.explore({ personId: "synthetic-1", purpose: "nav", anchorId: "n0" });
    const handle = first.routeHandle ?? "";
    expect(handle).toMatch(/^rh_[0-9a-f]{32}$/);
    const flipped = `${handle.slice(0, -1)}${handle.endsWith("a") ? "b" : "a"}`;
    const guesses = ["rh_0", "rh_1", "rh_2", `rh_${"0".repeat(32)}`, flipped];
    for (const guess of guesses) {
      const denied = lab.explore({ personId: "synthetic-1", purpose: "nav", routeHandle: guess });
      expect(denied.terminalReason).toBe("policy_blocked");
      expect(denied.detail).toContain("not recognized");
      expect(denied.items).toEqual([]);
    }
    const frontier = lab.localOverlay(handle)?.frontier;
    const otherPerson = lab.explore({ personId: "someone-else", purpose: "nav", routeHandle: handle });
    expect(otherPerson.terminalReason).toBe("policy_blocked");
    expect(lab.localOverlay(handle)?.frontier).toEqual(frontier);
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

  it("steps only the advertised note named by a click", () => {
    const lab = new RawContextLab({ pageSize: 5, hopLimit: 8 });
    lab.addFixture(event("a", "alpha fever"));
    lab.addFixture(event("b", "beta crp"));
    lab.addFixture(event("c", "gamma esr"));
    lab.linkStructural("a", "b");
    lab.linkStructural("a", "c");
    const opened = lab.explore({
      personId: "p1",
      purpose: "look",
      anchorId: "a",
      holdAtAnchor: true,
    });
    const handle = opened.routeHandle ?? "";
    const toBeta = lab.localRoutes(handle).find((route) => route.nodeIds.length === 1 && route.nodeIds[0] === "b");
    expect(toBeta?.kind).toBe("neighbour");
    const searches = lab.hnswSearchCount;
    const stepped = lab.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: handle,
      routeId: toBeta?.routeId,
      focusId: "b",
    });
    expect(lab.hnswSearchCount).toBe(searches);
    expect(stepped.hopDepth).toBe(1);
    expect(stepped.items).toHaveLength(1);
    expect(stepped.items[0]?.excerpt).toContain("beta");
    const overlay = lab.localOverlay(stepped.routeHandle ?? "");
    expect(overlay?.visited).toEqual(["a", "b"]);
    expect(overlay?.frontier).toContain("c");
    expect(stepped.nextRoutes.every((route) => !("nodeIds" in route))).toBe(true);
  });

  it("refuses a note that is not on the advertised route and leaves the frontier", () => {
    const lab = new RawContextLab({ pageSize: 1, hopLimit: 8 });
    lab.addFixture(event("a", "alpha fever"));
    lab.addFixture(event("b", "beta crp"));
    lab.addFixture(event("c", "gamma esr"));
    lab.linkStructural("a", "b");
    lab.linkStructural("a", "c");
    const opened = lab.explore({
      personId: "p1",
      purpose: "look",
      anchorId: "a",
      holdAtAnchor: true,
    });
    const handle = opened.routeHandle ?? "";
    const frontier = lab.localOverlay(handle)?.frontier ?? [];
    const neighbour = lab.localRoutes(handle).find((route) => route.kind === "neighbour");
    expect(neighbour).toBeTruthy();
    const missing = lab.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: handle,
      routeId: neighbour?.routeId,
      focusId: "not-on-the-route",
    });
    expect(missing.terminalReason).toBe("policy_blocked");
    expect(lab.localOverlay(handle)?.frontier).toEqual(frontier);
    const bare = lab.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: handle,
      focusId: "b",
    });
    expect(bare.terminalReason).toBe("policy_blocked");
    expect(lab.localOverlay(handle)?.frontier).toEqual(frontier);
  });

  it("does not link a copied note until an advertisement says so", () => {
    const lab = new RawContextLab();
    lab.addFixture({ ...event("orig", "original letter"), lineageId: "letter" });
    lab.addFixture({
      ...event("copy", "copied letter"),
      lineageId: "letter-copy",
      copiedFromId: "orig",
      sourceArrival: "copied",
    });
    expect(lab.projection.edgeBetween("copy", "orig")).toBeUndefined();
  });

  it("advertises the original record when that note is already on the frontier", () => {
    const lab = new RawContextLab({ pageSize: 1, hopLimit: 8 });
    lab.addFixture({ ...event("orig", "original letter"), lineageId: "letter" });
    lab.addFixture({
      ...event("copy", "copied letter"),
      lineageId: "letter-copy",
      copiedFromId: "orig",
      sourceArrival: "copied",
    });
    lab.linkStructural("copy", "orig", "derived_or_copied");
    const opened = lab.explore({
      personId: "p1",
      purpose: "look",
      anchorId: "copy",
      holdAtAnchor: true,
    });
    const source = lab.localRoutes(opened.routeHandle ?? "").find((route) => route.kind === "source");
    expect(source?.label).toBe("Original record");
    expect(source?.nodeIds).toEqual(["orig"]);
    expect(opened.nextRoutes.some((route) => route.kind === "source")).toBe(true);
    expect(opened.nextRoutes.some((route) => route.kind === "fallback")).toBe(true);
  });

  it("advertises a document hub as the original record", async () => {
    const lab = new RawContextLab({
      pageSize: 1,
      hopLimit: 8,
      judge: { async judge() { return []; } },
    });
    const saved = await lab.ingest({
      personId: "p1",
      text: "page one of the letter",
      sourceType: "pdf_extract",
      capturedAt: "2024-03-01T00:00:00.000Z",
      lineageId: "letter",
      independence: "source_family",
      sourceArrival: "imported",
      idempotencyKey: "letter-1",
      documentId: "letter",
    });
    const opened = lab.explore({
      personId: "p1",
      purpose: "look",
      anchorId: saved.eventId,
      holdAtAnchor: true,
    });
    const source = lab.localRoutes(opened.routeHandle ?? "").find((route) => route.kind === "source");
    expect(source?.nodeIds[0]).toMatch(/^hub_p1_letter$/);
  });

  it("stops when further neighbors would only repeat the same lineage", () => {
    const lab = new RawContextLab({ pageSize: 5, hopLimit: 10 });
    for (const id of ["a", "b", "c", "d"]) {
      lab.addFixture({ ...event(id, `${id} note`), lineageId: "same-family" });
    }
    lab.linkStructural("a", "b");
    lab.linkStructural("a", "c");
    lab.linkStructural("a", "d");
    const response = lab.explore({ personId: "p1", purpose: "nav", anchorId: "a" });
    expect(response.terminalReason).toBe("insufficient_independent_evidence");
    expect(response.detail.toLowerCase()).not.toContain("no relevant context");
    expect(response.routeHandle).toBeNull();
  });

  it("keeps a record-kind filter on the current note", () => {
    const lab = new RawContextLab({ pageSize: 5, hopLimit: 8 });
    lab.addFixture(event("a", "alpha"));
    lab.addFixture(event("b", "beta"));
    lab.addFixture(event("c", "gamma"));
    lab.addFixture(event("d", "delta"));
    lab.linkStructural("a", "b");
    lab.linkStructural("a", "c");
    lab.linkStructural("a", "d");
    const opened = lab.explore({ personId: "p1", purpose: "look", anchorId: "a", holdAtAnchor: true });
    const onlyNotes = lab.localRoutes(opened.routeHandle ?? "").find((route) => route.kind === "facet");
    expect(onlyNotes?.label).toBe("Only notes");
    expect(onlyNotes?.nodeIds).toEqual(["b", "c", "d"]);
    const filtered = lab.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: opened.routeHandle ?? "",
      routeId: onlyNotes?.routeId,
      operation: "continue",
    });
    expect(filtered.routeHandle).toBe(opened.routeHandle);
    expect(filtered.items).toEqual([]);
    expect(lab.localOverlay(filtered.routeHandle ?? "")?.visited).toEqual(["a"]);
    const opens = filtered.nextRoutes.filter((route) => route.kind === "neighbour").map((route) => route.label);
    expect(opens).toEqual(["Open b", "Open c", "Open d"]);
  });
});
