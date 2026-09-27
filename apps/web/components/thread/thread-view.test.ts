import { describe, expect, it } from "vitest";
import type { components } from "@wellbe/api-client";
import {
  clarifyQuestion,
  eventStage,
  latestChange,
  resolveSources,
  storyEntries,
  theoryEvidenceIds,
  waitingOn,
} from "./thread-view";
import type { ThreadTimelineV2 } from "@/lib/thread-hooks";

type Memory = components["schemas"]["MemoryEntryV2"];

function memory(overrides: Partial<Memory> = {}): Memory {
  return {
    schema_version: "c13.memory_entry.v2",
    memory_entry_id: "m1",
    memory_type: "clinical",
    lifecycle_state: "visible",
    title: "headache",
    thread_id: "t1",
    source_refs: [],
    ...overrides,
  } as Memory;
}

describe("storyEntries", () => {
  it("maps lifecycle, staleness and corrections onto the entry", () => {
    const [e] = storyEntries(
      [memory({ authorship_mode: "hybrid", projection_stale: true, resolved_overlays: [{ x: 1 }] })],
      new Map(),
    );
    expect(e).toMatchObject({ authorship: "hybrid", lifecycle: "projection_stale", correction: { state: "corrected" } });
    expect(e!.text).toBe("Headache");
  });

  it("keeps voice text verbatim", () => {
    const [e] = storyEntries([memory({ authorship_mode: "controller_authored", title: "a dull ache" })], new Map());
    expect(e!.text).toBe("a dull ache");
    expect(e!.reviewMarkers).toBeUndefined();
  });
});

describe("resolveSources", () => {
  it("dedupes and leaves unknown ids label-less so primitives never show them", () => {
    const out = resolveSources(["a", "a", "b"], new Map([["a", { id: "a", displayLabel: "Lab", component: "c2" }]]));
    expect(out).toEqual([
      { id: "a", displayLabel: "Lab", component: "c2" },
      { id: "b", displayLabel: "", component: "c5" },
    ]);
  });
});

describe("clarifyQuestion", () => {
  const derived = storyEntries([memory({ authorship_mode: "system_derived" })], new Map());
  const voice = storyEntries([memory({ authorship_mode: "controller_confirmed" })], new Map());

  it("asks for the user's words when everything is derived", () => {
    expect(clarifyQuestion({ title: "Headache", entries: derived, investigations: [] })?.question).toBe(
      "In your own words, how has your headache been?",
    );
  });

  it("returns null when nothing real is missing", () => {
    expect(clarifyQuestion({ title: "Headache", entries: voice, investigations: [] })).toBeNull();
  });

  it("phrases object-shaped missing items as a question", () => {
    const q = clarifyQuestion({
      title: "Headache",
      entries: voice,
      investigations: [
        { primary_question: "Why?", missing_context_items: [{ label: "sleep over the last week" }] },
      ] as never,
    });
    expect(q?.question).toBe("Could you add anything about sleep over the last week?");
  });
});

describe("timeline helpers", () => {
  const timeline = {
    status_history: ["draft", "active_unresolved"],
    events: [
      { event_id: "a", kind: "thread_started", occurred_at: "2026-09-01T00:00:00Z", title: "Started" },
      { event_id: "b", kind: "status_changed", occurred_at: "2026-09-02T00:00:00Z", title: "x", to_status: "active_unresolved" },
    ],
  } as unknown as ThreadTimelineV2;

  it("picks the latest non-start event as what changed", () => {
    expect(latestChange(timeline)?.event_id).toBe("b");
  });

  it("maps events to journey stages", () => {
    expect(eventStage(timeline.events[0]!, ["draft"])).toBe("started");
    expect(eventStage(timeline.events[1]!, ["draft"])).toBe("open");
  });

  it("names what an in-motion thread waits on", () => {
    expect(waitingOn([{ item_type: "referral_pending", title: "x" } as never])).toBe("a referral");
    expect(waitingOn([])).toBeUndefined();
    expect(waitingOn([{ item_type: "result_pending", title: "x" } as never], "waiting_for_result")).toBeUndefined();
    expect(waitingOn([{ item_type: "referral_pending", title: "x" } as never], "watchful_waiting")).toBe("a referral");
  });

  it("collects theory evidence ids from for/against and the user's citations", () => {
    expect(
      theoryEvidenceIds({
        evidence_for: [{ node_id: "n1" }],
        evidence_against: [{ id: "n2" }],
        latest_evaluation: { evidence_refs: [{ id: "f1" }], evidence_node_ids: ["n3"] },
      }),
    ).toEqual(["n1", "n2", "f1", "n3"]);
  });
});
