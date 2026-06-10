import type { SourceType, Tone } from "@wellbe/ui";

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

/**
 * A single body-system signal that rolls up into the Launcher "signals" summary
 * line. Today these are mock rows (see SIGNALS in `meta.ts`); this is the shape a
 * real signals/vitals endpoint would adapt to.
 */
export interface Signal {
  id: string;
  label: string;
  value: string;
  status: string;
  tone: Tone;
  /** 0–5 confidence in the underlying data. */
  conf: number;
}

export interface SignalsSummary {
  headline: string;
  detail: string;
  signals: Signal[];
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
