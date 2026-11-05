import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearSession, getSession } from "@/lib/session";
import { RequireSession } from "./RequireSession";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
}));

const PATIENT = "de7a0000-0000-4000-8000-000000000001";

describe("RequireSession", () => {
  beforeEach(() => {
    replace.mockReset();
    clearSession();
    delete window.__WELLBE_AUTH_CONFIG__;
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    clearSession();
  });

  it("opens the workspace without a prior sign-in when the guided experience is off", async () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "off");
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    render(
      <RequireSession>
        <p>workspace body</p>
      </RequireSession>,
    );
    expect(await screen.findByText("workspace body")).toBeInTheDocument();
    expect(getSession()?.onboarded).toBe(true);
    expect(replace).not.toHaveBeenCalled();
  });

  it("sends a missing session to the front door when the guided experience is on", async () => {
    vi.stubEnv("NEXT_PUBLIC_WELLBE_EXPERIENCE", "on");
    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", PATIENT);
    render(
      <RequireSession>
        <p>workspace body</p>
      </RequireSession>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(screen.queryByText("workspace body")).toBeNull();
  });
});
