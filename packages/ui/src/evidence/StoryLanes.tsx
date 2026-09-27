"use client";

import { useId } from "react";
import { Button } from "../primitives/Button";
import { CorrectionMarker } from "./CorrectionMarker";
import { cx, formatEvidenceDate } from "./format";
import { ReviewMarkerList } from "./ReviewMarker";
import { SourceMarker } from "./SourceMarker";
import shared from "./shared.module.css";
import styles from "./StoryLanes.module.css";
import type { CorrectionInfo, EvidenceSource, ReviewMarkerValue } from "./types";

/** C8 AuthorshipMode. */
export type AuthorshipMode =
  | "controller_authored"
  | "controller_confirmed"
  | "system_derived"
  | "hybrid"
  | "role_authored_pending_acceptance";

/** C8 MemoryLifecycleState. */
export type MemoryLifecycleState =
  | "draft"
  | "visible"
  | "not_current"
  | "superseded_by_correction"
  | "projection_stale";

export type StoryLane = "voice" | "derived" | "shared_in";

const AUTHORSHIP_TO_LANE: Record<AuthorshipMode, StoryLane> = {
  controller_authored: "voice",
  controller_confirmed: "voice",
  system_derived: "derived",
  hybrid: "derived",
  role_authored_pending_acceptance: "shared_in",
};

/** Lane is decided by AuthorshipMode only, never by memory type (WEL-146). */
export function laneForAuthorship(mode: AuthorshipMode): StoryLane {
  return AUTHORSHIP_TO_LANE[mode];
}

export const STORY_LANE_COPY: Record<StoryLane, { title: string; description: string }> = {
  voice: { title: "Your voice", description: "What you said or confirmed, in your words." },
  derived: { title: "WellBe summaries", description: "Summarized by WellBe from your sources." },
  shared_in: {
    title: "Shared in",
    description: "Added by someone you gave access to. You decide if it joins your story.",
  },
};

export const LIFECYCLE_LABELS: Record<Exclude<MemoryLifecycleState, "visible">, string> = {
  draft: "Not yet saved to your story",
  not_current: "Older note",
  superseded_by_correction: "Replaced by a correction",
  projection_stale: "Updating",
};

export interface StoryEntry {
  id: string;
  /** Verbatim text for Voice entries; summary text for Derived/Shared-in. */
  text: string;
  authorship: AuthorshipMode;
  lifecycle?: MemoryLifecycleState;
  date?: string | Date;
  /** For `hybrid`: the user-quoted portion, shown as an attributed inline quote. */
  quotedText?: string;
  /** Defaults: Voice → patient-entered; Derived → AI-summarized + not-clinician-reviewed. */
  reviewMarkers?: ReviewMarkerValue[];
  sources?: EvidenceSource[];
  /** Shared-in: who added it, e.g. "Dr Levi (your GP)". */
  origin?: string;
  correction?: CorrectionInfo;
}

export interface StoryLanesProps {
  /** Entries in display order (relevance, then recency, is the caller's job). */
  entries: readonly StoryEntry[];
  onOpenSources?: (entry: StoryEntry) => void;
  onAccept?: (entry: StoryEntry) => void;
  onDecline?: (entry: StoryEntry) => void;
  onOpenCorrection?: (entry: StoryEntry) => void;
  /** Entry point shown in the Voice lane; always writes as controller_authored. */
  onAddToStory?: () => void;
  className?: string;
}

const DEFAULT_MARKERS: Record<StoryLane, ReviewMarkerValue[]> = {
  voice: ["patient-entered"],
  derived: ["AI-summarized", "not-clinician-reviewed"],
  shared_in: [],
};

/**
 * Story Memory in three labeled authorship lanes (WEL-146): the user's own words,
 * WellBe's summaries, and grant-authored entries awaiting the user's decision.
 */
export function StoryLanes({
  entries,
  onOpenSources,
  onAccept,
  onDecline,
  onOpenCorrection,
  onAddToStory,
  className,
}: StoryLanesProps) {
  const baseId = useId();
  const byLane: Record<StoryLane, StoryEntry[]> = { voice: [], derived: [], shared_in: [] };
  for (const entry of entries) byLane[laneForAuthorship(entry.authorship)].push(entry);

  const lanes: StoryLane[] = ["voice", "derived", "shared_in"];

  return (
    <div className={cx(styles.lanes, className)}>
      {lanes.map((lane) => {
        const items = byLane[lane];
        if (lane !== "voice" && items.length === 0) return null;
        const headingId = `${baseId}-${lane}`;
        const copy = STORY_LANE_COPY[lane];
        return (
          <section key={lane} className={styles.lane} data-lane={lane} aria-labelledby={headingId}>
            <header className={styles.laneHead}>
              <h3 id={headingId} className={styles.laneTitle}>
                {copy.title}
              </h3>
              <p className={styles.laneDescription}>{copy.description}</p>
            </header>
            {items.length > 0 && (
              <ul className={styles.entries}>
                {items.map((entry) => (
                  <li key={entry.id}>
                    <Entry
                      entry={entry}
                      lane={lane}
                      onOpenSources={onOpenSources}
                      onAccept={onAccept}
                      onDecline={onDecline}
                      onOpenCorrection={onOpenCorrection}
                    />
                  </li>
                ))}
              </ul>
            )}
            {lane === "voice" && items.length === 0 && (
              <p className={styles.empty}>Nothing in your own words yet.</p>
            )}
            {lane === "voice" && onAddToStory && (
              <div>
                <Button variant="tertiary" icon="plus" onClick={onAddToStory}>
                  Add to your story
                </Button>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}

interface EntryProps {
  entry: StoryEntry;
  lane: StoryLane;
  onOpenSources?: (entry: StoryEntry) => void;
  onAccept?: (entry: StoryEntry) => void;
  onDecline?: (entry: StoryEntry) => void;
  onOpenCorrection?: (entry: StoryEntry) => void;
}

function Entry({ entry, lane, onOpenSources, onAccept, onDecline, onOpenCorrection }: EntryProps) {
  const when = formatEvidenceDate(entry.date);
  const lifecycle = entry.lifecycle ?? "visible";
  const markers = entry.reviewMarkers ?? DEFAULT_MARKERS[lane];
  const sources = entry.sources ?? [];
  const lead = sources[0];
  const correction: CorrectionInfo | undefined =
    entry.correction ?? (lifecycle === "superseded_by_correction" ? { state: "superseded" } : undefined);

  return (
    <article className={styles.entry} data-lane={lane} data-lifecycle={lifecycle}>
      {lane === "shared_in" && entry.origin && <p className={styles.origin}>From {entry.origin}</p>}

      {lane === "voice" ? (
        <blockquote className={styles.quote}>
          <p>{entry.text}</p>
        </blockquote>
      ) : (
        <p className={styles.summary}>{entry.text}</p>
      )}

      {lane === "derived" && entry.authorship === "hybrid" && entry.quotedText && (
        <p className={styles.hybridQuote}>
          <span className={styles.quoteLabel}>Your words:</span> <q>{entry.quotedText}</q>
        </p>
      )}

      <div className={styles.meta}>
        <ReviewMarkerList values={markers} />
        {when && (
          <time className={styles.date} dateTime={when.iso}>
            {when.label}
          </time>
        )}
        {lifecycle !== "visible" && lifecycle !== "superseded_by_correction" && (
          <span className={styles.lifecycle}>{LIFECYCLE_LABELS[lifecycle]}</span>
        )}
        {lead && (
          <SourceMarker
            displayLabel={lead.displayLabel}
            component={lead.component}
            kind={lead.kind}
            date={lead.date}
            count={sources.length}
            onOpen={onOpenSources ? () => onOpenSources(entry) : undefined}
          />
        )}
        {correction && (
          <CorrectionMarker
            {...correction}
            onOpenHistory={onOpenCorrection ? () => onOpenCorrection(entry) : undefined}
          />
        )}
      </div>

      {lane === "shared_in" && (onAccept || onDecline) && (
        <div className={styles.actions}>
          {onAccept && (
            <Button variant="secondary" onClick={() => onAccept(entry)}>
              Accept
              <span className={shared.srOnly}> into your story</span>
            </Button>
          )}
          {onDecline && (
            <Button variant="ghost" onClick={() => onDecline(entry)}>
              Decline
            </Button>
          )}
        </div>
      )}
    </article>
  );
}
