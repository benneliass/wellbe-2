import type { Thread } from "@/lib/types";
import { AddEventButton } from "./AddEventButton";
import { ConcernHeader } from "./ConcernHeader";
import { EvidenceList } from "./EvidenceList";
import { NextActions } from "./NextActions";
import { Panel } from "./Panel";
import { StatusRail } from "./StatusRail";
import { Timeline } from "./Timeline";
import styles from "./ThreadDetail.module.css";

export function ThreadDetail({ thread }: { thread: Thread }) {
  return (
    <div className={styles.detail}>
      <div className={styles.main}>
        <ConcernHeader thread={thread} />

        <Panel title="Timeline" icon="clock" action={<AddEventButton />}>
          <Timeline events={thread.events} />
        </Panel>
      </div>

      <aside className={styles.side}>
        <Panel title="Progress" icon="git-fork">
          <StatusRail rail={thread.rail} />
        </Panel>

        <Panel title="Evidence" icon="file-search" count={`${thread.evidence.length} sources`}>
          <EvidenceList evidence={thread.evidence} strong={thread.status !== "attention"} />
        </Panel>

        <Panel title="What next?" icon="circle-help">
          <NextActions thread={thread} />
        </Panel>
      </aside>
    </div>
  );
}
