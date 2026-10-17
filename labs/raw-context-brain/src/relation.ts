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

/** Names a source the way Memory does: Note, Result, Image, or File. */
export function sourceName(sourceType: string): string {
  if (sourceType === "note") return "Note";
  if (sourceType === "lab_text") return "Result";
  if (sourceType === "image_caption") return "Image";
  if (sourceType === "pdf_extract") return "File";
  return "Record";
}
