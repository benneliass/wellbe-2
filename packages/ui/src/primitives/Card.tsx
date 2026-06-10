import type { ReactNode } from "react";
import { Icon } from "../Icon";
import styles from "./Card.module.css";

export type CardVariant = "default" | "elevated" | "outline" | "filled";

export interface CardProps {
  /** Surface treatment. Default = border + xs shadow; elevated = shadow, no border; outline = stronger border, no shadow; filled = subtle teal tint. */
  variant?: CardVariant;
  /** Optional leading icon (kebab-case lucide name) shown in a tinted badge. */
  icon?: string;
  title?: ReactNode;
  /** Optional secondary line beneath the body (rendered in accent on filled cards). */
  secondary?: ReactNode;
  children?: ReactNode;
  className?: string;
}

/** Base container card with the four design-system surface treatments. */
export function Card({ variant = "default", icon, title, secondary, children, className }: CardProps) {
  return (
    <div className={className ? `${styles.card} ${className}` : styles.card} data-variant={variant}>
      {icon && (
        <span className={styles.icon}>
          <Icon name={icon} size={18} />
        </span>
      )}
      {title && <p className={styles.title}>{title}</p>}
      {children && <div className={styles.body}>{children}</div>}
      {secondary && <div className={styles.secondary}>{secondary}</div>}
    </div>
  );
}
