import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LiveGraph } from "./LiveGraph";
import fixture from "./liveGraph.fixture.json";

const get = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ GET: get, POST: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/graph",
}));

type Opts = { params?: { path?: { thread_id?: string } } };

function realResponses(path: string, opts?: Opts) {
  const tid = opts?.params?.path?.thread_id;
  const idx = fixture.threads.findIndex((t) => t.thread_id === tid);
  switch (path) {
    case "/v1/threads":
      return fixture.threads;
    case "/v2/graph/threads/{thread_id}":
      return fixture.graphs[idx];
    case "/v2/threads/{thread_id}/memories":
      return fixture.memories[idx];
    case "/v2/pending-items":
      return fixture.pending;
    case "/v2/patterns":
      return { schema_version: "c13.patterns.v2", patterns: fixture.patterns, note: "", not_diagnosis: true };
    case "/v2/investigations":
      return fixture.investigations;
    default:
      throw new Error(`unexpected GET ${path}`);
  }
}

function renderWithClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("LiveGraph", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("loads the person's threads and subgraphs into the cockpit", async () => {
    get.mockImplementation(async (path: string, opts?: Opts) => ({ data: realResponses(path, opts), error: undefined }));
    renderWithClient(<LiveGraph />);
    expect(screen.getByText("Mapping your records…")).toBeInTheDocument();
    expect(await screen.findByRole("group", { name: /Map of your concerns/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Vitamin D \(25-OH\), Lab result/ })).toBeInTheDocument();
    expect(screen.queryByText(/couldn.t be loaded/)).not.toBeInTheDocument();
  });

  it("says so calmly when there is nothing to map", async () => {
    get.mockImplementation(async (path: string) => ({ data: path === "/v2/patterns" ? { patterns: [] } : [], error: undefined }));
    renderWithClient(<LiveGraph />);
    expect(await screen.findByText("Nothing to map yet")).toBeInTheDocument();
  });

  it("shows an error state when threads fail", async () => {
    get.mockImplementation(async () => ({ data: undefined, error: { detail: "boom" } }));
    renderWithClient(<LiveGraph />);
    expect(await screen.findByText("Couldn't load your graph")).toBeInTheDocument();
  });

  it("still renders the map with a notice when an enrichment fails", async () => {
    get.mockImplementation(async (path: string, opts?: Opts) =>
      path === "/v2/patterns" ? { data: undefined, error: { detail: "down" } } : { data: realResponses(path, opts), error: undefined },
    );
    renderWithClient(<LiveGraph />);
    expect(await screen.findByText(/Some details couldn.t be loaded right now/)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: /Map of your concerns/ })).toBeInTheDocument();
  });
});
