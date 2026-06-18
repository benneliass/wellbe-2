import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TopBar } from "./TopBar";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

describe("TopBar", () => {
  beforeEach(() => {
    push.mockReset();
  });

  it("routes a search to Ask WellBe with the query", () => {
    render(<TopBar title="Workspace" />);
    fireEvent.change(screen.getByPlaceholderText(/search threads/i), {
      target: { value: "vitamin d" },
    });
    fireEvent.submit(screen.getByRole("search"));
    expect(push).toHaveBeenCalledWith("/ask?q=vitamin%20d");
  });

  it("routes an empty search to the Ask surface", () => {
    render(<TopBar title="Workspace" />);
    fireEvent.submit(screen.getByRole("search"));
    expect(push).toHaveBeenCalledWith("/ask");
  });

  it("opens a calm notifications panel", () => {
    render(<TopBar title="Workspace" />);
    fireEvent.click(screen.getByRole("button", { name: /notifications/i }));
    expect(screen.getByText(/caught up/i)).toBeInTheDocument();
  });

  it("opens a help panel", () => {
    render(<TopBar title="Workspace" />);
    fireEvent.click(screen.getByRole("button", { name: /help/i }));
    expect(screen.getByText(/how wellbe works/i)).toBeInTheDocument();
  });
});
