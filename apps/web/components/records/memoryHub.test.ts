import { describe, expect, it } from "vitest";
import type { components } from "@wellbe/api-client";
import { groupByType, memoryAuthorship, memoryLifecycle, memorySources, toHubEntry } from "./memoryHub";

type MemoryEntryV2 = components["schemas"]["MemoryEntryV2"];

function entry(over: Partial<MemoryEntryV2> & Record<string, unknown> = {}): MemoryEntryV2 {
  return {
    schema_version: "c13.memory_entry.v2",
    memory_entry_id: "m-1",
    memory_type: "clinical",
    lifecycle_state: "visible",
    title: "cough",
    thread_id: "t-1",
    source_refs: [],
    resolved_overlays: [],
    projection_stale: false,
    ...over,
  } as MemoryEntryV2;
}

describe("memoryHub adapters", () => {
  it("uses explicit authorship and falls back to derived, never to the type default", () => {
    expect(memoryAuthorship(entry({ authorship_mode: "controller_confirmed" }))).toBe("controller_confirmed");
    expect(memoryAuthorship(entry({ memory_type: "story" }))).toBe("system_derived");
    expect(memoryAuthorship(entry({ authorship_mode: "made_up" }))).toBe("system_derived");
  });

  it("maps lifecycle, archived and stale projections", () => {
    expect(memoryLifecycle(entry())).toBe("visible");
    expect(memoryLifecycle(entry({ projection_stale: true }))).toBe("projection_stale");
    expect(memoryLifecycle(entry({ lifecycle_state: "archived" }))).toBe("not_current");
    expect(memoryLifecycle(entry({ lifecycle_state: "superseded_by_correction", projection_stale: true }))).toBe(
      "superseded_by_correction",
    );
  });

  it("labels sources in plain language and never with ids", () => {
    const sources = memorySources(
      entry({
        source_refs: [
          { source_ref_id: "a0865ca4-fde9-5d06-a7c7-2a7a63921ca8", source_ref_type: "c4_extracted_fact" },
          { source_ref_id: "x", source_ref_type: "c3_capture" },
          { source_ref_type: "something_new" },
        ],
      }),
    );
    expect(sources.map((s) => [s.displayLabel, s.component])).toEqual([
      ["Fact from what you added", "c5"],
      ["Something you added", "c2"],
      ["Source", "c5"],
    ]);
  });

  it("prefers original source text over pointer labels", () => {
    const sources = memorySources(
      entry({
        source_texts: [
          {
            source_ref_type: "c4_extracted_fact",
            source_ref_id: "fact-1",
            label: "Published sample case C001: Dismissed and silenced hospital assessment",
            text: "Published sample case C001: Dismissed and silenced hospital assessment\n\nPatient attended hospital.",
          },
        ],
        source_refs: [{ source_ref_id: "node-1", source_ref_type: "c6_kg_node" }],
      }),
    );
    expect(sources).toEqual([
      {
        id: "fact-1:0",
        displayLabel: "Published sample case C001: Dismissed and silenced hospital assessment",
        component: "c2",
        kind: "reported",
        excerpt: "Published sample case C001: Dismissed and silenced hospital assessment\n\nPatient attended hospital.",
      },
    ]);
  });

  it("marks overlays as corrections and groups by type, newest first", () => {
    const a = toHubEntry(entry({ memory_entry_id: "a", created_at: "2026-01-01T00:00:00Z" }), "Cough");
    const b = toHubEntry(
      entry({ memory_entry_id: "b", created_at: "2026-03-01T00:00:00Z", resolved_overlays: [{ status: "applied" }] }),
      "Cough",
    );
    const c = toHubEntry(entry({ memory_entry_id: "c", memory_type: "mystery" }), "Cough");
    expect(b.correction).toEqual({ state: "corrected" });
    const groups = groupByType([a, b, c]);
    expect(groups.get("clinical")!.map((e) => e.id)).toEqual(["b", "a"]);
    expect(groups.get("other")!.map((e) => e.id)).toEqual(["c"]);
    expect(Array.from(groups.keys())).toEqual([
      "story",
      "clinical",
      "pattern",
      "decision",
      "responsibility",
      "equity_access",
      "other",
    ]);
  });
});
