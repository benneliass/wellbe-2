import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearSession,
  getSession,
  hasSession,
  signInDev,
  signInNewUser,
  updateSession,
} from "./session";

describe("session", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("has no session by default — there is no auto-login", () => {
    expect(getSession()).toBeNull();
    expect(hasSession()).toBe(false);
  });

  it("signInNewUser starts a non-onboarded identity with no patient id yet", () => {
    const s = signInNewUser();
    expect(s.onboarded).toBe(false);
    expect(s.patientId).toBeNull();
    expect(s.issuer).toBe("dev-local");
    expect(s.subject).toMatch(/^user-/);
    expect(getSession()?.subject).toBe(s.subject);
  });

  it("signInDev signs into the seeded, pre-onboarded dev identity", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", "de7a0000-0000-4000-8000-000000000001");
    const s = signInDev();
    expect(s).not.toBeNull();
    expect(s?.onboarded).toBe(true);
    expect(s?.patientId).toBe("de7a0000-0000-4000-8000-000000000001");
    expect(s?.displayName).toBe("Dev workspace");
  });

  it("signInDev is unavailable when no dev patient id is configured", () => {
    expect(signInDev()).toBeNull();
    expect(hasSession()).toBe(false);
  });

  it("updateSession patches the active session and clearSession ends it", () => {
    signInNewUser();
    const next = updateSession({ patientId: "p1", onboarded: true });
    expect(next?.patientId).toBe("p1");
    expect(next?.onboarded).toBe(true);
    clearSession();
    expect(getSession()).toBeNull();
  });
});
