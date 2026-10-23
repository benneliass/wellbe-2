import { describe, expect, it } from "vitest";
import {
  boundForwardActions,
  forwardItems,
  retainsSession,
  selectIssuedActions,
  truncatePath,
  type IssuedKind,
  type TerminalReason,
} from "../src/routing/session-policy.js";

const CLOSED: TerminalReason[] = [
  "policy_blocked",
  "authorization_changed",
  "stale_snapshot",
  "dependency_unavailable",
  "budget_exhausted",
  "insufficient_independent_evidence",
  "approximate_frontier_exhausted",
];

describe("session retention", () => {
  it("keeps a supported leaf inspectable and rewindable", () => {
    expect(retainsSession("supported_leaf")).toBe(true);
  });

  it("releases policy, authorization, snapshot, and dependency terminals", () => {
    const reasons: TerminalReason[] = [
      "policy_blocked",
      "authorization_changed",
      "stale_snapshot",
      "dependency_unavailable",
    ];
    for (const reason of reasons) expect(retainsSession(reason)).toBe(false);
  });

  it("releases budget exhaustion and insufficient independent evidence", () => {
    expect(retainsSession("budget_exhausted")).toBe(false);
    expect(retainsSession("insufficient_independent_evidence")).toBe(false);
  });

  it("keeps a null terminal while the walk can continue", () => {
    expect(retainsSession(null)).toBe(true);
  });

  it("releases an exhausted approximate frontier", () => {
    expect(retainsSession("approximate_frontier_exhausted")).toBe(false);
  });

  it("releases every terminal other than a supported leaf", () => {
    for (const reason of CLOSED) expect(retainsSession(reason)).toBe(false);
  });
});

describe("rewind", () => {
  it("cuts the path so the target is the tip and drops later nodes", () => {
    const visited = ["anchor", "mid", "later", "end"];
    expect(truncatePath(visited, "mid")).toEqual({ visited: ["anchor", "mid"] });
    expect(visited).toEqual(["anchor", "mid", "later", "end"]);
  });

  it("returns the same path when the target is already the tip", () => {
    const visited = ["anchor", "mid", "tip"];
    const once = truncatePath(visited, "tip");
    expect(once).toEqual({ visited: ["anchor", "mid", "tip"] });
    if ("error" in once) throw new Error("expected a path");
    expect(truncatePath(once.visited, "tip")).toEqual({ visited: ["anchor", "mid", "tip"] });
    expect(truncatePath(["a", "b", "a"], "a")).toEqual({ visited: ["a", "b", "a"] });
  });

  it("returns rewind_target when the target is off the path", () => {
    const visited = ["anchor", "mid"];
    expect(truncatePath(visited, "other")).toEqual({ error: "rewind_target" });
    expect(visited).toEqual(["anchor", "mid"]);
    expect(truncatePath([], "anchor")).toEqual({ error: "rewind_target" });
  });
});

describe("forward frontier", () => {
  it("returns only items expanded from the tip", () => {
    const items = [
      { nodeId: "from-tip", fromId: "tip" },
      { nodeId: "sibling", fromId: "earlier" },
      { nodeId: "also-from-tip", fromId: "tip" },
    ];
    expect(forwardItems(items, "tip")).toEqual([
      { nodeId: "from-tip", fromId: "tip" },
      { nodeId: "also-from-tip", fromId: "tip" },
    ]);
    expect(items).toHaveLength(3);
  });

  it("drops siblings expanded from an earlier node after the tip moves", () => {
    const items = [
      { nodeId: "old-child", fromId: "earlier" },
      { nodeId: "old-sibling", fromId: "earlier" },
    ];
    expect(forwardItems(items, "tip")).toEqual([]);
  });
});

describe("issued actions", () => {
  it("clamps open-node advertisements to at most three", () => {
    expect(boundForwardActions(0)).toBe(0);
    expect(boundForwardActions(1)).toBe(1);
    expect(boundForwardActions(3)).toBe(3);
    expect(boundForwardActions(4)).toBe(3);
    expect(boundForwardActions(12)).toBe(3);
  });

  it("keeps at most three neighbour actions", () => {
    const actions = [
      { kind: "neighbour" as const, id: "n1" },
      { kind: "neighbour" as const, id: "n2" },
      { kind: "facet" as const, id: "facet" },
      { kind: "neighbour" as const, id: "n3" },
      { kind: "neighbour" as const, id: "n4" },
      { kind: "temporal" as const, id: "time" },
      { kind: "fallback" as const, id: "stop" },
    ];
    const issued = selectIssuedActions(actions);
    expect(issued.filter((action) => action.kind === "neighbour").map((action) => action.id)).toEqual([
      "n1",
      "n2",
      "n3",
    ]);
    expect(issued.map((action) => action.id)).toEqual(["n1", "n2", "facet", "n3", "time", "stop"]);
    expect(issued[0]).toBe(actions[0]);
    expect(actions).toHaveLength(7);
  });

  it("keeps a fallback and stays within seven actions", () => {
    const kinds: IssuedKind[] = [
      "facet",
      "facet",
      "temporal",
      "temporal",
      "source",
      "source",
      "facet",
      "fallback",
    ];
    const actions = kinds.map((kind, index) => ({ kind, id: index }));
    const issued = selectIssuedActions(actions);
    expect(issued).toHaveLength(7);
    expect(issued.map((action) => action.kind)).toEqual([
      "facet",
      "facet",
      "temporal",
      "temporal",
      "source",
      "source",
      "fallback",
    ]);
    expect(issued.some((action) => action.kind === "fallback")).toBe(true);
  });

  it("stays between three and seven actions when enough candidates exist", () => {
    const actions = [
      { kind: "neighbour" as const },
      { kind: "neighbour" as const },
      { kind: "neighbour" as const },
      { kind: "neighbour" as const },
      { kind: "facet" as const },
      { kind: "temporal" as const },
      { kind: "source" as const },
      { kind: "facet" as const },
      { kind: "fallback" as const },
    ];
    const issued = selectIssuedActions(actions);
    expect(issued.filter((action) => action.kind === "neighbour")).toHaveLength(3);
    expect(issued.length).toBeGreaterThanOrEqual(3);
    expect(issued.length).toBeLessThanOrEqual(7);
    expect(issued.some((action) => action.kind === "fallback")).toBe(true);
    expect(issued.map((action) => action.kind)).toEqual([
      "neighbour",
      "neighbour",
      "neighbour",
      "facet",
      "temporal",
      "source",
      "fallback",
    ]);
  });

  it("leaves a short list unchanged when fewer than three candidates exist", () => {
    const actions = [{ kind: "neighbour" as const }, { kind: "fallback" as const }];
    expect(selectIssuedActions(actions)).toEqual(actions);
  });
});
