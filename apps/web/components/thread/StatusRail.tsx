import { Icon } from "@wellbe/ui";
import type { RailStep } from "@/lib/types";
import styles from "./StatusRail.module.css";

export function StatusRail({ rail }: { rail: RailStep[] }) {
  return (
    <div className={styles.rail}>
      {rail.map((s, i) => {
        const last = i === rail.length - 1;
        return (
          <div className={styles.step} key={i}>
            <div className={styles.marker}>
              <span className={styles.node} data-state={s.state}>
                {s.state === "done" && <Icon name="check" size={10} />}
              </span>
              {!last && <span className={styles.line} data-done={s.state === "done" || undefined} />}
            </div>
            <div className={styles.body}>
              <div className={styles.label}>{s.label}</div>
              <div className={styles.meta} data-state={s.state}>
                {s.meta}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
