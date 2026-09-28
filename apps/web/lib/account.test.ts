import { describe, expect, it } from "vitest";
import { toInitials } from "./account";

describe("toInitials", () => {
  it("uses the first letters of up to two name parts", () => {
    expect(toInitials("Ben Elias")).toBe("BE");
    expect(toInitials("Demo")).toBe("D");
  });

  it("works from an email when there is no name", () => {
    expect(toInitials("ben7423@gmail.com")).toBe("B");
  });

  it("falls back for an empty name", () => {
    expect(toInitials("  ")).toBe("Y");
  });
});
