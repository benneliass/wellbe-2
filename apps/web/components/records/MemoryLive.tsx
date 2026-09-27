"use client";

import Link from "next/link";
import { Chip, Icon } from "@wellbe/ui";
import { StateNote } from "@/components/placeholder/StateNote";
import { memoryTypeLabel, sourceRefSummary } from "@/lib/graph-labels";
import { useMemoriesForThreads, useThreads } from "@/lib/hooks";
import styles from "./RecordList.module.css";

/**
 * The health memory: the source-linked memories WellBe keeps around each thread
 * (/v2/threads/{id}/memories), grouped by thread.
 */
export function MemoryLive() {
  const threads = useThreads();
  const list = threads.data ?? [];
  const memories = useMemoriesForThreads(list.map((t) => t.id));

  if (threads.isLoading) return <StateNote icon="clock" title="Loading your memory…" />;
  if (threads.isError) {
    return (
      <StateNote
        icon="alert-circle"
        title="Couldn't load your memory"
        description="Please try again in a moment."
      />
    );
  }
  if (list.length === 0) {
    return (
      <StateNote
        icon="book"
        title="Nothing kept yet"
        description="As you add symptoms, results, and notes, WellBe keeps source-linked memories around each thread here."
      />
    );
  }

  return (
    <div className={styles.wrap}>
      <p className={styles.hint}>
        <Icon name="lock" size={13} />
        Your longitudinal record — every memory links back to what you added.
      </p>
      {list.map((t, i) => {
        const q = memories[i];
        const entries = q?.data ?? [];
        return (
          <section key={t.id} className={styles.group} aria-label={`${t.title} memories`}>
            <div className={styles.groupHead}>
              <h2 className={styles.groupTitle}>{t.title}</h2>
              <Link href={`/threads/${t.id}`} className={styles.groupLink}>
                Open thread
              </Link>
            </div>
            {!q || q.isLoading ? (
              <p className={styles.muted}>Loading…</p>
            ) : q.isError ? (
              <p className={styles.muted}>These memories aren&rsquo;t available right now.</p>
            ) : entries.length === 0 ? (
              <p className={styles.muted}>Nothing kept for this thread yet.</p>
            ) : (
              <ul className={styles.list}>
                {entries.map((m) => (
                  <li key={m.memory_entry_id} className={styles.row}>
                    <span className={styles.rowIcon}>
                      <Icon name="book" size={15} />
                    </span>
                    <span className={styles.rowMain}>
                      <span className={styles.rowTitle}>{m.title}</span>
                      <span className={styles.rowSub}>
                        <Icon name="badge-check" size={11} />
                        {sourceRefSummary(m.source_refs ?? []) || "Source-linked"}
                      </span>
                    </span>
                    <Chip size="sm" tone="tealmid">
                      {memoryTypeLabel(m.memory_type)}
                    </Chip>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
