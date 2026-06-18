import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ThreadSummary } from "@/lib/types";
import { SummaryStrip } from "./SummaryStrip";

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

describe("SummaryStrip", () => {
  it("derives open and attention counts from the threads", () => {
    const threads: ThreadSummary[] = [
      thread({ id: "1", status: "active" }),
      thread({ id: "2", status: "monitoring" }),
      thread({ id: "3", status: "attention" }),
      thread({ id: "4", status: "resolved" }),
    ];
    render(<SummaryStrip threads={threads} pendingCount={5} />);

    // active + monitoring + attention = 3 open
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("open threads")).toBeInTheDocument();
    // pending items surfaced as open loops
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("to follow up")).toBeInTheDocument();
  });

  it("uses singular copy for a single open thread", () => {
    render(<SummaryStrip threads={[thread({ status: "active" })]} pendingCount={0} />);
    expect(screen.getByText("open thread")).toBeInTheDocument();
  });
});
