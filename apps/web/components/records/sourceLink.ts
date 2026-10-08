import type { SourceKind } from "@wellbe/ui";

const RESULT = "Result · ";
const FILE = "File · ";

/** Kind named on a memory source label. Unknown labels stay unlabeled. */
export function sourceKindForLabel(label: string): SourceKind | undefined {
  if (label.startsWith(RESULT) || label === "Result") return "lab";
  if (label === "Note") return "note";
  if (label === "What you reported") return "reported";
  if (label === "File" || label.startsWith(FILE)) return "doc";
  return undefined;
}

/** Page that holds this input. Notes and reported wording have no separate page. */
export function sourceHrefForLabel(label: string): string | undefined {
  if (label.startsWith(RESULT)) {
    const name = label.slice(RESULT.length).trim();
    return name ? `/results?analyte=${encodeURIComponent(name)}` : "/results";
  }
  if (label === "Result") return "/results";
  if (label.startsWith(FILE)) {
    const name = label.slice(FILE.length).trim();
    return name ? `/documents?file=${encodeURIComponent(name)}` : "/documents";
  }
  if (label === "File") return "/documents";
  return undefined;
}

/** Drawer title. One input uses its own name. Mixed inputs stay "Sources". */
export function drawerTitleForLabels(labels: readonly string[]): string {
  if (labels.length === 0) return "Sources";
  if (labels.length === 1) return labels[0]!;
  const kinds = new Set(labels.map((label) => sourceKindForLabel(label) ?? label));
  if (kinds.size !== 1) return "Sources";
  const kind = [...kinds][0];
  if (kind === "lab") return "Results";
  if (kind === "doc") return "Files";
  if (kind === "note") return "Notes";
  if (kind === "reported") return "What you reported";
  return "Sources";
}
