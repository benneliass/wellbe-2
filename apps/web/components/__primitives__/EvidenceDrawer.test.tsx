import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { EvidenceDrawer, type EvidenceSource } from "@wellbe/ui";

const SOURCES: EvidenceSource[] = [
  {
    id: "src-1",
    displayLabel: "GP visit notes",
    component: "c2",
    kind: "note",
    date: "2026-02-10",
    excerpt: "Headaches most mornings for three weeks.",
    confidence: 0.8,
    confidenceBasis: "Recorded at two separate visits",
    reviewMarkers: ["AI-summarized", "not-clinician-reviewed"],
    correction: { state: "corrected", correctedBy: "you", correctedAt: "2026-02-12" },
  },
  {
    id: "3f2b8c1e-9a4d-4f7e-8b21-0c5d6e7f8a90",
    displayLabel: "Migraine overview",
    component: "c16",
    kind: "research",
    qualityTier: "Clinical guideline",
  },
];

function Harness({
  onClose,
  onOpenSource,
}: {
  onClose?: () => void;
  onOpenSource?: (source: EvidenceSource) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Show evidence
      </button>
      <EvidenceDrawer
        open={open}
        onClose={() => {
          onClose?.();
          setOpen(false);
        }}
        claim="Morning headaches have been recurring."
        sources={SOURCES}
        onOpenSource={onOpenSource}
      />
    </>
  );
}

describe("EvidenceDrawer", () => {
  it("opens as a labelled modal dialog and moves focus inside", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    const dialog = screen.getByRole("dialog", { name: "Evidence" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleDescription("Morning headaches have been recurring.");
    expect(screen.getByRole("button", { name: "Close evidence" })).toHaveFocus();
  });

  it("lists sources with source, review, confidence and correction markers", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("GP visit notes")).toBeInTheDocument();
    expect(within(dialog).getByText("WellBe summary")).toBeInTheDocument();
    expect(within(dialog).getByText("Not clinician-reviewed")).toBeInTheDocument();
    expect(within(dialog).getByRole("img", { name: /well supported/i })).toBeInTheDocument();
    expect(within(dialog).getByText("Recorded at two separate visits")).toBeInTheDocument();
    expect(within(dialog).getByText("Corrected")).toBeInTheDocument();
  });

  it("keeps external references in their own section and never shows raw ids", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    const external = screen.getByRole("region", { name: "External reference" });
    expect(within(external).getByText("Migraine overview")).toBeInTheDocument();
    expect(within(external).getByText("General context, not about you specifically.")).toBeInTheDocument();
    expect(within(external).getByText("Source quality: Clinical guideline")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("3f2b8c1e-9a4d");
    expect(document.body).not.toHaveTextContent("src-1");
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} />);
    const trigger = screen.getByRole("button", { name: "Show evidence" });
    await userEvent.click(trigger);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("traps Tab focus inside the dialog", async () => {
    render(
      <>
        <Harness onOpenSource={() => {}} />
        <button type="button">Outside</button>
      </>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    const dialog = screen.getByRole("dialog");
    const close = screen.getByRole("button", { name: "Close evidence" });
    const external = screen.getByRole("button", { name: /migraine overview/i });
    for (let i = 0; i < 6; i++) {
      await userEvent.tab();
      expect(dialog).toContainElement(document.activeElement as HTMLElement);
    }
    close.focus();
    await userEvent.tab({ shift: true });
    expect(external).toHaveFocus();
    await userEvent.tab();
    expect(close).toHaveFocus();
  });

  it("opens a specific source from the drawer", async () => {
    const onOpenSource = vi.fn();
    render(<Harness onOpenSource={onOpenSource} />);
    await userEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    await userEvent.click(screen.getByRole("button", { name: /gp visit notes/i }));
    expect(onOpenSource).toHaveBeenCalledWith(SOURCES[0]);
  });

  it("closes from the close button", async () => {
    render(<Harness />);
    await userEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    await userEvent.click(screen.getByRole("button", { name: "Close evidence" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("says so honestly when there are no sources", () => {
    render(<EvidenceDrawer open onClose={() => {}} sources={[]} />);
    expect(screen.getByText("No sources are attached to this yet.")).toBeInTheDocument();
  });
});
