import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContextWalk } from "./ContextWalk";

const post = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ POST: post }),
}));

const opened = {
  route: "selected",
  breadcrumb: ["Note 2024-02-01"],
  hop_depth: 0,
  direct_link_count: 2,
  cycle_count: 0,
  exhaustion: "continuing",
  terminal_reason: null,
  detail: "",
  route_handle: "rh_1",
  snapshot_revision: 1,
  snapshot_digest: "d",
  next_routes: [
    { route_id: "facet-1", label: "Only notes", kind: "facet" },
    { route_id: "open-b", label: "Open b", kind: "neighbour" },
  ],
  opened: [],
};

describe("ContextWalk", () => {
  beforeEach(() => {
    post.mockReset();
  });

  it("opens the record and keeps a filter on it", async () => {
    post.mockResolvedValueOnce({ data: opened, error: undefined });
    post.mockResolvedValueOnce({
      data: { ...opened, opened: [] },
      error: undefined,
    });
    render(<ContextWalk captureId="vault-1" />);
    fireEvent.click(screen.getByRole("button", { name: "See what relates" }));
    expect(await screen.findByRole("button", { name: "Only notes" })).toBeInTheDocument();
    const first = post.mock.calls[0]?.[1].body;
    expect(first.anchor_id).toBe("vault-1");
    expect(first.hold_at_anchor).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Only notes" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    const second = post.mock.calls[1]?.[1].body;
    expect(second.operation).toBe("continue");
    expect(second.route_handle).toBe("rh_1");
    expect(second.route_id).toBe("facet-1");
    expect(screen.queryByText("Open b")).toBeInTheDocument();
  });

  it("names the problem when the walk cannot start", async () => {
    post.mockResolvedValueOnce({ data: undefined, error: { code: "grant_required" } });
    render(<ContextWalk captureId="vault-1" />);
    fireEvent.click(screen.getByRole("button", { name: "See what relates" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't open related context");
  });
});
