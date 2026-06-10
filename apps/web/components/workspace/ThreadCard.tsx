import Link from "next/link";
import { Chip, Icon } from "@wellbe/ui";
import { STATUS_META } from "@/lib/meta";
import type { Thread } from "@/lib/types";
import styles from "./ThreadCard.module.css";

export function ThreadCard({ thread }: { thread: Thread }) {
  const status = STATUS_META[thread.status];
  return (
    <Link href={`/threads/${thread.id}`} className={styles.card}>
      <div className={styles.top}>
        <div className={styles.icon} data-tone={status.tone}>
          <Icon name={status.icon} size={18} />
        </div>
        <Chip tone={status.tone} size="sm">
          {status.label}
        </Chip>
      </div>
      <h3 className={styles.title}>{thread.title}</h3>
      <p className={styles.question}>{thread.question}</p>

      <div className={styles.changed}>
        <Icon name="trending-up" size={14} />
        <span>{thread.changed}</span>
      </div>

      <div className={styles.foot}>
        <span className={styles.meta}>
          {thread.started} · {thread.updated}
        </span>
        <span className={styles.go}>
          Open thread <Icon name="chevron-right" size={15} />
        </span>
      </div>
    </Link>
  );
}
