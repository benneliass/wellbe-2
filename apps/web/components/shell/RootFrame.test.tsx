import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RootFrame } from "./RootFrame";

let session: { onboarded: boolean } | null = null;

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

vi.mock("@/lib/useSession", () => ({
  useSession: () => session,
}));

vi.mock("@/components/capture/CaptureModal", () => ({
  CaptureModal: () => <div role="dialog" aria-label="Capture" />,
}));

describe("RootFrame", () => {
  it("gives the front door a main landmark without app navigation", () => {
    session = null;
    render(
      <RootFrame>door</RootFrame>,
    );
    expect(screen.getByRole("main")).toHaveTextContent("door");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("adds the mobile bottom nav once onboarded", () => {
    session = { onboarded: true };
    render(<RootFrame>launcher</RootFrame>);
    expect(screen.getByRole("main")).toHaveTextContent("launcher");
    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });

  it("adds no desktop nav beside the launcher: only the mobile bar", () => {
    session = { onboarded: true };
    render(<RootFrame>launcher</RootFrame>);
    expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Menu" })).toBeNull();
  });

  it("opens capture from the mobile bar", () => {
    session = { onboarded: true };
    render(<RootFrame>launcher</RootFrame>);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    fireEvent.click(within(nav).getByRole("button", { name: "Capture" }));
    expect(screen.getByRole("dialog", { name: "Capture" })).toBeInTheDocument();
  });
});
