import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ThreadTheories } from "./ThreadTheories";

const get = vi.fn();
const post = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ GET: get, POST: post }),
}));

const THREAD = "thread-1";
const THEORY = {
  theory_id: "theory-1",
  investigation_id: "inv-1",
  label: "Could screen time relate to my headaches?",
  status: "unreviewed",
  version: 3,
  assessment: null,
  latest_evaluation: null,
};

function responses(path: string) {
  switch (path) {
    case "/v2/investigations":
      return [
        { investigation_id: "inv-1", primary_question: "Why the headaches?", health_thread_ids: [THREAD] },
        { investigation_id: "inv-2", primary_question: "Other thread", health_thread_ids: ["x"] },
      ];
    case "/v2/investigations/{investigation_id}/theories":
      return [THEORY];
    case "/v2/threads/{thread_id}/memories":
      return [
        {
          title: "Headache",
          source_refs: [
            { source_ref_type: "c4_extracted_fact", source_ref_id: "fact-1" },
            { source_ref_type: "c6_kg_node", source_ref_id: "node-1" },
          ],
        },
        { title: "Sleep 6h", source_refs: [{ source_ref_type: "c4_extracted_fact", source_ref_id: "fact-2" }] },
      ];
    case "/v2/theories/{theory_id}/evaluations":
      return [];
    default:
      throw new Error(`unexpected GET ${path}`);
  }
}

function renderWithClient(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

async function openForm() {
  renderWithClient(<ThreadTheories threadId={THREAD} />);
  fireEvent.click(await screen.findByRole("button", { name: /evaluate/i }));
  return screen.getByRole("form");
}

describe("ThreadTheories", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    get.mockImplementation(async (path: string) => ({ data: responses(path), error: null }));
  });

  it("shows only investigations that include this thread", async () => {
    renderWithClient(<ThreadTheories threadId={THREAD} />);
    expect(await screen.findByText("Why the headaches?")).toBeInTheDocument();
    expect(screen.queryByText("Other thread")).not.toBeInTheDocument();
    expect(await screen.findByText(THEORY.label)).toBeInTheDocument();
  });

  it("shows the question framing once and never inside a stored label", async () => {
    get.mockImplementation(async (path: string) => ({
      data:
        path === "/v2/investigations/{investigation_id}/theories"
          ? [{ ...THEORY, label: "Could my data be related to: Could my data be related to: screen time?" }]
          : responses(path),
      error: null,
    }));
    renderWithClient(<ThreadTheories threadId={THREAD} />);
    expect(await screen.findByText("screen time")).toBeInTheDocument();
    expect(screen.getAllByText(/could my data be related to/i)).toHaveLength(1);
  });

  it("requires a mark, cited evidence and a rationale before saving", async () => {
    const form = await openForm();
    const save = within(form).getByRole("button", { name: /save evaluation/i });
    expect(save).toBeDisabled();

    fireEvent.click(within(form).getByLabelText(/weakened/i));
    fireEvent.click(within(form).getByLabelText("Headache"));
    expect(save).toBeDisabled();

    fireEvent.change(within(form).getByLabelText(/why\?/i), { target: { value: "  " } });
    expect(save).toBeDisabled();
    expect(post).not.toHaveBeenCalled();
  });

  it("posts the user's evaluation with cited facts and the theory version", async () => {
    post.mockResolvedValue({ data: { theory: THEORY, evaluation: {} }, error: null });
    const form = await openForm();

    fireEvent.click(within(form).getByLabelText(/weakened/i));
    fireEvent.click(within(form).getByLabelText("Headache"));
    fireEvent.change(within(form).getByLabelText(/why\?/i), {
      target: { value: "Headaches continued on screen-free days." },
    });
    fireEvent.click(within(form).getByRole("button", { name: /save evaluation/i }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const [path, opts] = post.mock.calls[0]!;
    expect(path).toBe("/v2/theories/{theory_id}/evaluate");
    expect(opts.params.path.theory_id).toBe("theory-1");
    expect(opts.params.header["Idempotency-Key"]).toMatch(/^web-eval-/);
    expect(opts.body).toEqual({
      to_status: "weakened",
      rationale: "Headaches continued on screen-free days.",
      evidence_refs: [{ kind: "fact", id: "fact-1" }],
      expected_version: 3,
    });
    await waitFor(() => expect(screen.queryByRole("form")).not.toBeInTheDocument());
  });

  it("explains a version conflict and keeps the form open", async () => {
    post.mockResolvedValue({
      data: null,
      error: { code: "version_conflict", detail: "stale" },
      response: { status: 409 },
    });
    const form = await openForm();
    fireEvent.click(within(form).getByLabelText(/ruled out/i));
    fireEvent.click(within(form).getByLabelText("Sleep 6h"));
    fireEvent.change(within(form).getByLabelText(/why\?/i), { target: { value: "Not it." } });
    fireEvent.click(within(form).getByRole("button", { name: /save evaluation/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/changed since you opened it/i);
    expect(screen.getByRole("form")).toBeInTheDocument();
  });
});
