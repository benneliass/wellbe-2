/**
 * Plain-language labels for knowledge-graph (C6) node types and relations.
 * Raw C6 codes are never shown; unknown codes fall back to a humanized form.
 */

const NODE_TYPE_LABEL: Record<string, string> = {
  Symptom: "Symptom",
  LabResult: "Lab result",
  Lab: "Lab result",
  Observation: "Observation",
  Medication: "Medication",
  Condition: "Condition on record",
  Procedure: "Procedure",
  Encounter: "Visit",
  Document: "Document",
  Context: "Personal context",
  Theory: "Working theory",
  Investigation: "Investigation",
};

const RELATION_PHRASE: Record<string, string> = {
  co_occurs_with: "appears with",
  temporally_near: "around the same time as",
  mentioned_with: "recorded with",
  part_of: "part of",
  measured_by: "measured by",
  related_to: "related to",
  investigates: "is looking into",
};

function humanize(code: string): string {
  const spaced = code
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .trim()
    .toLowerCase();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : "Item";
}

export function nodeTypeLabel(type: string): string {
  return NODE_TYPE_LABEL[type] ?? humanize(type);
}

export function relationPhrase(relation: string): string {
  return RELATION_PHRASE[relation] ?? humanize(relation).toLowerCase();
}

const MEMORY_TYPE_LABEL: Record<string, string> = {
  story: "Your story",
  clinical: "Clinical",
  pattern: "Pattern",
  decision: "Decision",
  responsibility: "Responsibility",
};

export function memoryTypeLabel(type: string): string {
  return MEMORY_TYPE_LABEL[type] ?? humanize(type);
}

const SOURCE_REF_LABEL: Record<string, [string, string]> = {
  c4_extracted_fact: ["fact from what you added", "facts from what you added"],
  c6_kg_node: ["linked concept", "linked concepts"],
  c3_capture: ["capture", "captures"],
  capture: ["capture", "captures"],
};
const OTHER_SOURCE: [string, string] = ["source", "sources"];

/** "1 fact from what you added · 1 linked concept" for a memory's source refs. */
export function sourceRefSummary(refs: { source_ref_type?: unknown }[]): string {
  const counts = new Map<[string, string], number>();
  for (const r of refs) {
    const t = typeof r.source_ref_type === "string" ? r.source_ref_type : "";
    const label = SOURCE_REF_LABEL[t] ?? OTHER_SOURCE;
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return Array.from(counts, ([[one, many], n]) => `${n} ${n === 1 ? one : many}`).join(" · ");
}
