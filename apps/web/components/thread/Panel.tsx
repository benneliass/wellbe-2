import type { ReactNode } from "react";
import { Icon } from "@wellbe/ui";
import styles from "./Panel.module.css";

export interface PanelProps {
  title: string;
  icon: string;
  /** Right-aligned count text (e.g. "3 sources"). */
  count?: string;
  /** Right-aligned action node (e.g. an "Add event" button). */
  action?: ReactNode;
  children: ReactNode;
}

/** Card with an icon + title header — the repeated container in the thread detail. */
export function Panel({ title, icon, count, action, children }: PanelProps) {
  return (
    <section className={styles.panel}>
      <div className={styles.head}>
        <h3>
          <Icon name={icon} size={16} />
          {title}
        </h3>
        {count && <span className={styles.count}>{count}</span>}
        {action}
      </div>
      {children}
    </section>
  );
}
