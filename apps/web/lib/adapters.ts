import type { components } from "@wellbe/api-client";
import type { ThreadStatus, ThreadSummary } from "./types";

type ThreadV1 = components["schemas"]["ThreadV1"];

/**
 * Map the backend HealthThreadStatus lifecycle onto the UI's calmer status set.
 * HealthThreadStatus is defined in docs/system-design/health_thread_state_machine.md.
 * Unknown/future statuses fall back to "active" so the thread still renders.
 */
const STATUS_MAP: Record<string, ThreadStatus> = {
  draft: "active",
  active_unresolved: "active",
  reopened: "active",
  waiting_for_result: "monitoring",
  referred: "monitoring",
  watchful_waiting: "monitoring",
  chronic_monitoring: "monitoring",
  escalated: "attention",
  explained: "resolved",
  closed: "closed",
  archived: "closed",
};

export function mapThreadStatus(raw: string): ThreadStatus {
  return STATUS_MAP[raw] ?? "active";
}

/** Short, human date ("May 12"). Returns "" for an unparseable input. */
export function formatShortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(d);
}

export function toThreadSummary(t: ThreadV1): ThreadSummary {
  const started = formatShortDate(t.created_at);
  const updated = formatShortDate(t.updated_at);
  return {
    id: t.thread_id,
    title: t.title,
    status: mapThreadStatus(t.status),
    rawStatus: t.status,
    started: started ? `Started ${started}` : "Started recently",
    updated: updated ? `Updated ${updated}` : "Updated recently",
  };
}
