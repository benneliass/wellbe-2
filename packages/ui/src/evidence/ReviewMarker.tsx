import { Icon } from "../Icon";
import { STATE_TOKENS } from "../tokens";
import { cx } from "./format";
import shared from "./shared.module.css";
import type { ReviewMarkerValue } from "./types";

/** Exact labels from the WEL-144 ReviewMarker table. */
export const REVIEW_MARKER_LABELS: Record<ReviewMarkerValue, string> = {
  "patient-entered": "Your words",
  "AI-summarized": "WellBe summary",
  "not-clinician-reviewed": "Not clinician-reviewed",
  "clinician-reviewed": "Clinician-reviewed",
  "clinician-annotated": "Clinician note added",
  "ready-for-visit": "Ready for visit",
  "needs-urgent-care-consideration": "Worth urgent attention",
};

const REVIEW_META: Record<ReviewMarkerValue, { icon: string; evidence: string }> = {
  "patient-entered": { icon: "message-circle", evidence: "patient_entered" },
  "AI-summarized": { icon: "file-search", evidence: "ai_summarized" },
  "not-clinician-reviewed": { icon: "info", evidence: "not_reviewed" },
  "clinician-reviewed": { icon: "badge-check", evidence: "clinician_reviewed" },
  "clinician-annotated": { icon: "clipboard-list", evidence: "clinician_reviewed" },
  "ready-for-visit": { icon: "check-circle-2", evidence: "clinician_reviewed" },
  "needs-urgent-care-consideration": { icon: "alert-circle", evidence: "urgent" },
};

export interface ReviewMarkerProps {
  value: ReviewMarkerValue;
  /**
   * Set only when the marker comes from a C10 decision carrying route_urgent.
   * Without it, `needs-urgent-care-consideration` falls back to "Needs attention".
   */
  safetyApproved?: boolean;
  className?: string;
}

/** Tells the user who stands behind a piece of text (WEL-144 §3). */
export function ReviewMarker({ value, safetyApproved = false, className }: ReviewMarkerProps) {
  const downgraded = value === "needs-urgent-care-consideration" && !safetyApproved;
  const meta = REVIEW_META[value];
  const label = downgraded ? STATE_TOKENS.needs_attention.label : REVIEW_MARKER_LABELS[value];
  const evidence = downgraded ? "attention" : meta.evidence;

  return (
    <span className={cx(shared.marker, className)} data-evidence={evidence} data-review={value}>
      <Icon name={downgraded ? "info" : meta.icon} size={14} />
      <span className={shared.srOnly}>Review: </span>
      {label}
    </span>
  );
}

export interface ReviewMarkerListProps {
  /** Every marker the render approval carries; all are shown, in order. */
  values: readonly ReviewMarkerValue[];
  safetyApproved?: boolean;
  className?: string;
}

export function ReviewMarkerList({ values, safetyApproved, className }: ReviewMarkerListProps) {
  if (values.length === 0) return null;
  return (
    <ul className={cx(shared.markerList, className)} aria-label="Review status">
      {values.map((v) => (
        <li key={v}>
          <ReviewMarker value={v} safetyApproved={safetyApproved} />
        </li>
      ))}
    </ul>
  );
}
