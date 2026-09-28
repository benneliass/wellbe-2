import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TopBar } from "./TopBar";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/useSession", () => ({
  useSession: () => ({
    issuer: "https://auth.example",
    subject: "s1",
    patientId: "p1",
    actorType: "controller",
    onboarded: true,
    displayName: "Ben Elias",
    email: "ben@example.com",
  }),
}));

vi.mock("./NotificationBell", () => ({
  NotificationBell: () => <button type="button">Notifications</button>,
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

  it("shows the signed-in account and opens it", () => {
    render(<TopBar title="Workspace" />);
    const btn = screen.getByRole("button", { name: /your account: ben elias/i });
    expect(btn).toHaveTextContent("BE");
    fireEvent.click(btn);
    expect(screen.getByText("ben@example.com")).toBeInTheDocument();
  });

  it("renders the notification bell", () => {
    render(<TopBar title="Workspace" />);
    expect(screen.getByRole("button", { name: /notifications/i })).toBeInTheDocument();
  });

  it("opens a help panel", () => {
    render(<TopBar title="Workspace" />);
    fireEvent.click(screen.getByRole("button", { name: /help/i }));
    expect(screen.getByText(/how wellbe works/i)).toBeInTheDocument();
  });
});
