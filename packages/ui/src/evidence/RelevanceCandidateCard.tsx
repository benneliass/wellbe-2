"use client";

import { useId } from "react";
import { Icon } from "../Icon";
import { Button } from "../primitives/Button";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { containsBannedPhrasing, cx } from "./format";
import { ReviewMarkerList } from "./ReviewMarker";
import { SourceMarker } from "./SourceMarker";
import styles from "./RelevanceCandidateCard.module.css";
import type { EvidenceSource, ReviewMarkerValue } from "./types";

export const CANDIDATE_COPY = {
  heading: "Things noticed",
  subjectFallback: "This",
  mayRelate: "may relate to",
  reasonLabel: "Why it might matter",
  sourcesLabel: "Based on",
  effectLabel: "If you accept",
  defaultEffect: "It is added to this thread as context. Your original entry stays as it is, and you can undo this later.",
  fallbackReason: "WellBe noticed a possible connection worth a look.",
  accept: "Accept",
  reject: "Reject",
  ignore: "Ignore for now",
  remindLater: "Remind me later",
} as const;

export interface RelevanceCandidateCardProps {
  /** Title of the thread this may relate to. */
  targetThreadTitle: string;
  /** Short, non-causal reason, e.g. "Similar timing to your last two headaches." */
  reason: string;
  /** The new item that may belong, e.g. "Sleep log, 12 Mar". */
  candidateLabel?: string;
  /** What changes if accepted. */
  effectIfAccepted?: string;
  sources?: readonly EvidenceSource[];
  /** C5 confidence 0..1. */
  confidence?: number;
  confidenceBasis?: string;
  reviewMarkers?: ReviewMarkerValue[];
  onAccept: () => void;
  onReject: () => void;
  onIgnore: () => void;
  onRemindLater: () => void;
  onOpenSource?: (source: EvidenceSource) => void;
  className?: string;
}

function safeCopy(text: string | undefined, fallback: string): string {
  if (!text?.trim() || containsBannedPhrasing(text)) return fallback;
  return text;
}

/**
 * "Things noticed" candidate card: a possible connection, never a fact. Offers
 * accept / reject / ignore / remind later. Causal or diagnostic phrasing passed in
 * is replaced with neutral copy so it never reaches the screen.
 */
export function RelevanceCandidateCard({
  targetThreadTitle,
  reason,
  candidateLabel,
  effectIfAccepted,
  sources = [],
  confidence,
  confidenceBasis,
  reviewMarkers = ["AI-summarized", "not-clinician-reviewed"],
  onAccept,
  onReject,
  onIgnore,
  onRemindLater,
  onOpenSource,
  className,
}: RelevanceCandidateCardProps) {
  const headingId = useId();
  const safeReason = safeCopy(reason, CANDIDATE_COPY.fallbackReason);
  const safeEffect = safeCopy(effectIfAccepted, CANDIDATE_COPY.defaultEffect);
  const safeCandidate = candidateLabel && !containsBannedPhrasing(candidateLabel) ? candidateLabel : undefined;

  return (
    <article className={cx(styles.card, className)} aria-labelledby={headingId}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>
          <Icon name="eye" size={16} />
          {CANDIDATE_COPY.heading}
        </p>
        <h3 id={headingId} className={styles.title}>
          {safeCandidate ?? CANDIDATE_COPY.subjectFallback} {CANDIDATE_COPY.mayRelate}{" "}
          <span className={styles.thread}>{targetThreadTitle}</span>
        </h3>
      </header>

      <dl className={styles.facts}>
        <div>
          <dt>{CANDIDATE_COPY.reasonLabel}</dt>
          <dd>{safeReason}</dd>
        </div>
        {sources.length > 0 && (
          <div>
            <dt>{CANDIDATE_COPY.sourcesLabel}</dt>
            <dd>
              <ul className={styles.sources}>
                {sources.map((s) => (
                  <li key={s.id}>
                    <SourceMarker
                      displayLabel={s.displayLabel}
                      component={s.component}
                      kind={s.kind}
                      date={s.date}
                      onOpen={onOpenSource ? () => onOpenSource(s) : undefined}
                    />
                  </li>
                ))}
              </ul>
            </dd>
          </div>
        )}
        <div>
          <dt>{CANDIDATE_COPY.effectLabel}</dt>
          <dd>{safeEffect}</dd>
        </div>
      </dl>

      <div className={styles.markers}>
        <ConfidenceMeter score={confidence} basis={confidenceBasis} />
        <ReviewMarkerList values={reviewMarkers} />
      </div>

      <div className={styles.actions} role="group" aria-labelledby={headingId}>
        <Button variant="primary" onClick={onAccept}>
          {CANDIDATE_COPY.accept}
        </Button>
        <Button variant="ghost" onClick={onReject}>
          {CANDIDATE_COPY.reject}
        </Button>
        <Button variant="tertiary" onClick={onIgnore}>
          {CANDIDATE_COPY.ignore}
        </Button>
        <Button variant="tertiary" icon="clock" onClick={onRemindLater}>
          {CANDIDATE_COPY.remindLater}
        </Button>
      </div>
    </article>
  );
}
