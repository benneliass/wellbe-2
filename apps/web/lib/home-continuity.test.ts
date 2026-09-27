import { describe, expect, it } from "vitest";
import type { components } from "@wellbe/api-client";
import { containsBannedPhrasing } from "@wellbe/ui";
import {
  advanceVisit,
  buildWhatChanged,
  continuityCounts,
  continuityLine,
  groupOpenLoops,
  homeStatusLine,
  isDueSoon,
  loopStateLabel,
  nextStepFor,
  noticedReason,
  remindLaterDate,
  visibleThingsNoticed,
} from "./home-continuity";
import type { ThreadSummary } from "./types";

type PendingItemV2 = components["schemas"]["PendingItemV2"];
type DeltaEventV2 = components["schemas"]["DeltaEventV2"];
type ThingNoticedV1 = components["schemas"]["ThingNoticedV1"];

const NOW = new Date("2026-09-27T12:00:00Z");

function loop(over: Partial<PendingItemV2>): PendingItemV2 {
  return {
    schema_version: "c13.pending_item.v2",
    pending_item_id: over.pending_item_id ?? "p",
    primary_thread_id: "t1",
    item_type: "follow_up_due",
    status: "active",
    title: "Loop",
    due_precision: "date",
    blocks_closure: false,
    created_at: "2026-09-01T00:00:00Z",
    updated_at: "2026-09-01T00:00:00Z",
    ...over,
  };
}

function event(over: Partial<DeltaEventV2>): DeltaEventV2 {
  return {
    id: over.id ?? "e",
    category: "open_loop",
    title: "Something",
    ranking_reason: "Open item changed",
    occurred_at: "2026-09-25T00:00:00Z",
    source: { ref_type: "health_thread", source_id: "t1", label: "Something" },
    ...over,
  };
}

function noticed(over: Partial<ThingNoticedV1>): ThingNoticedV1 {
  return {
    schema_version: "c13.thing_noticed.v1",
    candidate_id: over.candidate_id ?? "c",
    title: "Morning dizziness",
    candidate_type: "symptom",
    status: "pending",
    seen_count: 1,
    first_seen_at: "2026-09-18T00:00:00Z",
    last_seen_at: "2026-09-26T00:00:00Z",
    source_capture_count: 1,
    source_fact_count: 0,
    ...over,
  };
}

describe("groupOpenLoops", () => {
  it("groups by what the person can do and keeps done items off Home", () => {
    const groups = groupOpenLoops([
      loop({ pending_item_id: "due", status: "due", due_at: "2026-09-30T00:00:00Z" }),
      loop({ pending_item_id: "over", status: "overdue", due_at: "2026-10-05T00:00:00Z" }),
      loop({ pending_item_id: "wait", status: "waiting_external" }),
      loop({ pending_item_id: "back", status: "result_received" }),
      loop({ pending_item_id: "calm", status: "no_due_date" }),
      loop({ pending_item_id: "act", status: "active" }),
      loop({ pending_item_id: "done", status: "resolved" }),
      loop({ pending_item_id: "gone", status: "cancelled" }),
    ]);
    const ids = (xs: PendingItemV2[]) => xs.map((x) => x.pending_item_id);
    // Overdue raises order within Needs attention, ahead of a sooner due date.
    expect(ids(groups.attention)).toEqual(["over", "due"]);
    expect(ids(groups.motion).sort()).toEqual(["back", "wait"]);
    expect(ids(groups.steady).sort()).toEqual(["act", "calm"]);
  });
});

describe("loop copy", () => {
  it("gives one plain next step, preferring the backend's code", () => {
    expect(nextStepFor(loop({ item_type: "referral_pending" }))).toBe("Ask about the referral");
    expect(nextStepFor(loop({ next_action_code: "book_follow_up" }))).toBe("Book follow up");
    expect(nextStepFor(loop({ status: "result_received" }))).toBe("Log the result");
  });

  it("never uses alarm copy for overdue items", () => {
    const state = loopStateLabel(loop({ status: "overdue", due_at: "2026-09-20T12:00:00Z" }));
    expect(state).toEqual({ label: "Still open · was due Sep 20", tone: "amber" });
  });
});

describe("isDueSoon", () => {
  it("counts due/overdue and items due within a week", () => {
    expect(isDueSoon(loop({ status: "due" }), NOW)).toBe(true);
    expect(isDueSoon(loop({ status: "active", due_at: "2026-10-01T00:00:00Z" }), NOW)).toBe(true);
    expect(isDueSoon(loop({ status: "active", due_at: "2026-11-01T00:00:00Z" }), NOW)).toBe(false);
    expect(isDueSoon(loop({ status: "resolved", due_at: "2026-09-28T00:00:00Z" }), NOW)).toBe(false);
  });
});

describe("advanceVisit", () => {
  it("has no window on a first visit", () => {
    const { since, next } = advanceVisit(null, NOW);
    expect(since).toBeNull();
    expect(JSON.parse(next)).toEqual({ previous: null, current: NOW.toISOString() });
  });

  it("keeps the same window on a reload within the visit", () => {
    const raw = JSON.stringify({ previous: "2026-09-20T08:00:00.000Z", current: "2026-09-27T10:00:00.000Z" });
    expect(advanceVisit(raw, NOW)).toEqual({ since: "2026-09-20T08:00:00.000Z", next: raw });
  });

  it("starts a new visit after a long gap, looking back to the last one", () => {
    const raw = JSON.stringify({ previous: null, current: "2026-09-20T08:00:00.000Z" });
    const { since, next } = advanceVisit(raw, NOW);
    expect(since).toBe("2026-09-20T08:00:00.000Z");
    expect(JSON.parse(next).current).toBe(NOW.toISOString());
  });

  it("recovers from a corrupt record", () => {
    expect(advanceVisit("{nope", NOW).since).toBeNull();
  });
});

describe("buildWhatChanged", () => {
  it("builds a calm headline from real changes", () => {
    const summary = buildWhatChanged({
      since: "2026-09-20T12:00:00Z",
      events: [
        event({ id: "a", category: "open_loop", ranking_reason: "New open item" }),
        event({ id: "b", category: "lifecycle", ranking_reason: "Status changed", occurred_at: "2026-09-26T00:00:00Z" }),
      ],
      resultDates: ["2026-09-22T00:00:00Z", "2026-08-01T00:00:00Z"],
      pending: [loop({ status: "due", due_at: "2026-09-29T00:00:00Z" })],
      now: NOW,
    });
    expect(summary.headline).toBe("Since Sep 20: 1 new result, 1 open loop due soon, 1 new open loop");
    expect(summary.status).toBe("One thing needs a look. Everything else is steady.");
    expect(summary.recent.map((e) => e.id)).toEqual(["b", "a"]);
  });

  it("stays affirming without implying closure when nothing changed", () => {
    const summary = buildWhatChanged({
      since: "2026-09-20T12:00:00Z",
      events: [],
      resultDates: [],
      pending: [],
      now: NOW,
    });
    expect(summary.headline).toBe("Nothing new since Sep 20");
    expect(summary.status).toMatch(/Nothing needs your attention right now/);
    expect(summary.status).not.toMatch(/all clear|healthy|fine/i);
  });

  it("counts several things needing a look", () => {
    expect(homeStatusLine([loop({ status: "due" }), loop({ status: "overdue" })])).toBe(
      "2 things need a look. Everything else is steady.",
    );
  });
});

describe("continuity strip", () => {
  const thread = (status: ThreadSummary["status"]): ThreadSummary => ({
    id: status,
    title: status,
    status,
    rawStatus: status,
    started: "",
    updated: "",
    createdAt: "",
    updatedAt: "",
  });

  it("counts carried threads, open loops and visible things noticed", () => {
    const counts = continuityCounts(
      [thread("active"), thread("attention"), thread("resolved")],
      [loop({ status: "due" }), loop({ status: "resolved" })],
      [noticed({}), noticed({ candidate_id: "s", snoozed_until: "2026-10-04T09:00:00Z" })],
      NOW,
    );
    expect(counts).toEqual({ threads: 2, loops: 1, noticed: 1 });
    expect(continuityLine(counts)).toBe("2 threads carrying forward · 1 open loop · 1 thing noticed");
    expect(continuityLine({ threads: 1, loops: 0, noticed: 0 })).toBe("1 thread carrying forward");
  });
});

describe("things noticed", () => {
  it("hides snoozed candidates until the date and ignored ones until seen again", () => {
    const items = [
      noticed({ candidate_id: "plain" }),
      noticed({ candidate_id: "snoozed", snoozed_until: "2026-10-04T09:00:00Z" }),
      noticed({ candidate_id: "due-back", snoozed_until: "2026-09-27T09:00:00Z" }),
      noticed({ candidate_id: "ignored", ignored_at: "2026-09-26T12:00:00Z" }),
      noticed({ candidate_id: "seen-again", ignored_at: "2026-09-25T00:00:00Z" }),
      noticed({ candidate_id: "rejected", status: "dismissed" }),
    ];
    expect(visibleThingsNoticed(items, NOW).map((c) => c.candidate_id)).toEqual([
      "plain",
      "due-back",
      "seen-again",
    ]);
  });

  it("writes reasons without causal or diagnostic phrasing", () => {
    const repeat = noticedReason({ seen_count: 3, first_seen_at: "2026-09-18T00:00:00Z", candidate_type: "symptom" });
    const once = noticedReason({ seen_count: 1, first_seen_at: "2026-09-18T00:00:00Z", candidate_type: "lab_abnormality" });
    expect(repeat).toBe("You've mentioned this 3 times since Sep 18. Keeping it together could be useful context.");
    expect(once).toMatch(/^A result you logged on Sep 18/);
    expect(containsBannedPhrasing(repeat)).toBe(false);
    expect(containsBannedPhrasing(once)).toBe(false);
  });

  it("reminds a week later at 9am local", () => {
    const d = remindLaterDate(new Date(2026, 8, 27, 15, 30));
    expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours(), d.getMinutes()]).toEqual([2026, 9, 4, 9, 0]);
  });
});
