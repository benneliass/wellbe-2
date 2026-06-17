import type { ThreadStatus, ThreadSummary } from "@/lib/types";
import styles from "./SummaryStrip.module.css";

const OPEN_STATUSES: ThreadStatus[] = ["active", "monitoring", "attention"];

/**
 * "What am I carrying forward?" — at-a-glance counts derived from real data:
 * open/attention threads from /v1/threads and open loops from /v2/pending-items.
 * No fabricated deltas — value surfaces (e.g. lab changes) arrive with Track D.
 */
export function SummaryStrip({
  threads,
  pendingCount,
}: {
  threads: ThreadSummary[];
  pendingCount: number;
}) {
  const open = threads.filter((t) => OPEN_STATUSES.includes(t.status)).length;
  const attention = threads.filter((t) => t.status === "attention").length;

  return (
    <section className={styles.summary}>
      <div className={styles.item}>
        <span className={styles.label}>Carrying forward</span>
        <span className={styles.value}>
          {open} <em>{open === 1 ? "open thread" : "open threads"}</em>
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
        <span className={styles.label}>Open loops</span>
        <span className={styles.value}>
          {pendingCount} <em>{pendingCount === 1 ? "to follow up" : "to follow up"}</em>
        </span>
      </div>
    </section>
  );
}
