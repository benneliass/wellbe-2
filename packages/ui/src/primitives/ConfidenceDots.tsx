import styles from "./ConfidenceDots.module.css";

export interface ConfidenceDotsProps {
  /** 0–5 filled dots. */
  level?: number;
  label?: string;
}

/** Five-dot evidence-confidence indicator. Pairs with a label for non-color meaning. */
export function ConfidenceDots({ level = 3, label }: ConfidenceDotsProps) {
  return (
    <span className={styles.conf} role="img" aria-label={label ?? `Confidence ${level} of 5`}>
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={styles.dot} data-on={i < level || undefined} />
      ))}
      {label && <span className={styles.label}>{label}</span>}
    </span>
  );
}
