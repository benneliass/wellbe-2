"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Icon } from "../Icon";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { CorrectionMarker } from "./CorrectionMarker";
import { ReviewMarkerList } from "./ReviewMarker";
import { SourceMarker } from "./SourceMarker";
import styles from "./EvidenceDrawer.module.css";
import type { EvidenceSource } from "./types";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export interface EvidenceDrawerProps {
  open: boolean;
  onClose: () => void;
  sources: readonly EvidenceSource[];
  title?: string;
  /** The claim these sources back, shown under the title. */
  claim?: ReactNode;
  onOpenSource?: (source: EvidenceSource) => void;
  onOpenCorrectionHistory?: (source: EvidenceSource) => void;
  /** Forwarded to review markers; only true for C10 route_urgent decisions. */
  safetyApproved?: boolean;
}

/**
 * Evidence drawer / source inspector (WEL-144 §5, disclosure L3–L4).
 * A modal dialog: focus moves in on open, Tab is trapped, Esc and the scrim close
 * it, and focus returns to the element that opened it. Bottom sheet on small
 * screens, side drawer from 768px.
 */
export function EvidenceDrawer({
  open,
  onClose,
  sources,
  title = "Evidence",
  claim,
  onOpenSource,
  onOpenCorrectionHistory,
  safetyApproved,
}: EvidenceDrawerProps) {
  const [mounted, setMounted] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const titleId = useId();
  const claimId = useId();
  const personalId = useId();
  const externalId = useId();

  useEffect(() => setMounted(true), []);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open || !mounted) return;
    const returnTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) {
        event.preventDefault();
        return;
      }
      const active = document.activeElement;
      const inside = active instanceof Node && panel.contains(active);
      if (event.shiftKey && (active === first || !inside)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (active === last || !inside)) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (returnTo?.isConnected) returnTo.focus();
    };
  }, [open, mounted]);

  if (!open || !mounted) return null;

  const personal = sources.filter((s) => s.component !== "c16");
  const external = sources.filter((s) => s.component === "c16");

  const renderItem = (source: EvidenceSource) => {
    const hasReview = (source.reviewMarkers?.length ?? 0) > 0;
    const hasConfidence = typeof source.confidence === "number";
    return (
      <li key={source.id} className={styles.item}>
        <SourceMarker
          displayLabel={source.displayLabel}
          component={source.component}
          kind={source.kind}
          date={source.date}
          onOpen={onOpenSource ? () => onOpenSource(source) : undefined}
        />
        {source.excerpt && <p className={styles.excerpt}>{source.excerpt}</p>}
        {source.href && (
          <a className={styles.open} href={source.href}>
            {source.kind === "lab"
              ? "Open this result"
              : source.kind === "doc"
                ? "Open this file"
                : "Open"}
          </a>
        )}
        {(hasReview || hasConfidence || source.correction || source.qualityTier) && (
          <div className={styles.details}>
            {hasReview && <ReviewMarkerList values={source.reviewMarkers ?? []} safetyApproved={safetyApproved} />}
            {hasConfidence && (
              <ConfidenceMeter score={source.confidence} basis={source.confidenceBasis} basisDisplay="inline" />
            )}
            {source.correction && (
              <CorrectionMarker
                {...source.correction}
                onOpenHistory={onOpenCorrectionHistory ? () => onOpenCorrectionHistory(source) : undefined}
              />
            )}
            {source.component === "c16" && source.qualityTier && (
              <p className={styles.tier}>Source quality: {source.qualityTier}</p>
            )}
          </div>
        )}
      </li>
    );
  };

  return createPortal(
    <div className={styles.root}>
      <div className={styles.scrim} onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={claim ? claimId : undefined}
      >
        <div className={styles.handle} aria-hidden="true" />
        <div className={styles.head}>
          <h2 id={titleId} className={styles.title}>
            <Icon name="file-search" size={18} />
            {title}
          </h2>
          <button ref={closeRef} type="button" className={styles.close} onClick={onClose} aria-label="Close evidence">
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className={styles.body}>
          {claim && (
            <p id={claimId} className={styles.claim}>
              {claim}
            </p>
          )}
          {sources.length === 0 && <p className={styles.empty}>No sources are attached to this yet.</p>}
          {personal.length > 0 && (
            <section aria-labelledby={personalId} className={styles.group}>
              <h3 id={personalId} className={styles.groupTitle}>
                From your records and data
              </h3>
              <ul className={styles.list}>{personal.map(renderItem)}</ul>
            </section>
          )}
          {external.length > 0 && (
            <section aria-labelledby={externalId} className={styles.group} data-external="true">
              <h3 id={externalId} className={styles.groupTitle}>
                External reference
              </h3>
              <p className={styles.groupNote}>General context, not about you specifically.</p>
              <ul className={styles.list}>{external.map(renderItem)}</ul>
            </section>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
