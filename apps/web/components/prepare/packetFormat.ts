import type { components } from "@wellbe/api-client";
import type { EvidenceSource, ReviewMarkerValue, SourceComponent, SourceKind } from "@wellbe/ui";

export type VisitPacket = components["schemas"]["VisitPacketV2"];
export type Statement = components["schemas"]["VisitPacketStatementV2"];
type PacketSourceRef = components["schemas"]["PacketSourceRef"];

export const LAYER_LABELS: Record<string, string> = {
  patient_prep: "What you want to raise",
  summary: "Source-linked summary",
};

export const ABSENCE_LABELS: Record<string, string> = {
  known_absent: "Known: none",
  not_asked: "Not asked yet",
  unavailable: "Not available",
  masked: "Hidden by you",
};

/** Who stands behind a statement, as C10 review markers (never hidden to look authoritative). */
export function reviewMarkersFor(statement: Statement): ReviewMarkerValue[] {
  switch (statement.classification) {
    case "patient_reported":
      return ["patient-entered"];
    case "generated_synthesis":
    case "generated_inference":
      return ["AI-summarized", "not-clinician-reviewed"];
    default:
      return ["not-clinician-reviewed"];
  }
}

const REF_COMPONENT: Record<string, SourceComponent> = {
  record_scan: "c2",
  patient_entered: "c5",
  health_thread: "c5",
  pending_item: "c5",
};

const REF_KIND: Record<string, SourceKind> = {
  record_scan: "doc",
  patient_entered: "reported",
};

/** PacketSourceRef -> the evidence primitives' source shape (labels only, never ids). */
export function toEvidenceSource(
  statement: Statement,
  ref: PacketSourceRef,
  index: number,
): EvidenceSource {
  return {
    id: `${statement.statement_id}:${index}`,
    displayLabel: ref.label ?? "",
    component: REF_COMPONENT[ref.ref_type] ?? "c5",
    kind: REF_KIND[ref.ref_type],
    reviewMarkers: reviewMarkersFor(statement),
  };
}

export function isEditable(statement: Statement): boolean {
  return statement.layer === "patient_prep";
}
