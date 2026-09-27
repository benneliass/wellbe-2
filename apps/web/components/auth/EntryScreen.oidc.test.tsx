import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getSession } from "@/lib/session";
import { EntryScreen } from "./EntryScreen";

const beginSignIn = vi.fn(async () => {});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/oidc", () => ({
  beginSignIn: () => beginSignIn(),
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
    expect(beginSignIn).toHaveBeenCalledTimes(1);
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
});
