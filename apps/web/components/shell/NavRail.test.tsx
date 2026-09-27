import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NavRail } from "./NavRail";

vi.mock("next/navigation", () => ({
  usePathname: () => "/memory",
}));

vi.mock("./WorkspaceSwitcher", () => ({
  WorkspaceSwitcher: () => <div data-testid="workspace-switcher" />,
}));

describe("NavRail", () => {
  it("lists the five primary destinations in the Primary nav", () => {
    render(<NavRail onCapture={() => {}} />);
    const primary = screen.getByRole("navigation", { name: "Primary" });
    const labels = within(primary)
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(labels).toEqual(["Home", "Threads", "Capture", "Packets", "Memory"]);
  });

  it("keeps Results, Documents and Appointments as secondary items", () => {
    render(<NavRail onCapture={() => {}} />);
    const more = screen.getByRole("navigation", { name: "More" });
    expect(within(more).getByRole("link", { name: "Results" })).toHaveAttribute("href", "/results");
    expect(within(more).getByRole("link", { name: "Documents" })).toHaveAttribute("href", "/documents");
    expect(within(more).getByRole("link", { name: "Appointments" })).toHaveAttribute(
      "href",
      "/appointments",
    );
  });

  it("marks the current destination and opens capture from the rail", () => {
    const onCapture = vi.fn();
    render(<NavRail onCapture={onCapture} />);
    expect(screen.getByRole("link", { name: "Memory" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: "Capture" }));
    expect(onCapture).toHaveBeenCalledTimes(1);
  });

  it("toggles the mobile More panel", () => {
    render(<NavRail onCapture={() => {}} />);
    const toggle = screen.getByRole("button", { name: "More" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });
});
