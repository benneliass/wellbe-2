import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  ConfidenceMeter,
  CorrectionMarker,
  EVIDENCE_TOKENS,
  REVIEW_MARKER_LABELS,
  ReviewMarker,
  ReviewMarkerList,
  SourceMarker,
  bucketConfidence,
  looksLikeRawId,
} from "@wellbe/ui";

describe("SourceMarker", () => {
  it("shows the display label, date and component, and opens evidence on click", async () => {
    const onOpen = vi.fn();
    render(
      <SourceMarker displayLabel="Blood panel, March" component="c2" kind="lab" date="2026-03-12" onOpen={onOpen} />,
    );
    const button = screen.getByRole("button", { name: /blood panel, march/i });
    expect(button).toHaveAccessibleName(/your record/i);
    expect(button).toHaveAccessibleName(/open evidence/i);
    expect(screen.getByText("12 Mar 2026")).toHaveAttribute("datetime", "2026-03-12T00:00:00.000Z");
    await userEvent.click(button);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("is keyboard activatable", async () => {
    const onOpen = vi.fn();
    render(<SourceMarker displayLabel="Sleep log" onOpen={onOpen} />);
    await userEvent.tab();
    expect(screen.getByRole("button")).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard(" ");
    expect(onOpen).toHaveBeenCalledTimes(2);
  });

  it("never renders a raw id, falling back to the component label", () => {
    const id = "3f2b8c1e-9a4d-4f7e-8b21-0c5d6e7f8a90";
    const { container } = render(<SourceMarker displayLabel={id} component="c5" />);
    expect(container).not.toHaveTextContent(id);
    expect(screen.getByText("From your data")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("separates external references visibly and shows extra source count", () => {
    const { container } = render(<SourceMarker displayLabel="NICE guideline" component="c16" count={3} />);
    expect(screen.getByText("External")).toBeInTheDocument();
    expect(container).toHaveTextContent("+2 more");
    expect(container.firstElementChild).toHaveAttribute("data-component", "c16");
  });

  it("detects raw id shapes but leaves human labels alone", () => {
    expect(looksLikeRawId("01HZX3K9T8Q4M2N6P7R5S1V0WY")).toBe(true);
    expect(looksLikeRawId("src_8f7a2b91c")).toBe(true);
    expect(looksLikeRawId("Blood panel")).toBe(false);
    expect(looksLikeRawId("GP visit notes")).toBe(false);
  });
});

describe("ConfidenceMeter", () => {
  it.each([
    [0, "tentative"],
    [0.39, "tentative"],
    [0.4, "moderate"],
    [0.75, "moderate"],
    [0.76, "well-supported"],
    [1, "well-supported"],
  ] as const)("buckets %s as %s", (score, level) => {
    expect(bucketConfidence(score)).toBe(level);
  });

  it("returns null for missing or invalid scores and clamps out-of-range ones", () => {
    expect(bucketConfidence(undefined)).toBeNull();
    expect(bucketConfidence(Number.NaN)).toBeNull();
    expect(bucketConfidence(-2)).toBe("tentative");
    expect(bucketConfidence(4)).toBe("well-supported");
  });

  it.each([
    [0.2, "Tentative", /confidence: tentative, early signal/i],
    [0.6, "Moderate", /confidence: moderate, some support/i],
    [0.9, "Well supported", /confidence: well supported, consistent support/i],
  ])("shows %s as words with an accessible label", (score, word, name) => {
    const { container } = render(<ConfidenceMeter score={score} />);
    expect(screen.getByRole("img", { name })).toBeInTheDocument();
    expect(container).toHaveTextContent(word);
    expect(container).not.toHaveTextContent(String(score));
    expect(container).not.toHaveTextContent("%");
  });

  it("renders nothing without a score or level", () => {
    const { container } = render(<ConfidenceMeter />);
    expect(container).toBeEmptyDOMElement();
  });

  it("reveals the basis on request", async () => {
    render(<ConfidenceMeter score={0.5} basis="Three logs over two weeks" />);
    expect(screen.queryByText("Three logs over two weeks")).not.toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "Why?" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Three logs over two weeks")).toBeInTheDocument();
  });
});

describe("ReviewMarker", () => {
  it.each([
    ["patient-entered", "Your words"],
    ["AI-summarized", "WellBe summary"],
    ["not-clinician-reviewed", "Not clinician-reviewed"],
    ["clinician-reviewed", "Clinician-reviewed"],
    ["clinician-annotated", "Clinician note added"],
    ["ready-for-visit", "Ready for visit"],
  ] as const)("labels %s as %s", (value, label) => {
    render(<ReviewMarker value={value} />);
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(REVIEW_MARKER_LABELS[value]).toBe(label);
  });

  it("only shows urgent wording with a Safety Gate approval", () => {
    const { rerender, container } = render(<ReviewMarker value="needs-urgent-care-consideration" />);
    expect(container).toHaveTextContent("Needs attention");
    expect(container).not.toHaveTextContent("urgent");
    rerender(<ReviewMarker value="needs-urgent-care-consideration" safetyApproved />);
    expect(container).toHaveTextContent("Worth urgent attention");
  });

  it("renders every marker the approval carries", () => {
    render(<ReviewMarkerList values={["AI-summarized", "not-clinician-reviewed"]} />);
    const list = screen.getByRole("list", { name: "Review status" });
    expect(list.querySelectorAll("li")).toHaveLength(2);
  });
});

describe("CorrectionMarker", () => {
  it("shows who corrected it and when, and links to the prior version", () => {
    render(
      <CorrectionMarker state="corrected" correctedBy="you" correctedAt="2026-04-02" priorVersionHref="/memory/m1/v1" />,
    );
    expect(screen.getByText("Corrected")).toBeInTheDocument();
    expect(screen.getByText("by you")).toBeInTheDocument();
    expect(screen.getByText(/2 Apr 2026/)).toBeInTheDocument();
    expect(screen.getByText(/original kept/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View earlier version" })).toHaveAttribute("href", "/memory/m1/v1");
  });

  it("uses a button for history when there is no link", async () => {
    const onOpenHistory = vi.fn();
    render(<CorrectionMarker state="superseded" onOpenHistory={onOpenHistory} />);
    expect(screen.getByText("Replaced by a correction")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "View earlier version" }));
    expect(onOpenHistory).toHaveBeenCalled();
  });

  it("renders nothing without a correction state", () => {
    const { container } = render(<CorrectionMarker />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("EVIDENCE_TOKENS", () => {
  it("names the four evidence provenance tokens as CSS custom properties", () => {
    expect(Object.keys(EVIDENCE_TOKENS).sort()).toEqual(
      ["ai_summarized", "clinician_reviewed", "corrected", "patient_entered"].sort(),
    );
    for (const meta of Object.values(EVIDENCE_TOKENS)) {
      expect(meta.tintVar).toMatch(/^--wb-evidence-/);
      expect(meta.fgVar).toMatch(/^--wb-evidence-/);
    }
  });
});
