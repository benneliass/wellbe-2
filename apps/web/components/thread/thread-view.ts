import {
  THREAD_STATUS_LABELS,
  mapThreadStatusToStage,
  type AuthorshipMode,
  type EvidenceSource,
  type HealthThreadStatus,
  type JourneyStage,
  type MemoryLifecycleState,
  type ReviewMarkerValue,
  type SourceKind,
  type StoryEntry,
} from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import type { PendingItemV2 } from "@/lib/pending";
import type { ThreadTimelineV2, TimelineEventV2, TimelineSourceV2 } from "@/lib/thread-hooks";

type MemoryEntryV2 = components["schemas"]["MemoryEntryV2"];
type InvestigationV2 = components["schemas"]["InvestigationV2"];
type GraphNode = { id: string; type: string; label: string; attributes?: Record<string, unknown> };

const STATUSES = new Set<string>(Object.keys(THREAD_STATUS_LABELS));
const AUTHORSHIP = new Set<string>([
  "controller_authored",
  "controller_confirmed",
  "system_derived",
  "hybrid",
  "role_authored_pending_acceptance",
]);
const LIFECYCLE = new Set<string>([
  "draft",
  "visible",
  "not_current",
  "superseded_by_correction",
  "projection_stale",
]);
const REVIEW = new Set<string>([
  "patient-entered",
  "AI-summarized",
  "not-clinician-reviewed",
  "clinician-reviewed",
  "clinician-annotated",
  "ready-for-visit",
  "needs-urgent-care-consideration",
]);

export function isThreadStatus(value: string | null | undefined): value is HealthThreadStatus {
  return typeof value === "string" && STATUSES.has(value);
}

export function statusLabel(value: string | null | undefined): string {
  return isThreadStatus(value) ? THREAD_STATUS_LABELS[value] : "Updated";
}

const KIND_TO_SOURCE: Record<string, SourceKind> = {
  lab: "lab",
  document: "doc",
  photo: "doc",
  connected_source: "wearable",
  entered_by_you: "reported",
  extracted_fact: "reported",
};

function reviewMarkers(value: string | null | undefined): ReviewMarkerValue[] | undefined {
  return value && REVIEW.has(value) ? [value as ReviewMarkerValue] : undefined;
}

export function toEvidenceSource(src: TimelineSourceV2): EvidenceSource {
  return {
    id: src.source_ref_id,
    displayLabel: src.display_label,
    component: src.component,
    kind: KIND_TO_SOURCE[src.kind],
    date: src.date ?? undefined,
    confidence: typeof src.confidence === "number" ? src.confidence : undefined,
    confidenceBasis: src.confidence_basis ?? undefined,
    reviewMarkers: reviewMarkers(src.review_marker),
  };
}

export type SourceIndex = Map<string, EvidenceSource>;

export function buildSourceIndex(timeline: ThreadTimelineV2 | undefined): SourceIndex {
  return new Map((timeline?.sources ?? []).map((s) => [s.source_ref_id, toEvidenceSource(s)]));
}

/**
 * Resolve ids to evidence sources. Ids the index doesn't know still count as a
 * source; the primitives swap the blank label for "From your data", never the id.
 */
export function resolveSources(ids: readonly string[], index: SourceIndex): EvidenceSource[] {
  const seen = new Set<string>();
  const out: EvidenceSource[] = [];
  for (const id of ids) {
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push(index.get(id) ?? { id, displayLabel: "", component: "c5" });
  }
  return out;
}

function refIds(refs: readonly Record<string, unknown>[] | undefined): string[] {
  return (refs ?? [])
    .map((r) => r["source_ref_id"] ?? r["id"] ?? r["node_id"])
    .filter((v): v is string => typeof v === "string");
}

function capitalize(text: string): string {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

/**
 * Story Memory entries for the display lanes. Lane follows the stored C8
 * authorship only; an entry without one is never shown as the user's words.
 */
export function storyEntries(memories: readonly MemoryEntryV2[], index: SourceIndex): StoryEntry[] {
  return memories.map((m) => {
    const known = m.authorship_mode && AUTHORSHIP.has(m.authorship_mode);
    const authorship = (known ? m.authorship_mode : "system_derived") as AuthorshipMode;
    const voice = authorship === "controller_authored" || authorship === "controller_confirmed";
    const raw = LIFECYCLE.has(m.lifecycle_state) ? (m.lifecycle_state as MemoryLifecycleState) : "visible";
    const lifecycle: MemoryLifecycleState = raw === "visible" && m.projection_stale ? "projection_stale" : raw;
    const title = m.title || "Untitled entry";
    return {
      id: m.memory_entry_id,
      text: voice ? title : capitalize(title),
      authorship,
      lifecycle,
      date: m.created_at ?? undefined,
      reviewMarkers: known ? undefined : ["not-clinician-reviewed"],
      sources: resolveSources(refIds(m.source_refs), index),
      correction: (m.resolved_overlays ?? []).length > 0 ? { state: "corrected" } : undefined,
    };
  });
}

export function hasVoice(entries: readonly StoryEntry[]): boolean {
  return entries.some(
    (e) => e.authorship === "controller_authored" || e.authorship === "controller_confirmed",
  );
}

export interface ClarifyQuestion {
  question: string;
  /** Why WellBe is asking — always a real gap in what's stored. */
  why: string;
}

function missingItemText(item: unknown): string | null {
  if (typeof item === "string") return item.trim() || null;
  if (item && typeof item === "object") {
    const o = item as Record<string, unknown>;
    for (const key of ["question", "label", "description", "item"]) {
      const v = o[key];
      if (typeof v === "string" && v.trim()) return v.trim();
    }
  }
  return null;
}

/**
 * At most one gentle question, drawn from real gaps: an investigation's stated
 * missing context, then the absence of the user's own words. Null when nothing
 * real is missing.
 */
export function clarifyQuestion(input: {
  title: string;
  entries: readonly StoryEntry[];
  investigations: readonly InvestigationV2[];
}): ClarifyQuestion | null {
  for (const inv of input.investigations) {
    for (const item of inv.missing_context_items ?? []) {
      const text = missingItemText(item);
      if (!text) continue;
      return {
        question: text.endsWith("?") ? text : `Could you add anything about ${text.replace(/[.]$/, "")}?`,
        why: `It's missing for “${inv.primary_question}”.`,
      };
    }
  }
  const concern = input.title.toLowerCase();
  if (input.entries.length === 0) {
    return {
      question: `What's been happening with your ${concern}?`,
      why: "Nothing is kept for this thread yet.",
    };
  }
  if (!hasVoice(input.entries)) {
    return {
      question: `In your own words, how has your ${concern} been?`,
      why: "Everything here so far is WellBe's summary of what you added.",
    };
  }
  return null;
}

export function eventTitle(event: TimelineEventV2): string {
  if (event.kind === "status_changed") return `Now: ${statusLabel(event.to_status).toLowerCase()}`;
  if (event.kind === "open_loop") return `Follow-up added: ${event.title}`;
  return event.title;
}

/** The most recent real event, for the rail's "what changed" line. */
export function latestChange(timeline: ThreadTimelineV2 | undefined): TimelineEventV2 | null {
  const events = timeline?.events ?? [];
  const meaningful = events.filter((e) => e.kind !== "thread_started");
  const pool = meaningful.length > 0 ? meaningful : events;
  return pool.length > 0 ? pool[pool.length - 1]! : null;
}

export function statusHistory(timeline: ThreadTimelineV2 | undefined): HealthThreadStatus[] {
  return (timeline?.status_history ?? []).filter(isThreadStatus);
}

/** Journey stage an event belongs to, so tapping a stage can jump to it. */
export function eventStage(event: TimelineEventV2, history: readonly HealthThreadStatus[]): JourneyStage | null {
  if (event.kind === "status_changed" && isThreadStatus(event.to_status)) {
    return mapThreadStatusToStage(event.to_status);
  }
  if (event.kind === "thread_started" && history[0]) return mapThreadStatusToStage(history[0]);
  return null;
}

const WAITING_ON: Record<string, string> = {
  result_pending: "a result",
  referral_pending: "a referral",
  follow_up_due: "a follow-up",
  repeat_test_due: "a repeat test",
  post_visit_plan_check: "a post-visit check",
  normal_test_safety_net: "a check-in after a normal result",
  care_team_next_step: "your care team",
  user_next_step: "a step from you",
};

/** What an in-motion thread waits on; omitted when the status already says it. */
export function waitingOn(loops: readonly PendingItemV2[], status?: string): string | undefined {
  const first = loops[0];
  if (!first) return undefined;
  if (status === "waiting_for_result" && first.item_type === "result_pending") return undefined;
  if (status === "referred" && first.item_type === "referral_pending") return undefined;
  return WAITING_ON[first.item_type] ?? first.title;
}

/** C15 theory status in plain words about fit with the user's data. Never a verdict. */
export const THEORY_SUPPORT_WORDS: Record<string, string> = {
  unreviewed: "Not weighed against your data yet",
  needs_more_data: "Needs more data to weigh",
  partially_supported: "Partly fits your data so far",
  not_supported_by_current_data: "Doesn't fit your current data",
  contradicted_by_current_data: "Your current data points the other way",
  discuss_with_clinician: "Worth discussing with a clinician",
  clinician_reviewed: "Reviewed by a clinician",
};

export function theorySupportWords(status: string | null | undefined): string | null {
  return (status && THEORY_SUPPORT_WORDS[status]) || null;
}

/** Evidence ids a theory points at: its for/against items and the user's cited refs. */
export function theoryEvidenceIds(theory: {
  evidence_for?: Record<string, unknown>[];
  evidence_against?: Record<string, unknown>[];
  latest_evaluation?: { evidence_refs?: { id: string }[]; evidence_node_ids?: string[] } | null;
}): string[] {
  return [
    ...refIds(theory.evidence_for),
    ...refIds(theory.evidence_against),
    ...(theory.latest_evaluation?.evidence_refs ?? []).map((r) => r.id),
    ...(theory.latest_evaluation?.evidence_node_ids ?? []),
  ];
}

/** A graph node as a source: the linked concept itself, as WellBe recorded it. */
export function nodeSource(node: GraphNode, index: SourceIndex): EvidenceSource {
  const known = index.get(node.id);
  if (known) return known;
  const seen = node.attributes?.["first_seen_at"];
  return {
    id: node.id,
    displayLabel: node.label,
    component: "c5",
    date: typeof seen === "string" ? seen : undefined,
    reviewMarkers: ["AI-summarized"],
  };
}
