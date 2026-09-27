import Link from "next/link";
import { Chip, Icon } from "@wellbe/ui";
import { describePendingItem, openPendingItems, type PendingItemV2 } from "@/lib/pending";
import styles from "./OpenLoops.module.css";

/**
 * Follow-ups the user is still carrying forward, soonest first, each with where
 * it stands ("Check back Oct 4", "Due Oct 4", "Still open"). Rows link to the
 * thread unless we are already on it.
 */
export function OpenLoops({
  items,
  linkToThread = true,
  title = "Open loops",
}: {
  items: PendingItemV2[];
  linkToThread?: boolean;
  title?: string;
}) {
  const open = openPendingItems(items);
  if (open.length === 0) return null;

  return (
    <section className={styles.loops} aria-label={title}>
      <h2 className={styles.head}>{title}</h2>
      <ul className={styles.list}>
        {open.map((item) => {
          const state = describePendingItem(item);
          const body = (
            <>
              <Icon name="clock" size={16} />
              <span className={styles.title}>{item.title}</span>
              <Chip tone={state.tone} size="sm">
                {state.label}
              </Chip>
            </>
          );
          return (
            <li key={item.pending_item_id} data-status={item.status}>
              {linkToThread ? (
                <Link href={`/threads/${item.primary_thread_id}`} className={styles.row}>
                  {body}
                  <Icon name="chevron-right" size={16} />
                </Link>
              ) : (
                <div className={styles.row}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
