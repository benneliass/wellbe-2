import { Icon } from "../Icon";
import type { Tone } from "./Chip";
import styles from "./VerificationBadge.module.css";

export type VerificationKind = "verified" | "clinician" | "ai";

interface BadgeMeta {
  icon: string;
  label: string;
  tone: Tone;
}

const VERIFICATION_META: Record<VerificationKind, BadgeMeta> = {
  verified: { icon: "badge-check", label: "Verified", tone: "green" },
  clinician: { icon: "users", label: "Clinician reviewed", tone: "teal" },
  ai: { icon: "sparkles", label: "AI extracted", tone: "violet" },
};

export interface VerificationBadgeProps {
  kind: VerificationKind;
  /** Override the default label (kept neutral/descriptive). */
  label?: string;
}

/** Provenance badge describing how a piece of evidence was reviewed. Meaning carried by icon + text. */
export function VerificationBadge({ kind, label }: VerificationBadgeProps) {
  const meta = VERIFICATION_META[kind];
  return (
    <span className={styles.badge} data-tone={meta.tone}>
      <Icon name={meta.icon} size={14} />
      {label ?? meta.label}
    </span>
  );
}
