import { Chip, Icon } from "@wellbe/ui";
import { RISK_META, STATUS_META } from "@/lib/meta";
import type { Thread } from "@/lib/types";
import styles from "./ConcernHeader.module.css";

export function ConcernHeader({ thread }: { thread: Thread }) {
  const status = STATUS_META[thread.status];
  const risk = RISK_META[thread.risk];

  return (
    <section className={styles.concern}>
      <div className={styles.row}>
        <div className={styles.icon} data-tone={status.tone}>
          <Icon name={status.icon} size={22} />
        </div>
        <div>
          <div className={styles.chips}>
            <Chip tone={status.tone} icon={status.icon}>
              {status.label}
            </Chip>
            <Chip tone={risk.tone} size="sm" outline>
              {risk.label} risk
            </Chip>
          </div>
          <h2 className={styles.question}>{thread.question}</h2>
        </div>
      </div>

      <div className={styles.changed}>
        <Icon name="activity" size={15} />
        <span>
          <b>What changed:</b> {thread.changed}
        </span>
      </div>

      <div className={styles.metrics}>
        {thread.metrics.map((m, i) => (
          <div className={styles.metric} key={i}>
            <span className={styles.metricLabel}>{m.label}</span>
            <span className={styles.metricValue}>
              {m.value}
              {m.unit && <em>{m.unit}</em>}
            </span>
            {m.delta && (
              <span className={styles.delta} data-dir={m.dir}>
                {m.delta}
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
