import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearSession } from "@/lib/session";
import { OnboardingFlow } from "./OnboardingFlow";

const replace = vi.fn();
const post = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ POST: post }),
}));

const PATIENT = "de7a0000-0000-4000-8000-000000000001";

describe("OnboardingFlow", () => {
  beforeEach(() => {
    replace.mockReset();
    post.mockReset();
    clearSession();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    clearSession();
  });

  it("leaves the wizard and does not start onboarding when the guided experience is off", async () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "off");
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    render(<OnboardingFlow />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(screen.queryByRole("heading", { name: /Welcome to WellBe/ })).toBeNull();
    expect(post).not.toHaveBeenCalled();
  });

  it("shows the welcome step when the guided experience is on", async () => {
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
    post.mockResolvedValue({ data: { core_consent: [], status: "pending" } });
    render(<OnboardingFlow />);
    expect(await screen.findByRole("heading", { name: /Welcome to WellBe/ })).toBeInTheDocument();
  });
});
