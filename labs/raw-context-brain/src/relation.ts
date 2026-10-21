import type { Independence, Origin, Relation, SourceArrival } from "./types.js";

/** One relation from the lab set. Conflict without comparable claim, time, units, and subject stays a possible association. */
export function mapRelation(origin: Origin, reasonCode: string): Relation {
  if (origin === "user_correction" && reasonCode !== "withdrawal") return "explicitly_linked";
  if (reasonCode === "membership") return "same_record_group";
  if (reasonCode === "temporal_neighbour") return "near_in_time";
  if (reasonCode === "derived_or_copied") return "derived_or_copied";
  return "possible_semantic_association";
}

export const RELATION_LABEL: Record<Relation, string> = {
  explicitly_linked: "you linked these",
  same_record_group: "same record",
  derived_or_copied: "copied from another record",
  near_in_time: "close in time",
  possible_semantic_association: "may relate",
  possible_inconsistency: "may not match",
};

/** How the note entered: typed, copied, or imported. */
export function arrivalName(arrival: SourceArrival | undefined): string {
  if (arrival === "typed") return "Typed";
  if (arrival === "copied") return "Copied";
  if (arrival === "imported") return "Imported";
  return "—";
}

/** Known independence can support a source family. Unknown must not. */
export function independenceName(independence: Independence | undefined): string {
  if (independence === "unknown") return "Not known";
  return "Known";
}

/** One record kind: the name on the key, the swatch, and the circle fill. */
export const RECORD_KINDS = {
  note: { label: "Note", hex: "#ed9e38", rgb: [0.93, 0.62, 0.22] },
  lab_text: { label: "Result", hex: "#5494e6", rgb: [0.33, 0.58, 0.9] },
  image_caption: { label: "Image", hex: "#59c77a", rgb: [0.35, 0.78, 0.48] },
  pdf_extract: { label: "File", hex: "#b86bd1", rgb: [0.72, 0.42, 0.82] },
  hub: { label: "Record", hex: "#9ea8b3", rgb: [0.62, 0.66, 0.7] },
} as const;

export const LEGEND_KINDS = ["note", "lab_text", "image_caption", "pdf_extract"] as const;

/** Names a source the way Memory does: Note, Result, Image, or File. */
export function sourceName(sourceType: string): string {
  const known = RECORD_KINDS[sourceType as keyof typeof RECORD_KINDS];
  return known?.label ?? "Record";
}
