import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RootFrame, useRootNav } from "./RootFrame";

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

/** Stands in for the launcher header, which places the root nav slot. */
function Header() {
  return <header>{useRootNav()}</header>;
}

function desktopNav() {
  return within(screen.getByRole("banner")).getByRole("navigation", { name: "Primary" });
}

describe("RootFrame", () => {
  it("gives the front door a main landmark without app navigation", () => {
    session = null;
    render(
      <RootFrame>
        <Header />
        door
      </RootFrame>,
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

  it("provides the desktop nav for the launcher header, with every destination", () => {
    session = { onboarded: true };
    render(
      <RootFrame>
        <Header />
      </RootFrame>,
    );
    const nav = desktopNav();
    for (const label of ["Home", "Threads", "Packets", "Memory"]) {
      expect(within(nav).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(within(nav).getByRole("button", { name: "Capture" })).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });

  it("toggles the compact menu and closes it on Escape", () => {
    session = { onboarded: true };
    render(
      <RootFrame>
        <Header />
      </RootFrame>,
    );
    const toggle = within(desktopNav()).getByRole("button", { name: "Menu" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(desktopNav()).toHaveAttribute("data-open", "true");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveFocus();
  });

  it("opens capture from the desktop nav and closes the menu", () => {
    session = { onboarded: true };
    render(
      <RootFrame>
        <Header />
      </RootFrame>,
    );
    const nav = desktopNav();
    fireEvent.click(within(nav).getByRole("button", { name: "Menu" }));
    fireEvent.click(within(nav).getByRole("button", { name: "Capture" }));
    expect(screen.getByRole("dialog", { name: "Capture" })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  });
});
