import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ThreadSummary } from "@/lib/types";
import { WorkspaceHome } from "./WorkspaceHome";

vi.mock("next/navigation", () => ({ usePathname: () => "/workspace" }));

function thread(over: Partial<ThreadSummary>): ThreadSummary {
  return {
    id: "t",
    title: "T",
    status: "active",
    rawStatus: "active_unresolved",
    started: "Started May 1",
    updated: "Updated May 2",
    createdAt: "2026-05-01T00:00:00Z",
    updatedAt: "2026-05-02T00:00:00Z",
    ...over,
  };
}

const threads: ThreadSummary[] = [
  thread({ id: "1", title: "Older thread", status: "active", updatedAt: "2026-01-01T00:00:00Z" }),
  thread({ id: "2", title: "Newer thread", status: "resolved", updatedAt: "2026-06-01T00:00:00Z" }),
];

describe("WorkspaceHome", () => {
  it("cycles the sort order and reorders threads", () => {
    render(<WorkspaceHome threads={threads} pendingCount={0} />);

    const titles = () =>
      screen.getAllByRole("heading", { level: 3 }).map((n) => n.textContent);
    // Default: recently updated first.
    expect(titles()[0]).toMatch(/newer/i);

    fireEvent.click(screen.getByRole("button", { name: /sort:/i }));
    // Oldest first now.
    expect(titles()[0]).toMatch(/older/i);
  });

  it("hides a status via the filters menu", () => {
    render(<WorkspaceHome threads={threads} pendingCount={0} />);
    expect(screen.getByText("Newer thread")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /filters/i }));
    fireEvent.click(screen.getByRole("menuitemcheckbox", { name: /resolved/i }));

    expect(screen.queryByText("Newer thread")).not.toBeInTheDocument();
    expect(screen.getByText("Older thread")).toBeInTheDocument();
  });
});
