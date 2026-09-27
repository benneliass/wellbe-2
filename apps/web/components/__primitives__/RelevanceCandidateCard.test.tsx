import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  BANNED_CANDIDATE_PHRASES,
  CANDIDATE_COPY,
  RelevanceCandidateCard,
  containsBannedPhrasing,
  type RelevanceCandidateCardProps,
} from "@wellbe/ui";

function props(over: Partial<RelevanceCandidateCardProps> = {}): RelevanceCandidateCardProps {
  return {
    targetThreadTitle: "Recurring morning headaches",
    reason: "Similar timing: logged two days before the last two headaches.",
    candidateLabel: "Sleep log, 12 Mar",
    sources: [
      { id: "s1", displayLabel: "Sleep log", component: "c5", kind: "wearable", date: "2026-03-12" },
      { id: "s2", displayLabel: "Symptom log", component: "c5", kind: "reported" },
    ],
    confidence: 0.35,
    confidenceBasis: "Two overlapping dates",
    onAccept: vi.fn(),
    onReject: vi.fn(),
    onIgnore: vi.fn(),
    onRemindLater: vi.fn(),
    ...over,
  };
}

const BANNED_WORDS = [/this caused/i, /explains/i, /diagnosis/i, /confirmed/i, /you have/i];

describe("RelevanceCandidateCard", () => {
  it("frames the suggestion as 'may relate' with reason, sources and confidence", () => {
    render(<RelevanceCandidateCard {...props()} />);
    expect(screen.getByText("Things noticed")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /sleep log, 12 mar may relate to recurring morning headaches/i })).toBeInTheDocument();
    expect(screen.getByText(/similar timing/i)).toBeInTheDocument();
    expect(screen.getByText("Sleep log")).toBeInTheDocument();
    expect(screen.getByText("Symptom log")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /confidence: tentative/i })).toBeInTheDocument();
    expect(screen.getByText("WellBe summary")).toBeInTheDocument();
    expect(screen.getByText(CANDIDATE_COPY.defaultEffect)).toBeInTheDocument();
  });

  it("wires accept, reject, ignore and remind-later callbacks", async () => {
    const p = props();
    render(<RelevanceCandidateCard {...p} />);
    await userEvent.click(screen.getByRole("button", { name: "Accept" }));
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    await userEvent.click(screen.getByRole("button", { name: "Ignore for now" }));
    await userEvent.click(screen.getByRole("button", { name: "Remind me later" }));
    expect(p.onAccept).toHaveBeenCalledTimes(1);
    expect(p.onReject).toHaveBeenCalledTimes(1);
    expect(p.onIgnore).toHaveBeenCalledTimes(1);
    expect(p.onRemindLater).toHaveBeenCalledTimes(1);
  });

  it("opens a source when a source marker is activated", async () => {
    const onOpenSource = vi.fn();
    const p = props({ onOpenSource });
    render(<RelevanceCandidateCard {...p} />);
    await userEvent.click(screen.getByRole("button", { name: /sleep log/i }));
    expect(onOpenSource).toHaveBeenCalledWith(p.sources?.[0]);
  });

  it("never renders banned phrasing in its default copy", () => {
    for (const confidence of [0.1, 0.5, 0.9]) {
      const { container, unmount } = render(
        <RelevanceCandidateCard {...props({ confidence, candidateLabel: undefined, effectIfAccepted: undefined })} />,
      );
      for (const re of BANNED_WORDS) expect(container.textContent ?? "").not.toMatch(re);
      unmount();
    }
    for (const text of Object.values(CANDIDATE_COPY)) {
      expect(containsBannedPhrasing(text)).toBe(false);
    }
  });

  it("replaces caller copy that contains causal or diagnostic phrasing", () => {
    const { container } = render(
      <RelevanceCandidateCard
        {...props({
          reason: "This explains your headaches.",
          effectIfAccepted: "Confirmed diagnosis will be added.",
          candidateLabel: "You have migraine",
        })}
      />,
    );
    for (const re of BANNED_WORDS) expect(container.textContent ?? "").not.toMatch(re);
    expect(screen.getByText(CANDIDATE_COPY.fallbackReason)).toBeInTheDocument();
    expect(screen.getByText(CANDIDATE_COPY.defaultEffect)).toBeInTheDocument();
  });

  it("flags every banned phrase", () => {
    for (const phrase of ["this caused it", "that explains it", "a diagnosis", "confirmed", "you have X"]) {
      expect(containsBannedPhrasing(phrase)).toBe(true);
    }
    expect(containsBannedPhrasing("may relate to similar timing")).toBe(false);
    expect(BANNED_CANDIDATE_PHRASES.length).toBeGreaterThanOrEqual(5);
  });
});
