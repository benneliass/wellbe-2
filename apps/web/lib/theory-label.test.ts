import { describe, expect, it } from "vitest";
import { cleanTheoryLabel } from "./theory-label";

describe("cleanTheoryLabel", () => {
  it("strips a stored question frame, even when repeated", () => {
    expect(cleanTheoryLabel("Could my data be related to: screen time?")).toBe("screen time");
    expect(
      cleanTheoryLabel("Could my data be related to: Could my data be related to: screen time?"),
    ).toBe("screen time");
  });

  it("leaves the user's own phrasing alone", () => {
    expect(cleanTheoryLabel("Could screen time relate to my headaches?")).toBe(
      "Could screen time relate to my headaches?",
    );
    expect(cleanTheoryLabel("Could my data be related tomatoes?")).toBe(
      "Could my data be related tomatoes?",
    );
  });
});
