"use client";

import { Chip, Icon, ReviewMarkerList, SourceMarker, type EvidenceSource } from "@wellbe/ui";
import { formatShortDate } from "@/lib/adapters";
import { describePendingItem } from "@/lib/pending";
import type { TimelineEventV2 } from "@/lib/thread-hooks";
import { eventTitle, resolveSources, type SourceIndex } from "./thread-view";
import styles from "./ThreadDetailLive.module.css";

const KIND_ICON: Record<TimelineEventV2["kind"], string> = {
  thread_started: "folder",
  status_changed: "activity",
  capture: "message-circle",
  open_loop: "clock",
};

export function timelineAnchor(eventId: string): string {
  return `timeline-${eventId.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

/** The thread's real events, oldest first. Every sourced event opens its evidence. */
export function LiveTimeline({
  events,
  index,
  onOpenEvidence,
}: {
  events: readonly TimelineEventV2[];
  index: SourceIndex;
  onOpenEvidence: (title: string, claim: string, sources: EvidenceSource[]) => void;
}) {
  if (events.length === 0) {
    return <p className={styles.muted}>Nothing has happened on this thread yet.</p>;
  }
  return (
    <ol className={styles.timeline} aria-label="Thread timeline">
      {events.map((ev) => {
        const title = eventTitle(ev);
        const when = formatShortDate(ev.occurred_at);
        const sources = resolveSources(ev.source_ref_ids ?? [], index);
        const lead = sources[0];
        const loop =
          ev.kind === "open_loop" && ev.item_status
            ? describePendingItem({ status: ev.item_status, due_at: ev.due_at ?? null })
            : null;
        return (
          <li key={ev.event_id} id={timelineAnchor(ev.event_id)} className={styles.tlItem} tabIndex={-1}>
            <span className={styles.tlNode} aria-hidden="true">
              <Icon name={KIND_ICON[ev.kind]} size={14} />
            </span>
            <div className={styles.tlBody}>
              <div className={styles.tlHead}>
                <span className={styles.tlTitle}>{title}</span>
                {when && (
                  <time className={styles.tlDate} dateTime={ev.occurred_at}>
                    {when}
                  </time>
                )}
              </div>
              {ev.detail && <p className={styles.tlDetail}>{ev.detail}</p>}
              {ev.kind === "status_changed" && ev.actor && (
                <p className={styles.tlDetail}>{ev.actor === "you" ? "Changed by you" : "Updated by WellBe"}</p>
              )}
              {(lead || loop) && (
                <div className={styles.tlMeta}>
                  {loop && (
                    <Chip size="sm" tone={loop.tone}>
                      {loop.label}
                    </Chip>
                  )}
                  {lead?.reviewMarkers && <ReviewMarkerList values={lead.reviewMarkers} />}
                  {lead && (
                    <SourceMarker
                      displayLabel={lead.displayLabel}
                      component={lead.component}
                      kind={lead.kind}
                      date={lead.date}
                      count={sources.length}
                      onOpen={() => onOpenEvidence("Where this came from", title, sources)}
                    />
                  )}
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
