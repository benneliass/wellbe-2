import { describe, expect, it } from "vitest";
import { describePendingItem, openPendingItems, type PendingItemV2 } from "./pending";

function item(over: Partial<PendingItemV2>): PendingItemV2 {
  return {
    schema_version: "c13.pending_item.v2",
    pending_item_id: "p",
    primary_thread_id: "t",
    item_type: "result_pending",
    status: "scheduled",
    title: "Waiting for a result: Ferritin",
    due_at: "2026-10-04T12:00:00Z",
    due_precision: "relative_policy",
    investigation_ids: [],
    blocks_closure: false,
    created_at: "2026-09-27T12:00:00Z",
    updated_at: "2026-09-27T12:00:00Z",
    audit_refs: [],
    ...over,
  } as PendingItemV2;
}

describe("describePendingItem", () => {
  it("shows when to check back for a scheduled item", () => {
    expect(describePendingItem(item({}))).toEqual({
      label: "Check back Oct 4",
      tone: "teal",
      open: true,
    });
  });

  it("labels due and still-open items calmly", () => {
    expect(describePendingItem(item({ status: "due" })).label).toBe("Due Oct 4");
    const overdue = describePendingItem(item({ status: "overdue" }));
    expect(overdue.label).toBe("Still open · was due Oct 4");
    expect(overdue.tone).toBe("amber");
  });

  it("treats settled items as closed and undated items honestly", () => {
    expect(describePendingItem(item({ status: "resolved" })).open).toBe(false);
    expect(describePendingItem(item({ status: "active", due_at: null })).label).toBe(
      "No date yet",
    );
  });
});

describe("openPendingItems", () => {
  it("keeps open items, soonest due first, undated last", () => {
    const out = openPendingItems([
      item({ pending_item_id: "late", due_at: "2026-11-01T00:00:00Z" }),
      item({ pending_item_id: "none", status: "active", due_at: null }),
      item({ pending_item_id: "done", status: "resolved" }),
      item({ pending_item_id: "soon", status: "due", due_at: "2026-10-01T00:00:00Z" }),
    ]);
    expect(out.map((i) => i.pending_item_id)).toEqual(["soon", "late", "none"]);
  });
});
