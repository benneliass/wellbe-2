import { mulberry32, sha256 } from "./text.js";
import { RawContextLab } from "./router.js";
import type { SourceArrival, TopologyKind, VaultEvent } from "./types.js";

const MOTIFS = ["sleep", "glucose", "knee", "headache", "travel"] as const;
const SOURCE_TYPES = ["note", "lab_text", "image_caption", "pdf_extract"] as const;

/** Display metadata only. Uses no random draws, so the link pattern stays put. */
function arrivalFor(
  index: number,
  sourceType: string,
): Pick<VaultEvent, "independence" | "sourceArrival" | "copiedFromId"> {
  if (sourceType === "pdf_extract" || sourceType === "image_caption") {
    return { independence: "source_family", sourceArrival: "imported", copiedFromId: null };
  }
  if (index > 0 && index % 7 === 0) {
    return { independence: "unknown", sourceArrival: "copied", copiedFromId: `n${index - 1}` };
  }
  return { independence: "source_family", sourceArrival: "typed" satisfies SourceArrival, copiedFromId: null };
}

export function generateTopology(options: {
  count: number;
  kind: TopologyKind;
  seed?: number;
  personId?: string;
  pageSize?: number;
  hopLimit?: number;
  expansionBudget?: number;
}): RawContextLab {
  const count = options.count;
  const seed = options.seed ?? 1;
  const personId = options.personId ?? "synthetic-1";
  const random = mulberry32(seed);
  const lab = new RawContextLab({
    seed,
    pageSize: options.pageSize,
    hopLimit: options.hopLimit,
    expansionBudget: options.expansionBudget,
  });

  for (let index = 0; index < count; index += 1) {
    const motif = MOTIFS[index % MOTIFS.length];
    const event: VaultEvent = {
      id: `n${index}`,
      personId,
      capturedAt: new Date(Date.UTC(2024, 0, 1) + index * 86_400_000).toISOString(),
      sourceType: SOURCE_TYPES[index % SOURCE_TYPES.length],
      text: `${motif} note ${index} sample ${Math.floor(random() * 1000)}`,
      contentHash: "",
      lineageId: `${motif}-${Math.floor(index / 5)}`,
      ...arrivalFor(index, SOURCE_TYPES[index % SOURCE_TYPES.length] ?? "note"),
      documentId: index % 11 === 0 ? `doc-${Math.floor(index / 11)}` : null,
    };
    if (options.kind === "varied") event.documentId = null;
    event.contentHash = sha256(event.text);
    lab.addFixture(event);
  }

  const link = (from: number, to: number) => {
    if (to < 0 || to >= count || from === to) return;
    lab.linkStructural(`n${from}`, `n${to}`, "recorded_association");
  };

  if (options.kind === "hub") {
    for (let index = 1; index < count; index += 1) link(0, index);
    return lab;
  }

  if (options.kind === "varied") {
    const neighbors = Array.from({ length: count }, () => new Set<number>());
    const connect = (left: number, right: number): boolean => {
      if (left === right || left < 0 || right < 0 || left >= count || right >= count) return false;
      if (neighbors[left]?.has(right)) return false;
      neighbors[left]?.add(right);
      neighbors[right]?.add(left);
      return true;
    };
    const target = new Array<number>(count);
    for (let index = 0; index < count; index += 1) {
      const roll = random();
      if (roll < 0.16) target[index] = 0;
      else if (roll < 0.42) target[index] = 1;
      else if (roll < 0.74) target[index] = 2 + Math.floor(random() * 3);
      else if (roll < 0.92) target[index] = 6 + Math.floor(random() * 7);
      else target[index] = 14 + Math.floor(random() * 10);
    }
    const stubs: number[] = [];
    target.forEach((degree, index) => {
      for (let stub = 0; stub < degree; stub += 1) stubs.push(index);
    });
    for (let index = stubs.length - 1; index > 0; index -= 1) {
      const swap = Math.floor(random() * (index + 1));
      const current = stubs[index] ?? 0;
      stubs[index] = stubs[swap] ?? 0;
      stubs[swap] = current;
    }
    if (stubs.length % 2 === 1) stubs.pop();
    for (let index = 0; index < stubs.length; index += 2) {
      const left = stubs[index];
      const right = stubs[index + 1];
      if (left === undefined || right === undefined) continue;
      connect(left, right);
    }
    const hubCount = Math.max(3, Math.min(8, Math.round(count / 40)));
    const hubs = [...neighbors.keys()].sort(
      (left, right) => (neighbors[right]?.size ?? 0) - (neighbors[left]?.size ?? 0),
    ).slice(0, hubCount);
    for (const hub of hubs) {
      const goal = 30 + Math.floor(random() * 21);
      const others = [...neighbors.keys()];
      for (let index = others.length - 1; index > 0; index -= 1) {
        const swap = Math.floor(random() * (index + 1));
        const current = others[index] ?? 0;
        others[index] = others[swap] ?? 0;
        others[swap] = current;
      }
      for (const other of others) {
        if ((neighbors[hub]?.size ?? 0) >= goal) break;
        connect(hub, other);
      }
    }
    for (let left = 0; left < count; left += 1) {
      for (const right of neighbors[left] ?? []) {
        if (left < right) link(left, right);
      }
    }
    return lab;
  }

  for (let index = 1; index < count; index += 1) {
    if (options.kind === "sparse" && index % 17 === 0) continue;
    link(index - 1, index);
    if (options.kind === "dense") {
      link(index, index + 1);
      link(index, index + 2);
    }
    if (options.kind === "cyclic" && index % 5 === 0) link(index, index - 3);
  }
  return lab;
}
