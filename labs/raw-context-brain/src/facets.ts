/** Kinds a route may advertise. A neighbour label may vary. These kinds do not. */
export const ROUTE_KINDS = ["neighbour", "facet", "temporal", "source", "fallback"] as const;

export type RouteKind = (typeof ROUTE_KINDS)[number];

/**
 * Fixed labels the lab already advertises.
 * A neighbour route stays out of this list because its text changes with the note.
 */
export const ALLOWED_FACET_LABELS = [
  "Earlier context",
  "Later context",
  "Original record",
  "Stop here",
] as const;

const FORBIDDEN_LABEL = /diagnosis|cause|severity|symptom|problem list/i;
const RECORD_KIND_FACET = /^Only .+s$/;
const NEIGHBOUR_LABEL = /^Open .+$/;

/** A fixed label, a record-kind facet such as "Only notes", or a varying neighbour label. */
export function isAllowedRouteLabel(label: string): boolean {
  if (FORBIDDEN_LABEL.test(label)) return false;
  if ((ALLOWED_FACET_LABELS as readonly string[]).includes(label)) return true;
  if (RECORD_KIND_FACET.test(label)) return true;
  if (NEIGHBOUR_LABEL.test(label)) return true;
  return false;
}

/** Lines are undirected associations. Color is record kind. Size is the number of links. */
export const PICTURE_CONTRACT = {
  lines: "undirected associations",
  color: "record kind",
  size: "number of links",
  legend: ["A line is an association", "the number of links", "not a diagnosis"],
} as const;

const GRAPH_FORBIDDEN = ["linkArrows", "arrowSize", "leads to"] as const;

export function assertPictureContract(html: string, graphSource: string): void {
  const legend = legendText(html);
  for (const phrase of PICTURE_CONTRACT.legend) {
    if (!legend.includes(phrase)) {
      throw new Error(`picture contract: legend misses ${phrase}`);
    }
  }
  for (const token of GRAPH_FORBIDDEN) {
    if (graphSource.includes(token)) {
      throw new Error(`picture contract: graph source contains ${token}`);
    }
  }
}

function legendText(html: string): string {
  const match = /<([a-z0-9]+)[^>]*\bclass="[^"]*\blegend\b[^"]*"[^>]*>([\s\S]*?)<\/\1>/i.exec(html);
  if (!match?.[2]) throw new Error("picture contract: html has no legend");
  return match[2];
}
