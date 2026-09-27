"use client";

import Link from "next/link";
import { Icon } from "@wellbe/ui";
import { StateNote } from "@/components/placeholder/StateNote";
import { formatShortDate } from "@/lib/adapters";
import { usePendingItems, useThreads } from "@/lib/hooks";
import styles from "./RecordList.module.css";

const ITEM_TYPE_LABEL: Record<string, string> = {
  result_pending: "Waiting for a result",
  follow_up: "Follow-up",
  referral: "Referral",
  appointment: "Appointment",
  question: "Question to raise",
};

/**
 * Open loops (/v2/pending-items) — what is still waiting between visits: results
 * to come back, follow-ups, referrals. Each links back to its thread.
 */
export function OpenLoopsLive() {
  const items = usePendingItems();
  const threads = useThreads();

  if (items.isLoading) return <StateNote icon="clock" title="Loading your open loops…" />;
  if (items.isError) {
    return (
      <StateNote
        icon="alert-circle"
        title="Couldn't load your open loops"
        description="Please try again in a moment."
      />
    );
  }

  const active = (items.data ?? []).filter((p) => p.status === "active");
  const titleById = new Map((threads.data ?? []).map((t) => [t.id, t.title]));

  return (
    <div className={styles.wrap}>
      <section className={styles.group} aria-labelledby="open-loops-heading">
        <div className={styles.groupHead}>
          <h2 id="open-loops-heading" className={styles.groupTitle}>
            Open loops to follow up
          </h2>
          <span className={styles.rowSub}>{active.length} open</span>
        </div>
        {active.length === 0 ? (
          <p className={styles.muted}>Nothing is waiting right now.</p>
        ) : (
          <ul className={styles.list}>
            {active.map((p) => {
              const due = p.due_at ? formatShortDate(p.due_at) : "";
              const thread = p.primary_thread_id ? titleById.get(p.primary_thread_id) : undefined;
              return (
                <li key={p.pending_item_id} className={styles.row}>
                  <span className={styles.rowIcon}>
                    <Icon name="clock" size={15} />
                  </span>
                  <span className={styles.rowMain}>
                    <span className={styles.rowTitle}>{p.title}</span>
                    <span className={styles.rowSub}>
                      {ITEM_TYPE_LABEL[p.item_type] ?? "Open item"}
                      {due ? ` · due ${due}` : ""}
                      {` · added ${formatShortDate(p.created_at)}`}
                    </span>
                  </span>
                  {p.primary_thread_id && (
                    <Link href={`/threads/${p.primary_thread_id}`} className={styles.groupLink}>
                      {thread ? `Open ${thread}` : "Open thread"}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
      <p className={styles.hint}>
        <Icon name="calendar" size={13} />
        Past and upcoming visits will appear here too once visit records are connected.
      </p>
    </div>
  );
}
