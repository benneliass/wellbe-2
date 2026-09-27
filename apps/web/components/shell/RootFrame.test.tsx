import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RootFrame } from "./RootFrame";

let session: { onboarded: boolean } | null = null;

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

vi.mock("@/lib/useSession", () => ({
  useSession: () => session,
}));

describe("RootFrame", () => {
  it("gives the front door a main landmark without app navigation", () => {
    session = null;
    render(<RootFrame>door</RootFrame>);
    expect(screen.getByRole("main")).toHaveTextContent("door");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("adds the primary nav around the launcher once onboarded", () => {
    session = { onboarded: true };
    render(<RootFrame>launcher</RootFrame>);
    expect(screen.getByRole("main")).toHaveTextContent("launcher");
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
  });
});
