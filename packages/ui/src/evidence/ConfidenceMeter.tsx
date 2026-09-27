"use client";

import { useId, useState } from "react";
import { cx } from "./format";
import shared from "./shared.module.css";
import styles from "./ConfidenceMeter.module.css";
import type { ConfidenceLevel } from "./types";

/**
 * Bucket a 0..1 C5 confidence into a display level (WEL-144 §2):
 * < 0.4 tentative, 0.4–0.75 moderate, > 0.75 well-supported.
 * Returns null for missing or non-finite scores; out-of-range scores are clamped.
 */
export function bucketConfidence(score: number | null | undefined): ConfidenceLevel | null {
  if (score === null || score === undefined || !Number.isFinite(score)) return null;
  const s = Math.min(1, Math.max(0, score));
  if (s < 0.4) return "tentative";
  if (s <= 0.75) return "moderate";
  return "well-supported";
}

export const CONFIDENCE_COPY: Record<ConfidenceLevel, { label: string; hint: string; filled: number }> = {
  tentative: { label: "Tentative", hint: "early signal", filled: 1 },
  moderate: { label: "Moderate", hint: "some support", filled: 2 },
  "well-supported": { label: "Well supported", hint: "consistent support", filled: 3 },
};

export interface ConfidenceMeterProps {
  /** C5 confidence 0..1. Never displayed as a number. */
  score?: number | null;
  /** Pre-bucketed level; used when `score` is absent. */
  level?: ConfidenceLevel;
  /** C5 confidence_basis. */
  basis?: string;
  /** "toggle" reveals basis on request (default), "inline" always shows it. */
  basisDisplay?: "toggle" | "inline" | "none";
  className?: string;
}

/** Confidence expressed in words with a subtle three-step meter; never colour-only. */
export function ConfidenceMeter({ score, level, basis, basisDisplay = "toggle", className }: ConfidenceMeterProps) {
  const [showBasis, setShowBasis] = useState(false);
  const basisId = useId();
  const resolved = bucketConfidence(score) ?? level ?? null;
  if (!resolved) return null;

  const copy = CONFIDENCE_COPY[resolved];
  const hasBasis = Boolean(basis?.trim()) && basisDisplay !== "none";
  const basisVisible = hasBasis && (basisDisplay === "inline" || showBasis);

  return (
    <span className={cx(styles.wrap, className)}>
      <span
        className={cx(shared.marker, styles.confidence)}
        data-confidence={resolved}
        role="img"
        aria-label={`Confidence: ${copy.label.toLowerCase()}, ${copy.hint}`}
      >
        <span className={styles.meter}>
          {[1, 2, 3].map((n) => (
            <span key={n} className={styles.seg} data-on={n <= copy.filled || undefined} />
          ))}
        </span>
        <span>{copy.label}</span>
        <span className={shared.meta}>· {copy.hint}</span>
      </span>
      {hasBasis && basisDisplay === "toggle" && (
        <button
          type="button"
          className={shared.link}
          aria-expanded={showBasis}
          aria-controls={basisId}
          onClick={() => setShowBasis((v) => !v)}
        >
          {showBasis ? "Hide basis" : "Why?"}
        </button>
      )}
      {basisVisible && (
        <span id={basisId} className={styles.basis}>
          {basis}
        </span>
      )}
    </span>
  );
}
