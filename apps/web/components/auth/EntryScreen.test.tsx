import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getSession } from "@/lib/session";
import { EntryScreen } from "./EntryScreen";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

describe("EntryScreen", () => {
  beforeEach(() => {
    push.mockReset();
    window.localStorage.clear();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("always offers a new-user path and never auto-enters", () => {
    render(<EntryScreen />);
    expect(screen.getByText("New to WellBe")).toBeInTheDocument();
    // No session is established just by viewing the front door.
    expect(getSession()).toBeNull();
  });

  it("starting as a new user signs in unonboarded and routes to onboarding", () => {
    render(<EntryScreen />);
    fireEvent.click(screen.getByText("New to WellBe"));
    expect(push).toHaveBeenCalledWith("/onboarding");
    const session = getSession();
    expect(session?.onboarded).toBe(false);
    expect(session?.patientId).toBeNull();
  });

  it("shows the Dev workspace as an explicit option only when configured", () => {
    const { rerender } = render(<EntryScreen />);
    expect(screen.queryByText("Dev workspace")).not.toBeInTheDocument();

    vi.stubEnv("NEXT_PUBLIC_WELLBE_DEV_PATIENT_ID", "de7a0000-0000-4000-8000-000000000001");
    rerender(<EntryScreen />);
    expect(screen.getByText("Dev workspace")).toBeInTheDocument();
  });
});
