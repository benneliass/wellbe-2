"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Icon } from "@wellbe/ui";
import { formatShortDate } from "@/lib/adapters";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/lib/hooks";
import { useSession } from "@/lib/useSession";
import styles from "./NotificationBell.module.css";

/**
 * In-app notifications: a bell with an unread badge and a dropdown list of
 * follow-up reminders (in-app only — nothing is pushed or emailed). Opening a
 * reminder marks it read and goes to its thread. Calm framing throughout.
 */
export function NotificationBell() {
  const signedIn = Boolean(useSession()?.patientId);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const { data, isError } = useNotifications(signedIn);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();

  const items = data?.notifications ?? [];
  const unread = data?.unread_count ?? 0;

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.bell}
        title="Notifications"
        aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Icon name="bell" size={18} />
        {unread > 0 && (
          <span className={styles.badge} aria-hidden="true">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className={styles.panel} role="dialog" aria-label="Notifications">
          <div className={styles.head}>
            <b>Notifications</b>
            {unread > 0 && (
              <button
                type="button"
                className={styles.linkBtn}
                onClick={() => markAll.mutate()}
                disabled={markAll.isPending}
              >
                Mark all read
              </button>
            )}
          </div>

          {items.length === 0 ? (
            <div className={styles.empty}>
              <p>
                {isError
                  ? "Couldn't load notifications just now."
                  : "You're all caught up. Follow-up reminders will gather here, calmly."}
              </p>
              <Link href="/workspace" className={styles.emptyLink} onClick={() => setOpen(false)}>
                <Icon name="list" size={15} /> See your open loops
              </Link>
            </div>
          ) : (
            <ul className={styles.list}>
              {items.map((n) => {
                const isUnread = !n.read_at;
                const onOpen = () => {
                  if (isUnread) markRead.mutate(n.notification_id);
                  setOpen(false);
                };
                const content = (
                  <>
                    <span className={styles.dot} data-unread={isUnread || undefined} />
                    <span className={styles.text}>
                      <b>{n.title}</b>
                      <span>{n.body}</span>
                      <time dateTime={n.created_at}>{formatShortDate(n.created_at)}</time>
                    </span>
                  </>
                );
                return (
                  <li key={n.notification_id} className={styles.item} data-unread={isUnread || undefined}>
                    {n.thread_id ? (
                      <Link href={`/threads/${n.thread_id}`} className={styles.row} onClick={onOpen}>
                        {content}
                      </Link>
                    ) : (
                      <div className={styles.row}>{content}</div>
                    )}
                    {isUnread && (
                      <button
                        type="button"
                        className={styles.markBtn}
                        aria-label={`Mark "${n.title}" as read`}
                        title="Mark as read"
                        onClick={() => markRead.mutate(n.notification_id)}
                      >
                        <Icon name="check" size={14} />
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
