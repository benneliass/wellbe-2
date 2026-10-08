import type { components } from "@wellbe/api-client";
import type {
  AuthorshipMode,
  EvidenceSource,
  MemoryLifecycleState,
  SourceComponent,
  StoryEntry,
} from "@wellbe/ui";
import { sourceHrefForLabel, sourceKindForLabel } from "./sourceLink";

type MemoryEntryV2 = components["schemas"]["MemoryEntryV2"];

/** The six C8 memory types, in the order the Memory hub presents them. */
export const MEMORY_TYPES = [
  "story",
  "clinical",
  "pattern",
  "decision",
  "responsibility",
  "equity_access",
] as const;

export type MemoryTypeId = (typeof MEMORY_TYPES)[number];

export const MEMORY_TYPE_COPY: Record<
  MemoryTypeId,
  { title: string; description: string; empty: string }
> = {
  story: {
    title: "Your story",
    description: "What you said and experienced, kept in your words.",
    empty: "When you describe what happened through Capture, it is kept here in your own words.",
  },
  clinical: {
    title: "Clinical",
    description: "What your records and sources say.",
    empty: "Results and documents you add are kept here, each linked to where it came from.",
  },
  pattern: {
    title: "Patterns",
    description: "Trends and recurrences across time — never a diagnosis.",
    empty: "As things repeat or change over time, WellBe keeps what it noticed here for you to review.",
  },
  decision: {
    title: "Decisions",
    description: "What was considered, what is still uncertain, and what would prompt another look.",
    empty: "Choices you and your care team weigh up, and what is still open, will be kept here.",
  },
  responsibility: {
    title: "Who does what next",
    description: "Follow-ups, who owns them, and by when.",
    empty: "Follow-ups and who is looking after them will be kept here.",
  },
  equity_access: {
    title: "Access & context",
    description: "Language, cost, transport, caregiving and other context that shapes your care.",
    empty: "Anything that makes care easier or harder for you — only if you choose to add it.",
  },
};

export function isMemoryType(value: string): value is MemoryTypeId {
  return (MEMORY_TYPES as readonly string[]).includes(value);
}

const AUTHORSHIP_MODES: readonly AuthorshipMode[] = [
  "controller_authored",
  "controller_confirmed",
  "system_derived",
  "hybrid",
  "role_authored_pending_acceptance",
];

/**
 * C8 authorship for an entry. MemoryEntryV2 does not carry `authorship_mode` yet,
 * and the lane must never be inferred from memory type (WEL-146), so anything
 * without explicit authorship stays out of the Voice lane.
 */
export function memoryAuthorship(entry: MemoryEntryV2): AuthorshipMode {
  const raw = (entry as { authorship_mode?: unknown }).authorship_mode;
  return typeof raw === "string" && (AUTHORSHIP_MODES as readonly string[]).includes(raw)
    ? (raw as AuthorshipMode)
    : "system_derived";
}

const LIFECYCLE: Record<string, MemoryLifecycleState> = {
  draft: "draft",
  visible: "visible",
  not_current: "not_current",
  superseded_by_correction: "superseded_by_correction",
  projection_stale: "projection_stale",
  archived: "not_current",
};

export function memoryLifecycle(entry: MemoryEntryV2): MemoryLifecycleState {
  const state = LIFECYCLE[entry.lifecycle_state] ?? "visible";
  return state === "visible" && entry.projection_stale ? "projection_stale" : state;
}

const SOURCE_REF: Record<string, { label: string; component: SourceComponent }> = {
  c2_raw_event: { label: "Something you added", component: "c2" },
  c3_capture: { label: "Something you added", component: "c2" },
  capture: { label: "Something you added", component: "c2" },
  c4_extracted_fact: { label: "Fact from what you added", component: "c5" },
  c5_evidence_link: { label: "Linked evidence", component: "c5" },
  c6_kg_node: { label: "Linked concept", component: "c5" },
};

/** Prefer original vault wording; otherwise source_refs. Ids are keys only, never labels. */
export function memorySources(entry: MemoryEntryV2): EvidenceSource[] {
  const texts = entry.source_texts ?? [];
  if (texts.length > 0) {
    return texts.map((item, i) => ({
      id: `${item.source_ref_id}:${i}`,
      displayLabel: item.label,
      component: "c2" as const,
      kind: sourceKindForLabel(item.label) ?? ("reported" as const),
      href: sourceHrefForLabel(item.label),
      excerpt: item.text,
    }));
  }
  return (entry.source_refs ?? []).map((ref, i) => {
    const type = typeof ref.source_ref_type === "string" ? ref.source_ref_type : "";
    const meta = SOURCE_REF[type] ?? { label: "Source", component: "c5" as const };
    const id = typeof ref.source_ref_id === "string" ? ref.source_ref_id : String(i);
    return { id: `${id}:${i}`, displayLabel: meta.label, component: meta.component };
  });
}

export interface HubEntry extends StoryEntry {
  memoryType: MemoryTypeId | "other";
  threadId: string;
  threadTitle: string;
}

export function toHubEntry(entry: MemoryEntryV2, threadTitle: string): HubEntry {
  return {
    id: entry.memory_entry_id,
    text: entry.title.trim() || "Untitled memory",
    authorship: memoryAuthorship(entry),
    lifecycle: memoryLifecycle(entry),
    date: entry.created_at ?? undefined,
    sources: memorySources(entry),
    correction: (entry.resolved_overlays ?? []).length > 0 ? { state: "corrected" } : undefined,
    memoryType: isMemoryType(entry.memory_type) ? entry.memory_type : "other",
    threadId: entry.thread_id,
    threadTitle,
  };
}

function time(entry: HubEntry): number {
  const t = entry.date ? new Date(entry.date).getTime() : NaN;
  return Number.isNaN(t) ? 0 : t;
}

/** Entries grouped by memory type (hub order, "other" last), newest first within each. */
export function groupByType(entries: readonly HubEntry[]): Map<MemoryTypeId | "other", HubEntry[]> {
  const groups = new Map<MemoryTypeId | "other", HubEntry[]>();
  for (const type of [...MEMORY_TYPES, "other" as const]) groups.set(type, []);
  for (const e of entries) groups.get(e.memoryType)!.push(e);
  for (const list of groups.values()) list.sort((a, b) => time(b) - time(a));
  return groups;
}
