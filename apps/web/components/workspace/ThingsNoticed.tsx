"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon, RelevanceCandidateCard, type EvidenceSource } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { formatShortDate } from "@/lib/adapters";
import { useThingsNoticed } from "@/lib/hooks";
import { noticedReason, remindLaterDate, visibleThingsNoticed } from "@/lib/home-continuity";
import { useThingNoticedAction, type NoticedAction } from "@/lib/home-hooks";
import styles from "./ThingsNoticed.module.css";

type ThingNoticedV1 = components["schemas"]["ThingNoticedV1"];

/** Cards shown before "Show more" — Home stays a short read. */
const INITIAL_VISIBLE = 2;

interface Feedback {
  tone: "ok" | "error";
  text: string;
  threadId?: string;
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

function sourcesFor(c: ThingNoticedV1): EvidenceSource[] {
  const sources: EvidenceSource[] = [];
  if (c.source_capture_count > 0) {
    sources.push({
      id: `${c.candidate_id}:captures`,
      displayLabel: `${plural(c.source_capture_count, "entry", "entries")} you logged`,
      component: "c2",
      kind: "reported",
      date: c.last_seen_at,
    });
  }
  if (c.source_fact_count > 0) {
    sources.push({
      id: `${c.candidate_id}:facts`,
      displayLabel: `${plural(c.source_fact_count, "detail", "details")} picked out`,
      component: "c5",
      kind: "note",
    });
  }
  return sources;
}

function feedbackFor(action: NoticedAction, title: string, until?: Date): string {
  switch (action) {
    case "accept":
      return `Started a health thread for “${title}”.`;
    case "reject":
      return `Set aside “${title}”. It won't come back.`;
    case "ignore":
      return `Ignored “${title}” for now. It comes back only if it's noticed again.`;
    case "remind":
      return `We'll bring “${title}” back on ${until ? formatShortDate(until.toISOString()) : "a later date"}.`;
  }
}

/**
 * "Things noticed" (/v1/things-noticed): possible connections WellBe spotted in
 * what the person added, shown as relevance candidate cards. Each offers accept
 * (open a thread), reject, ignore for now, or remind later. Nothing becomes a
 * thread without the person's say-so, and nothing here is a diagnosis.
 */
export function ThingsNoticed() {
  const { data, isLoading, isError } = useThingsNoticed();
  const act = useThingNoticedAction();
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [expanded, setExpanded] = useState(false);

  const visible = visibleThingsNoticed(data ?? [], new Date());
  if (isLoading || isError || (visible.length === 0 && !feedback)) return null;

  const shown = expanded ? visible : visible.slice(0, INITIAL_VISIBLE);
  const hidden = visible.length - shown.length;

  function run(c: ThingNoticedV1, action: NoticedAction) {
    const until = action === "remind" ? remindLaterDate(new Date()) : undefined;
    setFeedback(null);
    act.mutate(
      { id: c.candidate_id, action, until },
      {
        onSuccess: (result) =>
          setFeedback({ tone: "ok", text: feedbackFor(action, c.title, until), threadId: result.threadId }),
        onError: () =>
          setFeedback({ tone: "error", text: "That didn't go through. Please try again." }),
      },
    );
  }

  return (
    <section className={styles.section} aria-label="Things noticed">
      <p className={styles.sub}>
        <Icon name="eye" size={14} />
        Possible connections in what you added. Nothing joins a thread without your say-so.
      </p>

      <p className={styles.feedback} data-tone={feedback?.tone} role="status" aria-live="polite">
        {feedback && (
          <>
            {feedback.text}
            {feedback.threadId && (
              <>
                {" "}
                <Link href={`/threads/${feedback.threadId}`} className={styles.feedbackLink}>
                  Open it
                </Link>
              </>
            )}
          </>
        )}
      </p>

      {shown.length > 0 && (
        <ul className={styles.list}>
          {shown.map((c) => (
            <li key={c.candidate_id}>
              <RelevanceCandidateCard
                targetThreadTitle={c.title}
                candidateLabel={
                  c.seen_count > 1 ? plural(c.seen_count, "recent entry", "recent entries") : "Something you logged"
                }
                reason={noticedReason(c)}
                effectIfAccepted={`WellBe starts a health thread called “${c.title}” and carries these entries into it. Your original entries stay as they are.`}
                sources={sourcesFor(c)}
                confidence={c.confidence ?? undefined}
                confidenceBasis="How clearly it came through in what you logged."
                onAccept={() => run(c, "accept")}
                onReject={() => run(c, "reject")}
                onIgnore={() => run(c, "ignore")}
                onRemindLater={() => run(c, "remind")}
              />
            </li>
          ))}
        </ul>
      )}

      {hidden > 0 && (
        <button type="button" className={styles.more} onClick={() => setExpanded(true)}>
          Show {plural(hidden, "more thing noticed", "more things noticed")}
        </button>
      )}
    </section>
  );
}
