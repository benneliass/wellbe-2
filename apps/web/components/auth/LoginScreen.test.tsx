import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { describeRules, LoginScreen } from "./LoginScreen";

const beginSignIn = vi.fn(async (_options?: { demo?: boolean }) => {});
const takeDemoSignInIntent = vi.fn(() => false);
vi.mock("@/lib/oidc", () => ({
  beginSignIn: (options?: { demo?: boolean }) => beginSignIn(options),
  takeDemoSignInIntent: () => takeDemoSignInIntent(),
}));

const fetchMock = vi.fn();
const assign = vi.fn();

function reply(body: unknown, status = 200) {
  fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(body), { status }));
}

function fillCredentials() {
  fireEvent.change(screen.getByLabelText("Email or username"), { target: { value: "ben" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pw" } });
  fireEvent.click(screen.getByRole("button", { name: /^Sign in/ }));
}

describe("LoginScreen", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    Object.defineProperty(window, "location", { value: { assign }, writable: true });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
    assign.mockReset();
    beginSignIn.mockClear();
    takeDemoSignInIntent.mockReset().mockReturnValue(false);
  });

  it("signs in and follows the callback URL", async () => {
    reply({ kind: "ok", callbackUrl: "https://auth.example/cb" });
    render(<LoginScreen authRequestId="V2_1" />);
    fillCredentials();
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://auth.example/cb"));
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/login/submit");
    expect(JSON.parse(init.body)).toEqual({ authRequestId: "V2_1", loginName: "ben", password: "pw" });
  });

  it("shows a generic error and clears the password when credentials are wrong", async () => {
    reply({ kind: "invalid_credentials" });
    render(<LoginScreen authRequestId="V2_1" />);
    fillCredentials();
    expect(await screen.findByRole("alert")).toHaveTextContent("don't match");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(assign).not.toHaveBeenCalled();
  });

  it("walks through a forced password change", async () => {
    reply({
      kind: "password_change_required",
      rules: { minLength: 8, requiresUppercase: true, requiresLowercase: false, requiresNumber: false, requiresSymbol: false },
    });
    render(<LoginScreen authRequestId="V2_1" />);
    fillCredentials();
    expect(await screen.findByText("Choose a new password")).toBeInTheDocument();
    expect(screen.getByText("At least 8 characters")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "New-Secret2" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "different" } });
    fireEvent.click(screen.getByRole("button", { name: /Save and continue/ }));
    expect(screen.getByRole("alert")).toHaveTextContent("don't match");
    expect(fetchMock).toHaveBeenCalledTimes(1);

    reply({ kind: "ok", callbackUrl: "https://auth.example/cb" });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "New-Secret2" } });
    fireEvent.click(screen.getByRole("button", { name: /Save and continue/ }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://auth.example/cb"));
    expect(JSON.parse(fetchMock.mock.calls[1]![1].body)).toMatchObject({
      password: "pw",
      newPassword: "New-Secret2",
    });
  });

  it("offers to restart when the auth request is missing or expired", async () => {
    render(<LoginScreen authRequestId={null} />);
    expect(screen.getByText("Let’s start again")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Sign in/ }));
    await waitFor(() => expect(beginSignIn).toHaveBeenCalledTimes(1));
  });

  it("describes password rules in plain words", () => {
    expect(
      describeRules({ minLength: 10, requiresUppercase: false, requiresLowercase: true, requiresNumber: true, requiresSymbol: true }),
    ).toEqual(["At least 10 characters", "A lowercase letter", "A number", "A symbol"]);
    expect(describeRules(null)).toEqual([]);
  });

  it("opens the demo without asking for anything when this tab chose it", async () => {
    takeDemoSignInIntent.mockReturnValue(true);
    reply({ kind: "ok", callbackUrl: "https://app.example/auth/callback?code=c" });
    render(<LoginScreen authRequestId="V2_1" />);
    expect(screen.getByRole("heading", { name: "Opening the demo…" })).toBeInTheDocument();
    expect(screen.getByText(/Shared sample data/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).toBeNull();
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://app.example/auth/callback?code=c"));
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/login/demo");
    expect(JSON.parse(init.body)).toEqual({ authRequestId: "V2_1" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("lets the demo be retried when it can't open", async () => {
    takeDemoSignInIntent.mockReturnValue(true);
    reply({ kind: "unavailable" }, 502);
    render(<LoginScreen authRequestId="V2_1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("unavailable");
    fireEvent.click(screen.getByRole("button", { name: /Try again/ }));
    await waitFor(() => expect(beginSignIn).toHaveBeenCalledWith({ demo: true }));
  });

  it("restarts an expired demo sign-in as a demo", async () => {
    takeDemoSignInIntent.mockReturnValue(true);
    reply({ kind: "expired" });
    render(<LoginScreen authRequestId="V2_1" />);
    fireEvent.click(await screen.findByRole("button", { name: /Open the demo/ }));
    await waitFor(() => expect(beginSignIn).toHaveBeenCalledWith({ demo: true }));
  });
});
