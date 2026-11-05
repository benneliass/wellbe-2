import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearSession, getSession } from "@/lib/session";
import { RootGate } from "./RootGate";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

vi.mock("@/components/launcher/Launcher", () => ({
  Launcher: () => <h1>What do you need today?</h1>,
}));

const PATIENT = "de7a0000-0000-4000-8000-000000000001";

describe("RootGate", () => {
  beforeEach(() => {
    replace.mockReset();
    clearSession();
    delete window.__WELLBE_AUTH_CONFIG__;
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    clearSession();
    delete window.__WELLBE_AUTH_CONFIG__;
  });

  it("opens the seeded workspace when the guided experience is off", async () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "off");
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    render(<RootGate />);
    expect(await screen.findByRole("heading", { name: /What do you need/ })).toBeInTheDocument();
    expect(screen.queryByText("New to WellBe")).toBeNull();
    expect(getSession()?.onboarded).toBe(true);
    expect(getSession()?.patientId).toBe(PATIENT);
  });

  it("keeps the front door when the guided experience is on", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "on");
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    render(<RootGate />);
    expect(screen.getByText("New to WellBe")).toBeInTheDocument();
    expect(screen.getByText("Dev workspace")).toBeInTheDocument();
    expect(getSession()).toBeNull();
  });

  it("offers Try the demo on the front door and does not auto-enter", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    window.__WELLBE_AUTH_CONFIG__ = {
      mode: "oidc",
      issuer: "https://auth.example",
      clientId: "web",
      demo: true,
    };
    render(<RootGate />);
    expect(screen.getByText("Sign in")).toBeInTheDocument();
    expect(screen.getByText("Try the demo")).toBeInTheDocument();
    expect(getSession()).toBeNull();
  });

  it("keeps OIDC sign-in when the guided experience is off", () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    window.__WELLBE_AUTH_CONFIG__ = {
      mode: "oidc",
      issuer: "https://auth.example",
      clientId: "web",
      demo: false,
    };
    render(<RootGate />);
    expect(screen.getByText("Sign in")).toBeInTheDocument();
    expect(screen.queryByText("New to WellBe")).toBeNull();
    expect(getSession()).toBeNull();
  });

  it("sends an unfinished account to onboarding when the guided experience is on", async () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "on");
    window.localStorage.setItem(
      "wellbe.session",
      JSON.stringify({
        issuer: "dev-local",
        subject: "user-1",
        patientId: null,
        actorType: "controller",
        onboarded: false,
        displayName: null,
      }),
    );
    render(<RootGate />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/onboarding"));
  });
});
