import { describe, expect, it } from "vitest";
import { LAUNCH_ACTIONS } from "./meta";

describe("LAUNCH_ACTIONS routing (T0.1 regression guard)", () => {
  it("routes the triage pill to /triage, not the old /threads/labs mis-wire", () => {
    const triage = LAUNCH_ACTIONS.find((a) => a.id === "triage");
    expect(triage?.href).toBe("/triage");
  });

  it("leaves the log pill without an href so it opens the capture modal", () => {
    const log = LAUNCH_ACTIONS.find((a) => a.id === "log");
    expect(log?.href).toBeUndefined();
  });

  it("gives every non-log action an explicit href (no silent /workspace fall-through)", () => {
    for (const action of LAUNCH_ACTIONS) {
      if (action.id === "log") continue;
      expect(action.href, `${action.id} should have an href`).toMatch(/^\//);
    }
  });

  it("maps each action to its own distinct destination", () => {
    const hrefs = LAUNCH_ACTIONS.map((a) => a.href).filter(Boolean);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
});
