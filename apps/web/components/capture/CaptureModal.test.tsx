import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CaptureModal } from "./CaptureModal";

const post = vi.fn();

vi.mock("@/lib/api", () => ({
  getApiClient: () => ({ POST: post }),
}));

describe("CaptureModal", () => {
  beforeEach(() => {
    post.mockReset();
    post.mockResolvedValue({ data: { capture_id: "evt-1", processing: "pending" }, error: null });
  });

  it("blocks an empty symptom capture before calling the API", () => {
    const onClose = vi.fn();
    render(<CaptureModal onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));

    expect(post).not.toHaveBeenCalled();
    expect(screen.getByText(/describe what you're feeling/i)).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("posts a symptom capture with an Idempotency-Key and acknowledges it", async () => {
    const onClose = vi.fn();
    const onCaptured = vi.fn();
    render(<CaptureModal onClose={onClose} onCaptured={onCaptured} />);

    fireEvent.change(screen.getByPlaceholderText(/describe the symptom/i), {
      target: { value: "sharp lower back ache" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/added to your memory/i));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /done/i }));
    expect(onClose).toHaveBeenCalled();

    expect(post).toHaveBeenCalledTimes(1);
    const [path, opts] = post.mock.calls[0]!;
    expect(path).toBe("/v1/capture");
    expect(opts.body.capture_type).toBe("symptom");
    expect(opts.body.payload.description).toBe("sharp lower back ache");
    expect(opts.params.header["Idempotency-Key"]).toMatch(/[0-9a-f-]{36}/);
    expect(onCaptured).toHaveBeenCalledWith("evt-1");
  });

  it("surfaces an error and stays open when the API rejects", async () => {
    const onClose = vi.fn();
    post.mockResolvedValue({ data: null, error: { detail: "nope" } });
    render(<CaptureModal onClose={onClose} />);

    fireEvent.change(screen.getByPlaceholderText(/describe the symptom/i), {
      target: { value: "headache" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));

    await waitFor(() => expect(screen.getByText(/could not be saved/i)).toBeInTheDocument());
    expect(onClose).not.toHaveBeenCalled();
  });

  it("keeps extra detail collapsed and sends no context by default", async () => {
    render(<CaptureModal onClose={vi.fn()} />);

    const toggle = screen.getByRole("button", { name: /add more detail/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByLabelText(/different from your normal/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/describe the symptom/i), {
      target: { value: "tired" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]![1].body).not.toHaveProperty("context");
  });

  it("sends only the optional answers the person filled in, trimmed and verbatim", async () => {
    render(<CaptureModal onClose={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/describe the symptom/i), {
      target: { value: "knee pain" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add more detail/i }));
    expect(screen.getByRole("button", { name: /hide extra detail/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByText("Your words")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/different from your normal/i), {
      target: { value: "  I can't run anymore  " },
    });
    fireEvent.change(screen.getByLabelText(/worries you most/i), {
      target: { value: "Is it a tear?" },
    });
    fireEvent.change(screen.getByLabelText(/visits, tests or referrals/i), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));

    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    const body = post.mock.calls[0]![1].body;
    expect(body.payload.description).toBe("knee pain");
    expect(body.context).toEqual({
      change_from_normal: "I can't run anymore",
      main_concern: "Is it a tear?",
    });
  });

  it("never requires the extra detail — a filled prompt with an empty story is still blocked", () => {
    render(<CaptureModal onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add more detail/i }));
    fireEvent.change(screen.getByLabelText(/when did it start/i), {
      target: { value: "yesterday" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));
    expect(post).not.toHaveBeenCalled();
    expect(screen.getByText(/describe what you're feeling/i)).toBeInTheDocument();
  });

  it("offers extra detail on notes but not on lab results or documents", () => {
    render(<CaptureModal onClose={vi.fn()} initialType="note" />);
    expect(screen.getByRole("button", { name: /add more detail/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /lab/i }));
    expect(screen.queryByRole("button", { name: /add more detail/i })).not.toBeInTheDocument();
  });

  it("does not send context for a lab capture even if prompts were filled earlier", async () => {
    render(<CaptureModal onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /add more detail/i }));
    fireEvent.change(screen.getByLabelText(/when did it start/i), {
      target: { value: "last week" },
    });
    fireEvent.click(screen.getByRole("button", { name: /lab/i }));
    fireEvent.change(screen.getByLabelText(/test name/i), { target: { value: "LDL" } });
    fireEvent.change(screen.getByLabelText(/^value$/i), { target: { value: "3.1" } });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(post.mock.calls[0]![1].body.capture_type).toBe("lab");
    expect(post.mock.calls[0]![1].body).not.toHaveProperty("context");
  });

  it("reuses the same Idempotency-Key when retried after a failure", async () => {
    const onClose = vi.fn();
    post.mockResolvedValueOnce({ data: null, error: { detail: "boom" } });
    post.mockResolvedValueOnce({ data: { capture_id: "evt-2" }, error: null });
    render(<CaptureModal onClose={onClose} />);

    fireEvent.change(screen.getByPlaceholderText(/describe the symptom/i), {
      target: { value: "dizzy" },
    });
    const submit = screen.getByRole("button", { name: /add to memory/i });

    fireEvent.click(submit);
    await waitFor(() => expect(screen.getByText(/could not be saved/i)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));
    await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());

    const firstKey = post.mock.calls[0]![1].params.header["Idempotency-Key"];
    const secondKey = post.mock.calls[1]![1].params.header["Idempotency-Key"];
    expect(firstKey).toBe(secondKey);
  });
});
