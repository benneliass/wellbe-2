import { Icon } from "@wellbe/ui";
import styles from "./ComingSoon.module.css";

export interface StateNoteProps {
  /** Kebab-case lucide icon name. */
  icon: string;
  /** Calm, honest headline. */
  title: string;
  /** One or two sentences explaining the state. */
  description?: string;
}

/**
 * Calm centered note for data states (loading / empty / error / sign-in needed).
 * Shares ComingSoon's card styling but carries no "in progress" badge — these are
 * runtime states, not unbuilt surfaces.
 */
export function StateNote({ icon, title, description }: StateNoteProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <span className={styles.icon}>
          <Icon name={icon} size={26} />
        </span>
        <h2 className={styles.title}>{title}</h2>
        {description && <p className={styles.desc}>{description}</p>}
      </div>
    </div>
  );
}
