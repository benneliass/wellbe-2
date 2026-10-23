import { describe, expect, it } from "vitest";
import { MemoryGraphStore } from "../src/persist/memory-store.js";
import { MemorySessionStore } from "../src/persist/session-store.js";
import { RawContextLab } from "../src/router.js";
import type { JudgeDecision, JudgeRequest, VaultEvent } from "../src/types.js";

function fixture(partial: Partial<VaultEvent> & Pick<VaultEvent, "id" | "text">): VaultEvent {
  return {
    personId: "p1",
    capturedAt: "2024-01-01T00:00:00.000Z",
    sourceType: "note",
    contentHash: "hash",
    lineageId: partial.id,
    documentId: null,
    ...partial,
  };
}

describe("finished lab contracts", () => {
  it("keeps an exact leaf rewindable on the same handle", () => {
    const lab = new RawContextLab();
    lab.addFixture(fixture({ id: "a", text: "alpha fever" }));
    lab.addFixture(fixture({ id: "b", text: "beta crp" }));
    lab.linkStructural("a", "b");
    const opened = lab.explore({ personId: "p1", purpose: "look", anchorId: "a", holdAtAnchor: true });
    const rewound = lab.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: opened.routeHandle ?? "",
      operation: "rewind",
      rewindToId: "a",
    });
    expect(rewound.routeHandle).toBe(opened.routeHandle);
    expect(lab.localOverlay(rewound.routeHandle ?? "")?.visited).toEqual(["a"]);
    const alone = new RawContextLab();
    alone.addFixture(fixture({ id: "only", text: "lentil soup" }));
    const leaf = alone.explore({ personId: "p1", purpose: "look", anchorId: "only" });
    expect(leaf.terminalReason).toBe("supported_leaf");
    expect(leaf.routeHandle).toBeTruthy();
    const back = alone.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: leaf.routeHandle ?? "",
      operation: "rewind",
      rewindToId: "only",
    });
    expect(back.routeHandle).toBe(leaf.routeHandle);
  });

  it("records route-set history and prune rows on the save result", async () => {
    const lab = new RawContextLab({ maxCandidates: 1 });
    lab.addFixture(fixture({ id: "early", text: "alpha fever", capturedAt: "2020-01-01T00:00:00.000Z" }));
    lab.addFixture(fixture({ id: "late", text: "alpha fever later", capturedAt: "2025-01-01T00:00:00.000Z" }));
    const saved = await lab.ingest({
      personId: "p1",
      text: "alpha fever today",
      sourceType: "note",
      capturedAt: "2024-01-01T00:00:00.000Z",
      lineageId: "fever",
      idempotencyKey: "save-1",
    });
    expect(saved.routeRevision).toBeGreaterThan(0);
    expect(saved.pruned.length).toBeGreaterThan(0);
    const again = await lab.ingest({
      personId: "p1",
      text: "alpha fever tomorrow",
      sourceType: "note",
      capturedAt: "2024-02-01T00:00:00.000Z",
      lineageId: "fever-2",
      idempotencyKey: "save-2",
    });
    expect(lab.routeHistory("p1")).toEqual([saved.routeRevision, again.routeRevision]);
  });

  it("judges a closer neighbor after a non-link", async () => {
    const requests: JudgeRequest[] = [];
    const lab = new RawContextLab({
      judge: {
        async judge(request) {
          requests.push(request);
          if (requests.length === 1) {
            return request.candidates.map((candidate) => ({
              handle: candidate.handle,
              judgment: "no_link" as const,
              reasonCode: "recorded_association",
              confidence: 0.2,
            }));
          }
          return request.candidates.map((candidate): JudgeDecision => ({
            handle: candidate.handle,
            judgment: "link",
            reasonCode: "recorded_association",
            confidence: 0.6,
          }));
        },
      },
    });
    lab.addFixture(fixture({ id: "weak", text: "alpha", capturedAt: "2020-01-01T00:00:00.000Z" }));
    lab.addFixture(fixture({ id: "filler", text: "marker", capturedAt: "2025-01-01T00:00:00.000Z" }));
    lab.addFixture(fixture({ id: "closer", text: "alpha fever marker", capturedAt: "2024-06-01T00:00:00.000Z" }));
    lab.linkStructural("weak", "closer");
    const saved = await lab.ingest({
      personId: "p1",
      text: "alpha fever marker",
      sourceType: "note",
      capturedAt: "2024-06-01T00:00:00.000Z",
      lineageId: "new",
      idempotencyKey: "refer",
    });
    expect(requests.length).toBe(2);
    expect(saved.judgments.some((row) => row.judgment === "link")).toBe(true);
  });

  it("stops a judge that is past its deadline", async () => {
    let clock = 0;
    const lab = new RawContextLab({
      now: () => clock,
      judgeDeadlineMs: 5,
      judge: {
        async judge() {
          clock = 10;
          throw new Error("slow");
        },
      },
    });
    const saved = await lab.ingest({
      personId: "p1",
      text: "a lone note",
      sourceType: "note",
      capturedAt: "2024-01-01T00:00:00.000Z",
      lineageId: "lone",
      idempotencyKey: "deadline",
    });
    expect(saved.terminalReason).toBe("dependency_unavailable");
  });

  it("restores the graph in a second lab and expires the walk", () => {
    const graphStore = new MemoryGraphStore();
    const sessionStore = new MemorySessionStore();
    const first = new RawContextLab({ graphStore, sessionStore });
    first.addFixture(fixture({ id: "a", text: "alpha fever" }));
    first.addFixture(fixture({ id: "b", text: "beta crp" }));
    const link = first.linkStructural("a", "b");
    const opened = first.explore({ personId: "p1", purpose: "look", anchorId: "a" });
    const second = new RawContextLab({ graphStore, sessionStore });
    expect(second.vault.get("a")?.text).toBe("alpha fever");
    expect(second.projection.edgeBetween("a", "b")?.adId).toBe(link.id);
    expect(second.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: opened.routeHandle ?? "",
      operation: "continue",
    }).terminalReason).not.toBe("policy_blocked");
    second.expireExploration();
    expect(second.explore({
      personId: "p1",
      purpose: "look",
      routeHandle: opened.routeHandle ?? "",
    }).terminalReason).toBe("policy_blocked");
    expect(second.vault.get("a")?.text).toBe("alpha fever");
  });

  it("rejects a same-record link that is not hub membership on rebuild", () => {
    const lab = new RawContextLab();
    lab.addFixture(fixture({ id: "a", text: "alpha" }));
    lab.addFixture(fixture({ id: "b", text: "beta" }));
    const ordinary = lab.linkStructural("a", "b");
    expect(ordinary.relation).toBe("possible_semantic_association");
    lab.finishRebuild();
    lab.linkStructural("a", "b", "membership");
    expect(() => lab.finishRebuild()).toThrow(/source-group membership/);
  });
});
