import { Chip, ConfidenceDots, Icon } from "@wellbe/ui";
import { EVENT_META, REVIEW_META } from "@/lib/meta";
import type { ThreadEvent } from "@/lib/types";
import styles from "./Timeline.module.css";

function TimelineEvent({ ev, last }: { ev: ThreadEvent; last: boolean }) {
  const meta = EVENT_META[ev.type];
  const review = ev.review ? REVIEW_META[ev.review] : undefined;

  return (
    <div className={styles.ev}>
      <div className={styles.col}>
        <span className={styles.node} data-tone={meta.tone} data-current={ev.state === "current" || undefined}>
          <Icon name={meta.icon} size={15} />
        </span>
        {!last && <span className={styles.line} />}
      </div>
      <div className={styles.card}>
        <div className={styles.head}>
          <span className={styles.time}>{ev.time}</span>
          {ev.state === "attention" && (
            <Chip tone="amber" size="sm" icon="alert-circle">
              Needs attention
            </Chip>
          )}
          {ev.state === "current" && (
            <Chip tone="teal" size="sm">
              Current
            </Chip>
          )}
        </div>
        <div className={styles.title}>{ev.title}</div>
        <div className={styles.detail}>{ev.detail}</div>
        {(ev.conf || review) && (
          <div className={styles.evi}>
            {ev.conf && <ConfidenceDots level={ev.conf} />}
            {review && (
              <Chip tone={review.tone} size="sm" icon={review.icon}>
                {review.label}
              </Chip>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function Timeline({ events }: { events: ThreadEvent[] }) {
  return (
    <div className={styles.tl}>
      {events.map((ev, i) => (
        <TimelineEvent key={i} ev={ev} last={i === events.length - 1} />
      ))}
    </div>
  );
}
