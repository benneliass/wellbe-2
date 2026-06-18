import type { Tone } from "@wellbe/ui";
import type { EventType, ReviewKind, RiskLevel, ThreadStatus } from "./types";

export interface StatusMeta {
  tone: Tone;
  icon: string;
  label: string;
}

export const STATUS_META: Record<ThreadStatus, StatusMeta> = {
  active: { tone: "teal", icon: "activity", label: "Active" },
  monitoring: { tone: "tealmid", icon: "line-chart", label: "Monitoring" },
  attention: { tone: "amber", icon: "alert-circle", label: "Needs attention" },
  resolved: { tone: "green", icon: "check-circle-2", label: "Resolved" },
  paused: { tone: "violet", icon: "pause", label: "Paused" },
  closed: { tone: "neutral", icon: "lock", label: "Closed" },
};

export interface RiskMeta {
  tone: Tone;
  label: string;
}

export const RISK_META: Record<RiskLevel, RiskMeta> = {
  urgent: { tone: "danger", label: "Urgent" },
  high: { tone: "orange", label: "High" },
  medium: { tone: "amber", label: "Medium" },
  low: { tone: "green", label: "Low" },
  informational: { tone: "teal", label: "Informational" },
};

export interface EventMeta {
  icon: string;
  tone: Tone;
}

export const EVENT_META: Record<EventType, EventMeta> = {
  lab: { icon: "flask-conical", tone: "teal" },
  note: { icon: "clipboard-list", tone: "tealmid" },
  doc: { icon: "file-text", tone: "violet" },
  reported: { icon: "message-circle", tone: "amber" },
  wearable: { icon: "heart-pulse", tone: "green" },
  appointment: { icon: "calendar", tone: "teal" },
};

export interface ReviewMeta {
  tone: Tone;
  icon: string;
  label: string;
}

export const REVIEW_META: Record<ReviewKind, ReviewMeta> = {
  verified: { tone: "green", icon: "badge-check", label: "Verified" },
  clinician: { tone: "tealmid", icon: "users", label: "Clinician reviewed" },
  ai: { tone: "violet", icon: "sparkles", label: "AI extracted" },
};

export interface NavItem {
  id: string;
  icon: string;
  label: string;
  href: string;
  /** Not yet built — rendered but inert. */
  disabled?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "home", icon: "home", label: "Home", href: "/" },
  { id: "threads", icon: "list", label: "Threads", href: "/workspace" },
  { id: "memory", icon: "book", label: "Memory", href: "/memory" },
  { id: "results", icon: "bar-chart-3", label: "Results", href: "/results" },
  { id: "documents", icon: "file-text", label: "Documents", href: "/documents" },
  { id: "appointments", icon: "calendar", label: "Appointments", href: "/appointments" },
];

export interface CaptureType {
  id: string;
  icon: string;
  label: string;
  hint: string;
}

export const CAPTURE_TYPES: CaptureType[] = [
  { id: "reported", icon: "message-circle", label: "Log a symptom", hint: "How you feel right now" },
  { id: "lab", icon: "flask-conical", label: "Add a result", hint: "Lab or test value" },
  { id: "doc", icon: "file-text", label: "Upload a document", hint: "PDF, photo, or report" },
  { id: "note", icon: "clipboard-list", label: "Write a note", hint: "A thought or question" },
];

export interface LaunchAction {
  id: string;
  icon: string;
  title: string;
  sub: string;
  tone?: "alert";
  /**
   * Destination route. Omitted for `log`, which opens the capture modal instead
   * of navigating. Every other action routes here — no silent fall-through.
   */
  href?: string;
}

export const LAUNCH_ACTIONS: LaunchAction[] = [
  { id: "triage", icon: "heart-pulse", title: "Something feels off", sub: "Triage", tone: "alert", href: "/triage" },
  { id: "log", icon: "pencil", title: "Log something", sub: "Quick Log" },
  { id: "delta", icon: "activity", title: "What changed?", sub: "Delta Digest", href: "/delta" },
  { id: "pattern", icon: "bar-chart-3", title: "Check my patterns", sub: "Pattern Check", href: "/patterns" },
  { id: "prep", icon: "user", title: "Prepare for appointment", sub: "Doctor Prep", href: "/prepare" },
  { id: "graph", icon: "git-fork", title: "Open the graph", sub: "Deep Dive", href: "/graph" },
];
