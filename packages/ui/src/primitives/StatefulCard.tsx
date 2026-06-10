import type { ReactNode } from "react";
import { Icon } from "../Icon";
import styles from "./StatefulCard.module.css";

export type CardState = "success" | "warning" | "error" | "info";

const DEFAULT_ICON: Record<CardState, string> = {
  success: "check-circle-2",
  warning: "alert-triangle",
  error: "x-circle",
  info: "info",
};

export interface StatefulCardProps {
  /** Calm state register: success/warning/error/info. Tints stay soft; the hue is reserved for icon + chip text. */
  state: CardState;
  /** Override the default state icon (kebab-case lucide name). */
  icon?: string;
  title?: ReactNode;
  children?: ReactNode;
  /** Optional state chip shown beneath the body (e.g. "Needs attention"). */
  chipLabel?: ReactNode;
  className?: string;
}

/** Tinted card that carries a calm state. Use sparingly; pair with descriptive (never judging) copy. */
export function StatefulCard({ state, icon, title, children, chipLabel, className }: StatefulCardProps) {
  return (
    <div className={className ? `${styles.card} ${className}` : styles.card} data-state={state}>
      <span className={styles.icon}>
        <Icon name={icon ?? DEFAULT_ICON[state]} size={18} />
      </span>
      {title && <p className={styles.title}>{title}</p>}
      {children && <div className={styles.body}>{children}</div>}
      {chipLabel && <span className={styles.chip}>{chipLabel}</span>}
    </div>
  );
}
