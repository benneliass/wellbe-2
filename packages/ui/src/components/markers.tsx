import type { CSSProperties, ReactNode } from "react";

/**
 * Evidence UI primitives per docs/implementation/ui/evidence-ui-primitives.md.
 * Each marker carries meaning via icon + text (never color-only) and is compact
 * at shallow disclosure, resolving to the evidence drawer at depth.
 */

const chip: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "var(--wb-space-1)",
  padding: "1px var(--wb-space-2)",
  borderRadius: "var(--wb-radius-sm)",
  fontSize: "var(--wb-text-xs)",
  background: "var(--wb-surface-muted)",
  color: "var(--wb-text-muted)",
  border: "1px solid var(--wb-border)",
};

function Chip({ icon, children, onActivate, title }: { icon: string; children: ReactNode; onActivate?: () => void; title?: string }) {
  if (onActivate) {
    return (
      <button type="button" style={{ ...chip, cursor: "pointer", font: "inherit", fontSize: "var(--wb-text-xs)" }} onClick={onActivate} title={title}>
        <span aria-hidden="true">{icon}</span>
        {children}
      </button>
    );
  }
  return (
    <span style={chip} title={title}>
      <span aria-hidden="true">{icon}</span>
      {children}
    </span>
  );
}

type SourceComponent = "c2" | "c5" | "c16";
const SOURCE_LABEL: Record<SourceComponent, string> = {
  c2: "your record",
  c5: "from your data",
  c16: "external reference",
};

export function SourceMarker({ count = 1, topComponent = "c5", onOpen }: { count?: number; topComponent?: SourceComponent; onOpen?: () => void }) {
  const label = count > 1 ? `${count} sources` : SOURCE_LABEL[topComponent];
  return <Chip icon="🔗" onActivate={onOpen} title="View source">{label}</Chip>;
}

export type ReviewMarkerValue =
  | "patient-entered"
  | "AI-summarized"
  | "not-clinician-reviewed"
  | "clinician-reviewed"
  | "clinician-annotated"
  | "ready-for-visit"
  | "needs-urgent-care-consideration";

const REVIEW_LABEL: Record<ReviewMarkerValue, string> = {
  "patient-entered": "Your words",
  "AI-summarized": "WellBe summary",
  "not-clinician-reviewed": "Not clinician-reviewed",
  "clinician-reviewed": "Clinician-reviewed",
  "clinician-annotated": "Clinician note added",
  "ready-for-visit": "Ready for visit",
  "needs-urgent-care-consideration": "Worth urgent attention",
};

export function ReviewMarker({ value }: { value: ReviewMarkerValue }) {
  return <Chip icon="✔">{REVIEW_LABEL[value]}</Chip>;
}

export type ConfidenceLevel = "tentative" | "moderate" | "well-supported";
const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  tentative: "Early signal",
  moderate: "Some support",
  "well-supported": "Well supported",
};

/** Bucket a 0..1 C5 confidence into a display level. */
export function bucketConfidence(score: number): ConfidenceLevel {
  if (score < 0.4) return "tentative";
  if (score <= 0.75) return "moderate";
  return "well-supported";
}

export function ConfidenceMeter({ level, basis }: { level: ConfidenceLevel; basis?: string }) {
  return <Chip icon="▱" title={basis}>{CONFIDENCE_LABEL[level]}</Chip>;
}

export function CorrectionMarker({ state, onOpenHistory }: { state: "corrected" | "superseded"; onOpenHistory?: () => void }) {
  const label = state === "corrected" ? "Corrected" : "Superseded";
  return <Chip icon="✎" onActivate={onOpenHistory} title="View correction history">{label}</Chip>;
}
