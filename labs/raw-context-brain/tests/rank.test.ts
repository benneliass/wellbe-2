import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { applyHysteresis, compareRank } from "../src/rank.js";
import { sha256 } from "../src/text.js";
import type { Rankable } from "../src/types.js";

function rank(partial: Partial<Rankable> & Pick<Rankable, "id">): Rankable {
  return {
    authorized: 1,
    provenance: 1,
    relevance: 0,
    novelty: 0,
    inverseDegree: 0,
    inverseHop: 0,
    ...partial,
  };
}

describe("rank and digest", () => {
  it("hashes with sha256", () => {
    expect(sha256("wellbe")).toBe(createHash("sha256").update("wellbe").digest("hex"));
  });

  it("orders authorization before relevance before degree", () => {
    const blocked = rank({ id: "b", authorized: 0, relevance: 1 });
    const allowed = rank({ id: "a", authorized: 1, relevance: 0.1 });
    expect(compareRank(allowed, blocked)).toBeLessThan(0);
  });

  it("lets a closer match beat a more specific note", () => {
    const hub = rank({ id: "hub", relevance: 0.9, inverseDegree: 0.1 });
    const specific = rank({ id: "leaf", relevance: 0.8, inverseDegree: 1 });
    expect(compareRank(hub, specific)).toBeLessThan(0);
  });

  it("uses degree only when the match ties", () => {
    const hub = rank({ id: "hub", relevance: 0.8, inverseDegree: 0.1 });
    const specific = rank({ id: "leaf", relevance: 0.8, inverseDegree: 1 });
    expect(compareRank(specific, hub)).toBeLessThan(0);
  });

  it("keeps a nearly equal previous route", () => {
    const ranked = [
      { id: "new", relevance: 0.52 },
      { id: "old", relevance: 0.5 },
    ];
    expect(applyHysteresis(ranked, "old").ranked.map((item) => item.id)).toEqual(["old", "new"]);
    expect(applyHysteresis(ranked, "old").heldPrevious).toBe(true);
  });

  it("does not hold a previous note that loses on a higher key", () => {
    const ranked = [
      rank({ id: "new", provenance: 2, relevance: 0.52 }),
      rank({ id: "old", provenance: 0, relevance: 0.5 }),
    ];
    const held = applyHysteresis(ranked, "old");
    expect(held.ranked.map((item) => item.id)).toEqual(["new", "old"]);
    expect(held.heldPrevious).toBe(false);
  });
});
