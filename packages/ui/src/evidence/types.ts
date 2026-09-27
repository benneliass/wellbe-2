import type { SourceType } from "../primitives/SourceChip";

/**
 * Shared shapes for the evidence primitives (docs/implementation/ui/evidence-ui-primitives.md).
 * These mirror the fields the UI needs from C13 SourceRefV2 / C10 ReviewMarker /
 * C5 confidence / C11 corrections without importing backend types into the design system.
 */

/** SourceRefV2.component — which store the source lives in. */
export type SourceComponent = "c2" | "c5" | "c16";

/** Visual kind of a source, reusing the design-system source taxonomy. */
export type SourceKind = SourceType;

/** C10 ReviewMarker values carried on RenderApprovalV2.review_markers. */
export type ReviewMarkerValue =
  | "patient-entered"
  | "AI-summarized"
  | "not-clinician-reviewed"
  | "clinician-reviewed"
  | "clinician-annotated"
  | "ready-for-visit"
  | "needs-urgent-care-consideration";

export type ConfidenceLevel = "tentative" | "moderate" | "well-supported";

export type CorrectionState = "corrected" | "superseded";

export interface CorrectionInfo {
  state: CorrectionState;
  /** Human name of who corrected it, e.g. "you" or "Dr Levi". Never an id. */
  correctedBy?: string;
  correctedAt?: string | Date;
  /** Where the preserved prior version can be viewed. */
  priorVersionHref?: string;
}

/** One backing source as the UI renders it. */
export interface EvidenceSource {
  /** Stable key for lists and callbacks. Never rendered. */
  id: string;
  /** SourceRefV2.display_label — the only label ever shown. */
  displayLabel: string;
  component: SourceComponent;
  kind?: SourceKind;
  /** Timeline date of the source. */
  date?: string | Date;
  /** Short excerpt from the source, shown in the drawer only. */
  excerpt?: string;
  /** C5 confidence, 0..1, only when the backend provided one. */
  confidence?: number;
  /** C5 confidence_basis. */
  confidenceBasis?: string;
  reviewMarkers?: ReviewMarkerValue[];
  correction?: CorrectionInfo;
  /** Source-quality tier for c16 external references. */
  qualityTier?: string;
}
