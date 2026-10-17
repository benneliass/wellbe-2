import { describe, expect, it } from "vitest";
import { memoryKeyword } from "../src/viz/keyword.js";

describe("memory keyword", () => {
  it("picks a short word from a sentence", () => {
    expect(memoryKeyword("Recurrent fever and migratory asymmetric joint symptoms began to drive repeated evaluation")).toBe("Fever");
    expect(memoryKeyword("Loose stools for many years, described as beginning in childhood.")).toBe("Stools");
  });

  it("keeps a lab name before the colon", () => {
    expect(memoryKeyword("ESR: 52 mm/h (reference <15)")).toBe("ESR");
    expect(memoryKeyword("CRP: 50 mg/dL (reference <0.3)")).toBe("CRP");
  });

  it("uses the topic in a labeled line", () => {
    expect(memoryKeyword("Fever episodes: Fever associated with joint flares.")).toBe("Fever");
    expect(memoryKeyword("Joint episodes: Recurrent migratory, asymmetrical polyarticular inflammatory pain")).toBe("Joint");
  });
});