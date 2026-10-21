import { describe, expect, it } from "vitest";
import { mapRelation } from "../src/relation.js";

describe("relation names", () => {
  it("keeps a possible conflict distinct from a possible association", () => {
    expect(mapRelation("model", "possible_conflict")).toBe("possible_inconsistency");
    expect(mapRelation("model", "shared_context")).toBe("possible_semantic_association");
    expect(mapRelation("policy", "derived_or_copied")).toBe("derived_or_copied");
  });
});
