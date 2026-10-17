import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { applyHysteresis, compareRank, degreeNormalized } from "../src/rank.js";
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

  it("degree-normalizes so a similar hub loses to a specific note", () => {
    const hub = degreeNormalized(0.9, 100);
    const specific = degreeNormalized(0.8, 1);
    expect(specific).toBeGreaterThan(hub);
  });

  it("keeps a nearly equal previous route", () => {
    const ranked = [
      { id: "new", relevance: 0.52 },
      { id: "old", relevance: 0.5 },
    ];
    expect(applyHysteresis(ranked, "old").map((item) => item.id)).toEqual(["old", "new"]);
  });
});
