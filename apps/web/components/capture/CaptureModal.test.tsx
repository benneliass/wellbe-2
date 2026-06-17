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

  it("posts a symptom capture with an Idempotency-Key and closes on success", async () => {
    const onClose = vi.fn();
    const onCaptured = vi.fn();
    render(<CaptureModal onClose={onClose} onCaptured={onCaptured} />);

    fireEvent.change(screen.getByPlaceholderText(/describe the symptom/i), {
      target: { value: "sharp lower back ache" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to memory/i }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());

    expect(post).toHaveBeenCalledTimes(1);
    const [path, opts] = post.mock.calls[0];
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
    await waitFor(() => expect(onClose).toHaveBeenCalled());

    const firstKey = post.mock.calls[0][1].params.header["Idempotency-Key"];
    const secondKey = post.mock.calls[1][1].params.header["Idempotency-Key"];
    expect(firstKey).toBe(secondKey);
  });
});
