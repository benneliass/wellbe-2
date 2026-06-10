import { ConfidenceDots, SourceChip } from "@wellbe/ui";
import type { EvidenceItem } from "@/lib/types";
import styles from "./EvidenceList.module.css";

export function EvidenceList({ evidence, strong }: { evidence: EvidenceItem[]; strong: boolean }) {
  return (
    <>
      <div className={styles.list}>
        {evidence.map((e, i) => (
          <div className={styles.row} key={i}>
            <SourceChip type={e.src} />
            <div className={styles.main}>
              <div className={styles.title}>{e.title}</div>
              <div className={styles.meta}>
                {e.author} · {e.date}
              </div>
            </div>
            <ConfidenceDots level={e.conf} />
          </div>
        ))}
      </div>
      <div className={styles.trust}>
        <span className={styles.trustLabel}>Overall confidence</span>
        <ConfidenceDots level={strong ? 4 : 3} label={strong ? "Strong" : "Moderate"} />
      </div>
    </>
  );
}
