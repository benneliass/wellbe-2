import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StoryLanes, laneForAuthorship, type StoryEntry } from "@wellbe/ui";

const ENTRIES: StoryEntry[] = [
  {
    id: "v1",
    authorship: "controller_authored",
    text: "The headaches start behind my left eye, usually before 9am.",
    date: "2026-03-01",
  },
  {
    id: "d1",
    authorship: "hybrid",
    text: "Morning headaches reported on most days over three weeks.",
    quotedText: "usually before 9am",
    sources: [
      { id: "s1", displayLabel: "Symptom log", component: "c5", kind: "reported" },
      { id: "s2", displayLabel: "GP visit notes", component: "c2", kind: "note" },
    ],
  },
  {
    id: "r1",
    authorship: "role_authored_pending_acceptance",
    text: "Discussed a sleep diary for two weeks.",
    origin: "Dr Levi (your GP)",
  },
];

describe("laneForAuthorship", () => {
  it("maps authorship modes to lanes", () => {
    expect(laneForAuthorship("controller_authored")).toBe("voice");
    expect(laneForAuthorship("controller_confirmed")).toBe("voice");
    expect(laneForAuthorship("system_derived")).toBe("derived");
    expect(laneForAuthorship("hybrid")).toBe("derived");
    expect(laneForAuthorship("role_authored_pending_acceptance")).toBe("shared_in");
  });
});

describe("StoryLanes", () => {
  it("renders three labelled lanes", () => {
    render(<StoryLanes entries={ENTRIES} />);
    expect(screen.getByRole("region", { name: "Your voice" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "WellBe summaries" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Shared in" })).toBeInTheDocument();
  });

  it("shows voice entries verbatim as a quote with a 'Your words' marker and no AI marker", () => {
    render(<StoryLanes entries={ENTRIES} />);
    const voice = screen.getByRole("region", { name: "Your voice" });
    const quote = voice.querySelector("blockquote");
    expect(quote).toHaveTextContent("The headaches start behind my left eye, usually before 9am.");
    expect(within(voice).getByText("Your words")).toBeInTheDocument();
    expect(within(voice).queryByText("WellBe summary")).not.toBeInTheDocument();
  });

  it("marks derived entries as summaries, attributes hybrid quotes and links to sources", async () => {
    const onOpenSources = vi.fn();
    render(<StoryLanes entries={ENTRIES} onOpenSources={onOpenSources} />);
    const derived = screen.getByRole("region", { name: "WellBe summaries" });
    expect(within(derived).getByText("WellBe summary")).toBeInTheDocument();
    expect(within(derived).getByText("Not clinician-reviewed")).toBeInTheDocument();
    expect(within(derived).getByText("Your words:")).toBeInTheDocument();
    expect(within(derived).getByText("usually before 9am")).toBeInTheDocument();
    await userEvent.click(within(derived).getByRole("button", { name: /symptom log/i }));
    expect(onOpenSources).toHaveBeenCalledWith(ENTRIES[1]);
  });

  it("keeps shared-in entries separate with origin and accept/decline", async () => {
    const onAccept = vi.fn();
    const onDecline = vi.fn();
    render(<StoryLanes entries={ENTRIES} onAccept={onAccept} onDecline={onDecline} />);
    const shared = screen.getByRole("region", { name: "Shared in" });
    expect(within(shared).getByText("From Dr Levi (your GP)")).toBeInTheDocument();
    await userEvent.click(within(shared).getByRole("button", { name: /accept/i }));
    await userEvent.click(within(shared).getByRole("button", { name: "Decline" }));
    expect(onAccept).toHaveBeenCalledWith(ENTRIES[2]);
    expect(onDecline).toHaveBeenCalledWith(ENTRIES[2]);
  });

  it("omits empty derived and shared-in lanes but keeps voice with an entry point", async () => {
    const onAddToStory = vi.fn();
    render(<StoryLanes entries={[]} onAddToStory={onAddToStory} />);
    expect(screen.getByRole("region", { name: "Your voice" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "WellBe summaries" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Shared in" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add to your story" }));
    expect(onAddToStory).toHaveBeenCalled();
  });

  it("keeps superseded entries visible with a link to the correction", () => {
    render(
      <StoryLanes
        entries={[
          {
            id: "v2",
            authorship: "controller_confirmed",
            text: "It started in January.",
            lifecycle: "superseded_by_correction",
            correction: { state: "superseded", priorVersionHref: "/memory/v2/history" },
          },
          { id: "v3", authorship: "controller_authored", text: "Draft note", lifecycle: "draft" },
        ]}
      />,
    );
    expect(screen.getByText("It started in January.")).toBeInTheDocument();
    expect(screen.getByText("Replaced by a correction")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View earlier version" })).toHaveAttribute("href", "/memory/v2/history");
    expect(screen.getByText("Not yet saved to your story")).toBeInTheDocument();
  });
});
