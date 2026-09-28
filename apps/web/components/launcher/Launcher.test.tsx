import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Launcher } from "./Launcher";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("./SignalsPanel", () => ({
  SignalsPanel: () => <button type="button">Your health signals</button>,
}));

let rootNav: ReactNode = null;

vi.mock("@/components/shell/RootFrame", () => ({
  useRootNav: () => rootNav,
}));

vi.mock("./ContinuityStrip", () => ({
  ContinuityStrip: () => <a href="/workspace">5 threads carrying forward</a>,
}));

describe("Launcher", () => {
  beforeEach(() => {
    push.mockReset();
    rootNav = null;
  });

  it("places the root nav in the header before the wordmark, outside the main column", () => {
    rootNav = <nav aria-label="Primary" />;
    render(<Launcher />);
    const nav = within(screen.getByRole("banner")).getByRole("navigation", { name: "Primary" });
    const brand = screen.getByRole("button", { name: "WellBe" });
    expect(nav.compareDocumentPosition(brand) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(screen.getByRole("main")).queryByRole("navigation")).toBeNull();
  });

  it("renders no nav when RootFrame provides none", () => {
    render(<Launcher />);
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("keeps the signals chip in the header, apart from the main column", () => {
    render(<Launcher />);
    const header = screen.getByRole("banner");
    const main = screen.getByRole("main");
    expect(within(header).getByRole("button", { name: /your health signals/i })).toBeInTheDocument();
    expect(within(header).getByRole("button", { name: /full view/i })).toBeInTheDocument();
    expect(within(main).getByRole("heading", { name: /what do you need/i })).toBeInTheDocument();
    expect(within(main).getByLabelText("Ask WellBe")).toBeInTheDocument();
    expect(within(main).queryByRole("button", { name: /your health signals/i })).toBeNull();
  });

  it("gives the triage pill the same calm treatment as every other pill", () => {
    render(<Launcher />);
    const triage = screen.getByRole("button", { name: /something feels off/i });
    const log = screen.getByRole("button", { name: /log something/i });
    expect(triage.className).toBe(log.className);
    expect(triage.children).toHaveLength(log.children.length);
  });

  it("routes pills and the Ask bar", () => {
    render(<Launcher />);
    fireEvent.click(screen.getByRole("button", { name: /something feels off/i }));
    expect(push).toHaveBeenCalledWith("/triage");
    fireEvent.change(screen.getByLabelText("Ask WellBe"), { target: { value: "knee pain" } });
    fireEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(push).toHaveBeenCalledWith("/ask?q=knee%20pain");
  });

  it("places the continuity strip after the Ask bar, inside the main column", () => {
    render(<Launcher />);
    const main = screen.getByRole("main");
    const strip = within(main).getByRole("link", { name: /carrying forward/i });
    const ask = within(main).getByLabelText("Ask WellBe");
    expect(ask.compareDocumentPosition(strip) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("Full View opens the workspace", () => {
    render(<Launcher />);
    fireEvent.click(screen.getByRole("button", { name: /full view/i }));
    expect(push).toHaveBeenCalledWith("/workspace");
  });
});
