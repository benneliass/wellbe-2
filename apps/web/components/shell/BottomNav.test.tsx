import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BottomNav } from "./BottomNav";

let pathname = "/";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

describe("BottomNav", () => {
  beforeEach(() => {
    pathname = "/";
  });

  it("is a labelled nav with exactly the five primary destinations in order", () => {
    render(<BottomNav onCapture={() => {}} />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    const labels = within(nav)
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(labels).toEqual(["Home", "Threads", "Capture", "Packets", "Memory"]);
  });

  it("links destinations to their routes, with Packets going to /prepare", () => {
    render(<BottomNav onCapture={() => {}} />);
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Threads" })).toHaveAttribute("href", "/workspace");
    expect(screen.getByRole("link", { name: "Packets" })).toHaveAttribute("href", "/prepare");
    expect(screen.getByRole("link", { name: "Memory" })).toHaveAttribute("href", "/memory");
  });

  it("marks only the current destination with aria-current", () => {
    pathname = "/prepare";
    render(<BottomNav onCapture={() => {}} />);
    expect(screen.getByRole("link", { name: "Packets" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
  });

  it("treats thread detail routes as the Threads destination", () => {
    pathname = "/threads/abc";
    render(<BottomNav onCapture={() => {}} />);
    expect(screen.getByRole("link", { name: "Threads" })).toHaveAttribute("aria-current", "page");
  });

  it("opens capture instead of navigating", () => {
    const onCapture = vi.fn();
    render(<BottomNav onCapture={onCapture} />);
    const capture = screen.getByRole("button", { name: "Capture" });
    expect(capture).toHaveAttribute("aria-haspopup", "dialog");
    fireEvent.click(capture);
    expect(onCapture).toHaveBeenCalledTimes(1);
  });
});
