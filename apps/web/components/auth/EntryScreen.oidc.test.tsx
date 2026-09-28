import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getSession } from "@/lib/session";
import { EntryScreen } from "./EntryScreen";

const beginSignIn = vi.fn(async (_options?: { demo?: boolean }) => {});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/oidc", () => ({
  beginSignIn: (options?: { demo?: boolean }) => beginSignIn(options),
  currentAccessToken: async () => null,
}));

describe("EntryScreen (oidc mode)", () => {
  afterEach(() => {
    delete window.__WELLBE_AUTH_CONFIG__;
    beginSignIn.mockClear();
  });

  it("offers ZITADEL sign-in instead of the dev identities", () => {
    window.__WELLBE_AUTH_CONFIG__ = { mode: "oidc", issuer: "https://auth.example", clientId: "c" };
    render(<EntryScreen />);
    expect(screen.queryByText("Dev workspace")).toBeNull();
    expect(screen.queryByText("New to WellBe")).toBeNull();
    fireEvent.click(screen.getByText("Sign in"));
    expect(beginSignIn).toHaveBeenCalledWith(undefined);
    // No local identity is minted: the session only exists after the callback.
    expect(getSession()).toBeNull();
  });

  it("explains when sign-in is not configured", () => {
    window.__WELLBE_AUTH_CONFIG__ = { mode: "oidc", issuer: "", clientId: "" };
    render(<EntryScreen />);
    expect(screen.getByRole("alert")).toHaveTextContent("isn't configured");
    fireEvent.click(screen.getByText("Sign in"));
    expect(beginSignIn).not.toHaveBeenCalled();
  });

  it("hides Try the demo unless the server enables it", () => {
    window.__WELLBE_AUTH_CONFIG__ = { mode: "oidc", issuer: "https://auth.example", clientId: "c" };
    render(<EntryScreen />);
    expect(screen.queryByText("Try the demo")).toBeNull();
  });

  it("offers Try the demo as shared sample data and starts a demo sign-in", () => {
    window.__WELLBE_AUTH_CONFIG__ = { mode: "oidc", issuer: "https://auth.example", clientId: "c", demo: true };
    render(<EntryScreen />);
    expect(screen.getByText("Sample data, shared with every visitor")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Try the demo"));
    expect(beginSignIn).toHaveBeenCalledWith({ demo: true });
    expect(getSession()).toBeNull();
  });
});
