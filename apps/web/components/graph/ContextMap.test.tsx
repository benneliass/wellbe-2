import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContextMap } from "./ContextMap";
import type { CosmosNode } from "./CosmosField";

// Exercise API/walk policy through the map interface. Real SVG geometry,
// animation, pointer handling and visual effects run in the browser suite;
// continuous SVG mutation is not an input to these controller assertions.
vi.mock("./CosmosField", () => ({
  CosmosField: ({ nodes, onSelect }: { nodes: CosmosNode[]; onSelect: (id: string) => void }) => <div>
    {nodes.map((node) => <div key={node.id} data-dim={node.dim}>
      <button type="button" aria-pressed={node.pressed} onClick={() => onSelect(node.id)} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(node.id); }}>{node.label}</button>
    </div>)}
  </div>,
}));

const get = vi.fn();
const post = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ GET: get, POST: post }),
}));

const map = {
  nodes: [
    { id: "a", kind: "event", source_type: "note", degree: 1, label: "Alpha" },
    { id: "b", kind: "event", source_type: "note", degree: 1, label: "Beta" },
    { id: "c", kind: "event", source_type: "note", degree: 0, label: "Gamma" },
  ],
  links: [{ source: "a", target: "b", reason: "may relate" }],
};

const opened = {
  route: "selected",
  breadcrumb: ["Alpha"],
  hop_depth: 0,
  direct_link_count: 1,
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

describe("ContextMap", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    get.mockResolvedValue({ data: map, error: undefined });
  });

  it("opens the full map, keeps a filter on the record, and returns on clear", async () => {
    post.mockResolvedValue({ data: opened, error: undefined });
    render(<ContextMap />);
    expect(await screen.findByRole("button", { name: "Gamma" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    expect(await screen.findByRole("button", { name: "Only notes" })).toBeInTheDocument();
    expect(post.mock.calls[0]?.[1].body.anchor_id).toBe("a");
    expect(post.mock.calls[0]?.[1].body.hold_at_anchor).toBe(true);
    await waitFor(() => expect(screen.getByRole("button", { name: "Gamma" }).parentElement).toHaveAttribute("data-dim", "true"));

    fireEvent.click(screen.getByRole("button", { name: "Gamma" }));
    expect(post).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Only notes" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[1]?.[1].body.operation).toBe("continue");
    expect(post.mock.calls[1]?.[1].body.route_id).toBe("facet-1");
    expect(screen.getByRole("button", { name: "Gamma" }).parentElement).toHaveAttribute("data-dim", "true");

    fireEvent.click(screen.getByRole("button", { name: "Clear choice" }));
    expect(screen.getByRole("button", { name: "Gamma" }).parentElement).toHaveAttribute("data-dim", "false");
  });

  it("keeps the path and ends navigation when stopped", async () => {
    render(<ContextMap preview />);
    const monday = await screen.findByRole("button", { name: "Monday note" });
    fireEvent.keyDown(monday, { key: "Enter" });
    fireEvent.click(await screen.findByRole("button", { name: "Open r02" }));
    expect(screen.getByRole("button", { name: "Visit summary" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Stop here" }));
    expect(screen.queryByRole("button", { name: "Open r03" })).not.toBeInTheDocument();
    fireEvent.click(monday);
    expect(screen.getByRole("button", { name: "Visit summary" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Clear choice" })).toBeInTheDocument();
  });

  it("can rewind from an exhausted leaf without treating it as an explicit stop", async () => {
    post.mockResolvedValueOnce({ data: opened }).mockResolvedValueOnce({ data: { ...opened, terminal_reason: "supported_leaf", next_routes: [] } }).mockResolvedValueOnce({ data: opened });
    render(<ContextMap />);
    fireEvent.click(await screen.findByRole("button", { name: "Alpha" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open b" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Beta" })).toHaveAttribute("aria-pressed", "true"));
    fireEvent.click(screen.getByRole("button", { name: "Alpha" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(3));
    expect(post.mock.calls[2]?.[1].body.operation).toBe("rewind");
    await waitFor(() => expect(screen.getByRole("button", { name: "Alpha" })).toHaveAttribute("aria-pressed", "true"));
  });

});
