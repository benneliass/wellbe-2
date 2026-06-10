import type { Thread } from "@/lib/types";
import styles from "./SummaryStrip.module.css";

const OPEN_STATUSES: Thread["status"][] = ["active", "monitoring", "attention"];

/** "What am I carrying forward?" — at-a-glance counts derived from the threads. */
export function SummaryStrip({ threads }: { threads: Thread[] }) {
  const open = threads.filter((t) => OPEN_STATUSES.includes(t.status)).length;
  const attention = threads.filter((t) => t.status === "attention").length;

  return (
    <section className={styles.summary}>
      <div className={styles.item}>
        <span className={styles.label}>Carrying forward</span>
        <span className={styles.value}>
          {open} <em>open threads</em>
        </span>
      </div>
      <div className={styles.divider} />
      <div className={styles.item}>
        <span className={styles.label}>Needs attention</span>
        <span className={`${styles.value} ${styles.warn}`}>
          {attention} <em>{attention === 1 ? "thread" : "threads"}</em>
        </span>
      </div>
      <div className={styles.divider} />
      <div className={styles.item}>
        <span className={styles.label}>Changed from your normal</span>
        <span className={styles.value}>
          CRP <em>↑ 18 mg/L</em>
        </span>
      </div>
      <div className={styles.divider} />
      <div className={styles.item}>
        <span className={styles.label}>Unresolved questions</span>
        <span className={styles.value}>
          2 <em>to ask</em>
        </span>
      </div>
    </section>
  );
}
