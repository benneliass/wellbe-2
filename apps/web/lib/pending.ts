import type { components } from "@wellbe/api-client";
import type { Tone } from "@wellbe/ui";
import { formatShortDate } from "./adapters";

export type PendingItemV2 = components["schemas"]["PendingItemV2"];

const SETTLED = new Set(["resolved", "cancelled", "superseded", "result_received"]);

export interface PendingDueState {
  /** Calm, human label: "Check back Oct 4", "Due Oct 4", "Still open · was due Oct 4". */
  label: string;
  tone: Tone;
  open: boolean;
}

/** Where a follow-up stands on its timeline. Never alarming: amber at most. */
export function describePendingItem(
  item: Pick<PendingItemV2, "status" | "due_at">,
): PendingDueState {
  if (SETTLED.has(item.status)) return { label: "Settled", tone: "green", open: false };
  const date = item.due_at ? formatShortDate(item.due_at) : "";
  if (item.status === "overdue") {
    return { label: date ? `Still open · was due ${date}` : "Still open", tone: "amber", open: true };
  }
  if (item.status === "due") {
    return { label: date ? `Due ${date}` : "Due now", tone: "amber", open: true };
  }
  if (date) return { label: `Check back ${date}`, tone: "teal", open: true };
  return { label: "No date yet", tone: "neutral", open: true };
}

/** Open items, soonest-due first (undated last). */
export function openPendingItems(items: PendingItemV2[]): PendingItemV2[] {
  const time = (i: PendingItemV2) =>
    i.due_at ? new Date(i.due_at).getTime() : Number.POSITIVE_INFINITY;
  return items.filter((i) => describePendingItem(i).open).sort((a, b) => time(a) - time(b));
}
