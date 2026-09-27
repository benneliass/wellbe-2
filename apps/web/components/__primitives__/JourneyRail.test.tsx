import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  JourneyRail,
  mapThreadStatusToStage,
  stageTone,
  traveledStages,
  type HealthThreadStatus,
  type JourneyStage,
} from "@wellbe/ui";

describe("mapThreadStatusToStage", () => {
  it.each([
    ["draft", "started"],
    ["active_unresolved", "open"],
    ["reopened", "open"],
    ["waiting_for_result", "in_motion"],
    ["referred", "in_motion"],
    ["watchful_waiting", "in_motion"],
    ["escalated", "needs_attention"],
    ["explained", "understood"],
    ["chronic_monitoring", "ongoing"],
    ["closed", "closed"],
    ["archived", "archived"],
  ] as Array<[HealthThreadStatus, JourneyStage]>)("maps %s to %s", (status, stage) => {
    expect(mapThreadStatusToStage(status)).toBe(stage);
  });
});

describe("stageTone", () => {
  it("never produces urgent, and escalated is needs_attention", () => {
    expect(stageTone("needs_attention")).toBe("needs_attention");
    expect(stageTone("open")).toBeNull();
    expect(stageTone("open", true)).toBe("needs_attention");
    expect(stageTone("ongoing")).toBe("stable");
    expect(stageTone("closed")).toBe("stable");
  });
});

describe("traveledStages", () => {
  it("collapses repeats and excludes the current stage", () => {
    expect(
      traveledStages(["draft", "active_unresolved", "waiting_for_result", "referred"], "referred"),
    ).toEqual(["started", "open"]);
  });

  it("keeps a reopened journey continuous", () => {
    expect(traveledStages(["active_unresolved", "closed", "reopened"], "reopened")).toEqual(["open", "closed"]);
  });
});

describe("JourneyRail", () => {
  it("emphasises the current stage and shows only stages the thread entered", () => {
    render(
      <JourneyRail
        status="waiting_for_result"
        history={["draft", "active_unresolved", "waiting_for_result"]}
        waitingOn="blood test results"
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items.map((li) => li.getAttribute("data-stage"))).toEqual(["started", "open", "in_motion"]);
    const current = items[2];
    expect(current).toHaveAttribute("aria-current", "step");
    expect(current).toHaveTextContent("In motion");
    expect(current).toHaveTextContent("Waiting on blood test results");
    expect(screen.queryByText("Closed")).not.toBeInTheDocument();
  });

  it("shows a likely-next hint only when provided", () => {
    const { rerender } = render(<JourneyRail status="referred" />);
    expect(screen.queryByText("Likely next")).not.toBeInTheDocument();
    rerender(<JourneyRail status="referred" likelyNext="understood" />);
    expect(screen.getByText("Likely next")).toBeInTheDocument();
  });

  it("presents chronic monitoring as ongoing, not done", () => {
    render(<JourneyRail status="chronic_monitoring" />);
    expect(screen.getByText("Ongoing")).toBeInTheDocument();
    expect(screen.getByText("Monitored over time")).toBeInTheDocument();
    expect(screen.queryByText(/done|complete/i)).not.toBeInTheDocument();
  });

  it("has no percentage or score gamification", () => {
    const { container } = render(
      <JourneyRail
        status="explained"
        history={["draft", "active_unresolved", "waiting_for_result", "explained"]}
        whatChanged="Your result came back in the usual range."
        nextAction={<button type="button">Add a note</button>}
      />,
    );
    expect(container).not.toHaveTextContent("%");
    expect(container).not.toHaveTextContent(/\d+\s*(of|\/)\s*\d+/);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("never applies an urgent tone, even for escalated threads", () => {
    const { container } = render(<JourneyRail status="escalated" />);
    const nav = container.querySelector("nav");
    expect(nav).toHaveAttribute("data-state", "needs_attention");
    expect(container).not.toHaveTextContent(/urgent/i);
  });

  it("gives each stage an accessible name and makes stages keyboard focusable", async () => {
    render(
      <JourneyRail
        status="active_unresolved"
        history={["draft", "active_unresolved"]}
        whatChanged="You added a symptom note."
      />,
    );
    await userEvent.tab();
    expect(document.activeElement).toHaveTextContent("Started, visited");
    await userEvent.tab();
    expect(document.activeElement).toHaveTextContent(/Open, current stage\. Open and unresolved\. You added a symptom note\./);
  });

  it("lets the user jump to a stage when selectable", async () => {
    const onSelectStage = vi.fn();
    render(<JourneyRail status="closed" history={["active_unresolved", "closed"]} onSelectStage={onSelectStage} />);
    await userEvent.click(screen.getByRole("button", { name: /open, visited/i }));
    expect(onSelectStage).toHaveBeenCalledWith("open");
  });

  it("compact variant shows only the current stage with what changed", () => {
    render(
      <JourneyRail
        variant="compact"
        status="referred"
        history={["draft", "active_unresolved", "referred"]}
        whatChanged="Referral sent to dermatology."
      />,
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("Referral sent to dermatology.")).toBeInTheDocument();
  });
});
