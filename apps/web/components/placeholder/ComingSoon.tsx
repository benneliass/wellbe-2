import { Icon } from "@wellbe/ui";
import styles from "./ComingSoon.module.css";

export interface ComingSoonProps {
  /** Kebab-case lucide icon name. */
  icon: string;
  /** Calm, honest headline — what this surface will do. */
  title: string;
  /** One or two sentences. Plain, non-diagnostic, personal-first. */
  description: string;
  /** Optional extra context echoed back (e.g. the user's typed question). */
  echo?: string;
}

/**
 * Calm "not yet built" surface. Honest about what a destination will do without
 * pretending it already works. Used by route stubs for Home actions whose
 * feature track has not landed yet (see docs/implementation/home-buildout-plan.md).
 */
export function ComingSoon({ icon, title, description, echo }: ComingSoonProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <span className={styles.icon}>
          <Icon name={icon} size={26} />
        </span>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.desc}>{description}</p>
        {echo && (
          <p className={styles.echo}>
            <Icon name="search" size={15} />
            <span>{echo}</span>
          </p>
        )}
        <span className={styles.badge}>
          <span className={styles.badgeDot} />
          In progress
        </span>
      </div>
    </div>
  );
}
