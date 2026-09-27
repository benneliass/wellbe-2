import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThreadDetailLive } from "./ThreadDetailLive";

const get = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ GET: get, POST: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/threads/thread-1",
}));

const THREAD = "thread-1";

function responses(path: string) {
  switch (path) {
    case "/v1/threads/{thread_id}":
      return {
        thread_id: THREAD,
        title: "Headaches",
        status: "active",
        created_at: "2026-09-01T10:00:00Z",
        updated_at: "2026-09-10T10:00:00Z",
      };
    case "/v2/threads/{thread_id}/memories":
      return [
        {
          memory_entry_id: "m1",
          memory_type: "clinical",
          title: "Pain",
          source_refs: [{ source_ref_type: "c4_extracted_fact", source_ref_id: "f1" }],
          created_at: "2026-09-14T08:00:00Z",
        },
      ];
    case "/v2/graph/threads/{thread_id}":
      return {
        thread_id: THREAD,
        nodes: [
          { id: "n1", type: "Symptom", label: "Headache", status: "active", attributes: { in_thread: true } },
          { id: "n2", type: "Symptom", label: "Poor sleep", status: "active", attributes: { in_thread: false } },
        ],
        edges: [],
      };
    case "/v2/pending-items":
    case "/v2/investigations":
      return [];
    default:
      throw new Error(`unexpected GET ${path}`);
  }
}

function renderWithClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("ThreadDetailLive", () => {
  beforeEach(() => {
    get.mockReset();
    get.mockImplementation(async (path: string) => ({ data: responses(path), error: null }));
  });

  it("shows a short date on each memory row", async () => {
    renderWithClient(<ThreadDetailLive id={THREAD} />);
    expect(await screen.findByText("Pain")).toBeInTheDocument();
    expect(screen.getByText(/1 fact from what you added · Sep 14/)).toBeInTheDocument();
  });

  it("marks graph neighbours that sit outside this thread", async () => {
    renderWithClient(<ThreadDetailLive id={THREAD} />);
    expect(await screen.findByText("Poor sleep")).toBeInTheDocument();
    expect(screen.getAllByText(/elsewhere in your records/)).toHaveLength(1);
  });
});
