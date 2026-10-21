import { RawContextLab } from "./router.js";
import { sha256 } from "./text.js";
import type { Independence, Relation, SourceArrival, VaultEvent } from "./types.js";

/** One person from the benchmark dossiers, separated with lab-node-separation-v1. */
export interface CaseFile {
  principles: string;
  caseId: string;
  personId: string;
  label: string;
  mode: string;
  nodes: CaseNode[];
  links: CaseLink[];
}

export interface CaseNode {
  id: string;
  sourceEventId: string;
  sequence: number;
  sourceType: string;
  text: string;
  keyword: string;
  capturedAt: string;
  relativeTime: string;
  lineageId: string;
  independence: Independence;
  sourceArrival: SourceArrival;
  copiedFromId: string | null;
}

export interface CaseLink {
  from: string;
  to: string;
  relation: Relation;
  reason: string;
}

/** Read every `lab_nodes.json` the dev server finds under the research cases directory. */
export async function loadCasePeople(): Promise<CaseFile[]> {
  const response = await fetch("/lab-cases");
  if (!response.ok) throw new Error("The research cases could not be loaded.");
  const people = (await response.json()) as CaseFile[];
  return people.sort((left, right) => left.caseId.localeCompare(right.caseId));
}

export function labFromCase(file: CaseFile): RawContextLab {
  const lab = new RawContextLab({ seed: 7, pageSize: 1, hopLimit: 24, expansionBudget: 400 });
  const nodes = [...file.nodes].sort((left, right) => left.sequence - right.sequence);
  for (const node of nodes) {
    const event: VaultEvent = {
      id: node.id,
      personId: file.personId,
      capturedAt: node.capturedAt,
      sourceType: node.sourceType,
      text: node.text,
      keyword: node.keyword,
      contentHash: sha256(node.text),
      lineageId: node.lineageId,
      independence: node.independence,
      sourceArrival: node.sourceArrival,
      copiedFromId: node.copiedFromId,
      documentId: null,
    };
    lab.addFixture(event);
  }
  for (const link of file.links) {
    lab.linkStructural(link.from, link.to, reasonCode(link.relation));
  }
  return lab;
}

function reasonCode(relation: Relation): string {
  if (relation === "same_record_group") return "membership";
  if (relation === "near_in_time") return "temporal_neighbour";
  if (relation === "derived_or_copied") return "derived_or_copied";
  return "recorded_association";
}
