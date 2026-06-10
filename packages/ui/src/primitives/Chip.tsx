import type { ReactNode } from "react";
import { Icon } from "../Icon";
import styles from "./Chip.module.css";

export type Tone =
  | "neutral"
  | "teal"
  | "tealmid"
  | "green"
  | "amber"
  | "orange"
  | "danger"
  | "violet";

export interface ChipProps {
  tone?: Tone;
  icon?: string;
  dot?: boolean;
  size?: "sm" | "md";
  outline?: boolean;
  children: ReactNode;
}

/** Pill label with optional leading icon or dot. Tone drives color via data-tone. */
export function Chip({ tone = "neutral", icon, dot, size = "md", outline = false, children }: ChipProps) {
  return (
    <span className={styles.chip} data-tone={tone} data-size={size} data-outline={outline || undefined}>
      {dot && <span className={styles.dot} />}
      {icon && <Icon name={icon} size={size === "sm" ? 12 : 14} />}
      {children}
    </span>
  );
}
