export type RecordKind = "note" | "document" | "result" | "other" | "hub";

/** Record kinds, never a health or attention scale. */
export const RECORD_KINDS = {
  note: { label: "Note", color: "#287d80", tint: "#c0dddd", base: "#739b9c" },
  document: { label: "Document", color: "#8056ad", tint: "#dfd0ef", base: "#a48bbd" },
  result: { label: "Result", color: "#6984bf", tint: "#d0daf0", base: "#839bc3" },
  other: { label: "Other", color: "#64874d", tint: "#e0ead2", base: "#b5c998" },
  hub: { label: "Capture hub", color: "#667185", tint: "#e1e5ec", base: "#b2bccb" },
} satisfies Record<RecordKind, { label: string; color: string; tint: string; base: string }>;
