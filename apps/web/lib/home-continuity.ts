import type { components } from "@wellbe/api-client";
import type { Tone } from "@wellbe/ui";
import { formatShortDate } from "./adapters";
import type { ThreadStatus, ThreadSummary } from "./types";

type PendingItemV2 = components["schemas"]["PendingItemV2"];
type DeltaEventV2 = components["schemas"]["DeltaEventV2"];
type ThingNoticedV1 = components["schemas"]["ThingNoticedV1"];

const DAY_MS = 86_400_000;

/* ------------------------------------------------------------------------ */
/* Open loops, grouped by what the person can do (WEL-145).                  */
/* ------------------------------------------------------------------------ */

export type LoopGroupId = "attention" | "motion" | "steady";

const NEEDS_ATTENTION = new Set(["due", "overdue"]);
const IN_MOTION = new Set(["waiting_external", "scheduled", "in_progress", "result_received"]);
/** Done items live in the ledger, never on Home. */
const DONE = new Set(["resolved", "cancelled", "superseded", "draft"]);

export const LOOP_GROUPS: Record<LoopGroupId, { label: string; hint: string }> = {
  attention: { label: "Needs attention", hint: "Due now or still open past its date" },
  motion: { label: "In motion", hint: "Waiting on a result, referral or appointment" },
  steady: { label: "Steady", hint: "Open, nothing due yet" },
};

export function loopGroupOf(status: string): LoopGroupId | null {
  if (DONE.has(status)) return null;
  if (NEEDS_ATTENTION.has(status)) return "attention";
  if (IN_MOTION.has(status)) return "motion";
  return "steady";
}

function dueTime(item: PendingItemV2): number {
  return item.due_at ? new Date(item.due_at).getTime() : Number.POSITIVE_INFINITY;
}

/** Home's open loops: overdue first within "Needs attention", then soonest due. */
export function groupOpenLoops(items: PendingItemV2[]): Record<LoopGroupId, PendingItemV2[]> {
  const groups: Record<LoopGroupId, PendingItemV2[]> = { attention: [], motion: [], steady: [] };
  for (const item of items) {
    const g = loopGroupOf(item.status);
    if (g) groups[g].push(item);
  }
  groups.attention.sort(
    (a, b) =>
      Number(b.status === "overdue") - Number(a.status === "overdue") || dueTime(a) - dueTime(b),
  );
  groups.motion.sort((a, b) => dueTime(a) - dueTime(b));
  groups.steady.sort((a, b) => dueTime(a) - dueTime(b));
  return groups;
}

const NEXT_STEP_BY_TYPE: Record<string, string> = {
  result_pending: "Log the result when it comes back",
  referral_pending: "Ask about the referral",
  follow_up_due: "Book the follow-up",
  repeat_test_due: "Book the repeat test",
  post_visit_plan_check: "Check in on the plan",
  normal_test_safety_net: "Note it if things change",
  user_next_step: "Your next step",
  care_team_next_step: "Your care team's next step",
};

/** One plain next step per loop: the backend's code if present, else by type. */
export function nextStepFor(item: Pick<PendingItemV2, "next_action_code" | "item_type" | "status">): string {
  if (item.status === "result_received") return "Log the result";
  const code = item.next_action_code?.trim();
  if (code) {
    const text = code.replace(/[_-]+/g, " ");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }
  return NEXT_STEP_BY_TYPE[item.item_type] ?? "Follow up";
}

/** Where a loop stands — calm, amber at most, never an alarm. */
export function loopStateLabel(item: Pick<PendingItemV2, "status" | "due_at">): {
  label: string;
  tone: Tone;
} {
  const date = item.due_at ? formatShortDate(item.due_at) : "";
  switch (item.status) {
    case "overdue":
      return { label: date ? `Still open · was due ${date}` : "Still open", tone: "amber" };
    case "due":
      return { label: date ? `Due ${date}` : "Due now", tone: "amber" };
    case "result_received":
      return { label: "Result came back", tone: "teal" };
    case "waiting_external":
      return { label: date ? `Waiting · expected ${date}` : "Waiting on others", tone: "teal" };
    case "scheduled":
      return { label: date ? `Scheduled ${date}` : "Scheduled", tone: "teal" };
    case "in_progress":
      return { label: "In progress", tone: "teal" };
    default:
      return { label: date ? `Check back ${date}` : "No date yet", tone: "neutral" };
  }
}

/** Open (not done) and due within `days`, or already due/overdue. */
export function isDueSoon(item: PendingItemV2, now: Date, days = 7): boolean {
  const g = loopGroupOf(item.status);
  if (g === null || item.status === "result_received") return false;
  if (g === "attention") return true;
  if (!item.due_at) return false;
  const t = new Date(item.due_at).getTime();
  return !Number.isNaN(t) && t - now.getTime() <= days * DAY_MS;
}

/* ------------------------------------------------------------------------ */
/* "Since you last looked" window.                                           */
/* ------------------------------------------------------------------------ */

export const LAST_VISIT_KEY = "wellbe.home.visits";
/** A new visit starts after this long away; reloads within it keep the window. */
const VISIT_GAP_MS = 6 * 60 * 60 * 1000;

interface Visits {
  previous: string | null;
  current: string;
}

/**
 * Advance the visit record and return the start of "what changed": the previous
 * visit, or null on a first visit (the digest then uses its default window).
 */
export function advanceVisit(raw: string | null, now: Date): { since: string | null; next: string } {
  let visits: Visits | null = null;
  try {
    visits = raw ? (JSON.parse(raw) as Visits) : null;
  } catch {
    visits = null;
  }
  const nowIso = now.toISOString();
  const currentTime = visits?.current ? new Date(visits.current).getTime() : Number.NaN;
  if (!visits || Number.isNaN(currentTime)) {
    return { since: null, next: JSON.stringify({ previous: null, current: nowIso }) };
  }
  if (now.getTime() - currentTime > VISIT_GAP_MS) {
    return {
      since: visits.current,
      next: JSON.stringify({ previous: visits.current, current: nowIso }),
    };
  }
  return { since: visits.previous, next: JSON.stringify(visits) };
}

/* ------------------------------------------------------------------------ */
/* What changed headline.                                                    */
/* ------------------------------------------------------------------------ */

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

export interface WhatChangedInput {
  /** Start of the window (ISO). */
  since: string;
  events: DeltaEventV2[];
  /** Observation dates of the latest result per analyte. */
  resultDates: string[];
  pending: PendingItemV2[];
  now: Date;
}

export interface WhatChanged {
  /** "Since Sep 20: 1 new result, 1 open loop due soon" */
  headline: string;
  /** L0 status line: "1 thing needs a look. Everything else is steady." */
  status: string;
  /** Delta events worth one line each, newest first. */
  recent: DeltaEventV2[];
}

/** At most three parts keep the headline scannable. */
const MAX_PARTS = 3;

export function buildWhatChanged({ since, events, resultDates, pending, now }: WhatChangedInput): WhatChanged {
  const sinceTime = new Date(since).getTime();
  const sinceLabel = formatShortDate(since);

  const newResults = resultDates.filter((d) => new Date(d).getTime() >= sinceTime).length;
  const newThreads = events.filter((e) => e.category === "new_fact").length;
  const statusChanges = events.filter((e) => e.category === "lifecycle").length;
  const newLoops = events.filter(
    (e) => e.category === "open_loop" && e.ranking_reason === "New open item",
  ).length;
  const closedLoops = events.filter(
    (e) => e.category === "open_loop" && /closed|resolved/i.test(e.ranking_reason),
  ).length;
  const dueSoon = pending.filter((p) => isDueSoon(p, now)).length;

  const parts = [
    newResults > 0 && plural(newResults, "new result", "new results"),
    dueSoon > 0 && plural(dueSoon, "open loop due soon", "open loops due soon"),
    newThreads > 0 && plural(newThreads, "new thread", "new threads"),
    newLoops > 0 && plural(newLoops, "new open loop", "new open loops"),
    statusChanges > 0 && plural(statusChanges, "status update", "status updates"),
    closedLoops > 0 && plural(closedLoops, "loop closed", "loops closed"),
  ].filter((p): p is string => Boolean(p));

  const headline =
    parts.length > 0
      ? `${sinceLabel ? `Since ${sinceLabel}` : "Lately"}: ${parts.slice(0, MAX_PARTS).join(", ")}`
      : `Nothing new ${sinceLabel ? `since ${sinceLabel}` : "lately"}`;

  const recent = [...events]
    .sort((a, b) => new Date(b.occurred_at).getTime() - new Date(a.occurred_at).getTime())
    .slice(0, 3);

  return { headline, status: homeStatusLine(pending), recent };
}

/** L0 holistic status: affirming when calm, never implying medical closure. */
export function homeStatusLine(pending: PendingItemV2[]): string {
  const attention = pending.filter((p) => loopGroupOf(p.status) === "attention").length;
  if (attention === 0) {
    return "Nothing needs your attention right now. We'll surface anything that changes.";
  }
  return `${attention === 1 ? "One thing needs" : `${attention} things need`} a look. Everything else is steady.`;
}

/* ------------------------------------------------------------------------ */
/* Launcher continuity strip.                                                */
/* ------------------------------------------------------------------------ */

const CARRIED: ThreadStatus[] = ["active", "monitoring", "attention"];

export interface ContinuityCounts {
  threads: number;
  loops: number;
  noticed: number;
}

export function continuityCounts(
  threads: ThreadSummary[],
  pending: PendingItemV2[],
  noticed: ThingNoticedV1[],
  now: Date,
): ContinuityCounts {
  return {
    threads: threads.filter((t) => CARRIED.includes(t.status)).length,
    loops: pending.filter((p) => loopGroupOf(p.status) !== null).length,
    noticed: visibleThingsNoticed(noticed, now).length,
  };
}

/** "5 threads carrying forward · 1 open loop · 1 thing noticed" (zero parts dropped). */
export function continuityLine({ threads, loops, noticed }: ContinuityCounts): string {
  return [
    threads > 0 && `${plural(threads, "thread", "threads")} carrying forward`,
    loops > 0 && plural(loops, "open loop", "open loops"),
    noticed > 0 && plural(noticed, "thing noticed", "things noticed"),
  ]
    .filter(Boolean)
    .join(" · ");
}

/* ------------------------------------------------------------------------ */
/* Things noticed.                                                           */
/* ------------------------------------------------------------------------ */

/** Pending and not on a hold (the server filters too; this covers stale caches). */
export function visibleThingsNoticed(items: ThingNoticedV1[], now: Date): ThingNoticedV1[] {
  return items.filter((c) => {
    if (c.status !== "pending") return false;
    if (c.snoozed_until && new Date(c.snoozed_until).getTime() > now.getTime()) return false;
    if (c.ignored_at && new Date(c.last_seen_at).getTime() <= new Date(c.ignored_at).getTime()) {
      return false;
    }
    return true;
  });
}

/** Genesis ConcernType -> a plain noun for the reason line. */
const NOTICED_KIND: Record<string, string> = {
  symptom: "symptom",
  condition: "condition",
  lab_abnormality: "result",
  medication_issue: "medication note",
  care_gap: "care note",
  follow_up_task: "follow-up",
  question_or_worry: "question",
  procedure_or_test: "test",
};

/** Short, non-causal "why it might matter" line built from what was seen. */
export function noticedReason(c: Pick<ThingNoticedV1, "seen_count" | "first_seen_at" | "candidate_type">): string {
  const kind = NOTICED_KIND[c.candidate_type] ?? "note";
  const first = formatShortDate(c.first_seen_at);
  if (c.seen_count > 1) {
    return `You've mentioned this ${c.seen_count} times${first ? ` since ${first}` : ""}. Keeping it together could be useful context.`;
  }
  return `A ${kind} you logged${first ? ` on ${first}` : ""} could be worth following as its own thread.`;
}

/** Default "remind me later": a week from now, at 9am local. */
export function remindLaterDate(now: Date, days = 7): Date {
  const d = new Date(now.getTime() + days * DAY_MS);
  d.setHours(9, 0, 0, 0);
  return d;
}
