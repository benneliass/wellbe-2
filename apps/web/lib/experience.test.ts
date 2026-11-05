import { afterEach, describe, expect, it, vi } from "vitest";
import {
  enterTechnicalWorkspace,
  guidedExperienceEnabled,
  skipGuidedExperience,
} from "./experience";
import { clearSession, getSession } from "./session";

const PATIENT = "de7a0000-0000-4000-8000-000000000001";

describe("guided experience", () => {
  afterEach(() => {
    clearSession();
    delete window.__WELLBE_AUTH_CONFIG__;
    vi.unstubAllEnvs();
  });

  it("stays off unless the flag is on, 1, or true", () => {
    expect(guidedExperienceEnabled()).toBe(false);
    for (const value of ["", "off", "0", "false", "no"]) {
      vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", value);
      expect(guidedExperienceEnabled()).toBe(false);
    }
    for (const value of ["on", "ON", "1", "true"]) {
      vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", value);
      expect(guidedExperienceEnabled()).toBe(true);
    }
  });

  it("skips the wizard only for a configured dev workspace", () => {
    expect(skipGuidedExperience()).toBe(false);

    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    expect(skipGuidedExperience()).toBe(true);

    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "on");
    expect(skipGuidedExperience()).toBe(false);
  });

  it("does not skip OIDC sign-in", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    window.__WELLBE_AUTH_CONFIG__ = {
      mode: "oidc",
      issuer: "https://auth.example",
      clientId: "web",
      demo: false,
    };
    expect(skipGuidedExperience()).toBe(false);
    expect(enterTechnicalWorkspace()).toBeNull();
    expect(getSession()).toBeNull();
  });

  it("enters the seeded workspace when the guided flow is off", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    const session = enterTechnicalWorkspace();
    expect(session?.patientId).toBe(PATIENT);
    expect(session?.onboarded).toBe(true);
    expect(getSession()?.displayName).toBe("Dev workspace");
  });
});
