import { describe, expect, it } from "vitest";
import {
  associationPhrase,
  isClinicalReason,
  nextConfidence,
  readSuggestion,
} from "../src/confidence.js";
import type { Judgment, Origin } from "../src/types.js";

describe("suggestion readings", () => {
  it("treats uncertain as an abstain that adds nothing and is not a no_link", () => {
    const reading = readSuggestion("uncertain");
    expect(reading).toEqual({ kind: "uncertain", addsSuggestion: false });
    expect(reading.kind).not.toBe("no_link");
  });

  it("keeps link and no_link as suggestions", () => {
    expect(readSuggestion("link")).toEqual({ kind: "link", addsSuggestion: true });
    expect(readSuggestion("no_link")).toEqual({ kind: "no_link", addsSuggestion: true });
  });

  it("does not carry a flag that removes a kept link", () => {
    const judgments: Judgment[] = ["link", "no_link", "uncertain"];
    for (const judgment of judgments) {
      expect(Object.keys(readSuggestion(judgment)).sort()).toEqual(["addsSuggestion", "kind"]);
    }
  });
});

describe("next confidence", () => {
  const same = {
    existingLineages: ["line-a", "line-b"],
    evidenceLineages: ["line-b", "line-a"],
  };

  it("returns a first model proposal when no edge exists yet", () => {
    expect(
      nextConfidence({
        origin: "model",
        proposed: 0.95,
        existingConfidence: null,
        existingLineages: [],
        evidenceLineages: ["line-a"],
      }),
    ).toBe(0.95);
  });

  it("does not let the same evidence set raise confidence", () => {
    expect(
      nextConfidence({
        origin: "model",
        proposed: 0.95,
        existingConfidence: 0.4,
        ...same,
      }),
    ).toBe(0.4);
  });

  it("allows the same evidence set to lower confidence", () => {
    expect(
      nextConfidence({
        origin: "model",
        proposed: 0.2,
        existingConfidence: 0.4,
        ...same,
      }),
    ).toBe(0.2);
  });

  it("lets a new independent lineage move confidence up or down", () => {
    expect(
      nextConfidence({
        origin: "model",
        proposed: 0.95,
        existingConfidence: 0.4,
        existingLineages: ["line-a", "line-b"],
        evidenceLineages: ["line-a", "line-c"],
      }),
    ).toBe(0.95);
    expect(
      nextConfidence({
        origin: "model",
        proposed: 0.15,
        existingConfidence: 0.4,
        existingLineages: ["line-a"],
        evidenceLineages: ["line-a", "line-c"],
      }),
    ).toBe(0.15);
  });

  it("returns a user correction unchanged", () => {
    const origins: Origin[] = ["user_correction", "policy"];
    for (const origin of origins) {
      expect(
        nextConfidence({
          origin,
          proposed: 0.95,
          existingConfidence: 0.4,
          ...same,
        }),
      ).toBe(0.95);
      expect(
        nextConfidence({
          origin,
          proposed: 0.1,
          existingConfidence: 0.9,
          ...same,
        }),
      ).toBe(0.1);
    }
  });

  it("returns a number rather than an edge-removal flag", () => {
    const confidence = nextConfidence({
      origin: "model",
      proposed: 0.2,
      existingConfidence: 0.4,
      existingLineages: ["line-a"],
      evidenceLineages: ["line-a"],
    });
    expect(typeof confidence).toBe("number");
  });
});

describe("wording and reason codes", () => {
  it("offers a short conditional association without clinical claims", () => {
    const phrase = associationPhrase();
    expect(phrase.endsWith(".")).toBe(true);
    expect(phrase.length).toBeLessThan(80);
    expect(phrase).toMatch(/\bmay\b/i);
    expect(phrase.toLowerCase()).not.toMatch(/diagnos|cause|severity|cancer/);
  });

  it("rejects a clinical reason code as a link reason", () => {
    expect(isClinicalReason("diagnosis of cancer")).toBe(true);
    expect(isClinicalReason("DIAGNOSIS")).toBe(true);
    expect(isClinicalReason("severity")).toBe(true);
    expect(isClinicalReason("caused by")).toBe(true);
    expect(isClinicalReason("heart disease")).toBe(true);
    expect(isClinicalReason("shared_context")).toBe(false);
    expect(isClinicalReason("insufficient_overlap")).toBe(false);
    expect(isClinicalReason("recorded_association")).toBe(false);
    expect(isClinicalReason("user_correction")).toBe(false);
    expect(isClinicalReason("possible_conflict")).toBe(false);
  });
});
