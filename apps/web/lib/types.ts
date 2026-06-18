import type { SourceType } from "@wellbe/ui";

/**
 * Domain types for the patient workspace UI.
 *
 * These intentionally mirror the shape the screens render today (mock data) and
 * are the contract the real API layer (@wellbe/api-client, WEL-150) will adapt
 * to. Keeping them here means swapping mock -> API is a change in `mock-data.ts`
 * only, not in every component.
 */

export type ThreadStatus =
  | "active"
  | "monitoring"
  | "attention"
  | "resolved"
  | "paused"
  | "closed";

export type RiskLevel = "urgent" | "high" | "medium" | "low" | "informational";

export type EventType = "lab" | "note" | "doc" | "reported" | "wearable" | "appointment";

/** Lifecycle state shared by status-rail steps and timeline events. */
export type StepState = "done" | "current" | "attention" | "upcoming";

export type ReviewKind = "verified" | "clinician" | "ai";

export type MetricDirection = "good" | "bad";

export interface ThreadMetric {
  label: string;
  value: string;
  unit: string;
  delta: string | null;
  dir?: MetricDirection;
}

export interface RailStep {
  label: string;
  state: StepState;
  meta: string;
}

export interface ThreadEvent {
  type: EventType;
  time: string;
  title: string;
  detail: string;
  state: StepState;
  conf?: number;
  review?: ReviewKind;
}

export interface EvidenceItem {
  src: SourceType;
  title: string;
  author: string;
  date: string;
  conf: number;
}

export interface Thread {
  id: string;
  title: string;
  status: ThreadStatus;
  question: string;
  started: string;
  updated: string;
  risk: RiskLevel;
  changed: string;
  metrics: ThreadMetric[];
  rail: RailStep[];
  events: ThreadEvent[];
  evidence: EvidenceItem[];
}

/**
 * Lightweight thread shape backed by the real `/v1/threads` list endpoint
 * (`ThreadV1`), which exposes id/title/status/dates only. The rich `Thread`
 * shape above (timeline, evidence, rail, metrics) has no list/detail endpoint
 * yet, so the thread LIST and continuity Home consume this summary while the
 * detail demo keeps the rich mock until a detail endpoint lands.
 */
export interface ThreadSummary {
  id: string;
  title: string;
  status: ThreadStatus;
  /** The original HealthThreadStatus value from the API, before UI mapping. */
  rawStatus: string;
  started: string;
  updated: string;
  /** Raw ISO timestamps, kept for client-side sorting (display uses started/updated). */
  createdAt: string;
  updatedAt: string;
}
