"use client";

import { useMemo, useState } from "react";
import { Button } from "@wellbe/ui";
import type { Thread, ThreadStatus } from "@/lib/types";
import { SummaryStrip } from "./SummaryStrip";
import { ThreadCard } from "./ThreadCard";
import styles from "./WorkspaceHome.module.css";

type TabId = "all" | Extract<ThreadStatus, "active" | "attention" | "resolved">;

export function WorkspaceHome({ threads }: { threads: Thread[] }) {
  const [tab, setTab] = useState<TabId>("all");

  const tabs = useMemo(
    () => [
      { id: "all" as const, label: "All", count: threads.length },
      { id: "active" as const, label: "Active", count: threads.filter((t) => t.status === "active").length },
      { id: "attention" as const, label: "Needs attention", count: threads.filter((t) => t.status === "attention").length },
      { id: "resolved" as const, label: "Resolved", count: threads.filter((t) => t.status === "resolved").length },
    ],
    [threads],
  );

  const shown = tab === "all" ? threads : threads.filter((t) => t.status === tab);

  return (
    <div>
      <SummaryStrip threads={threads} />

      <div className={styles.bar}>
        <div className={styles.tabs} role="tablist">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className={styles.tab}
              data-active={tab === t.id || undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label} <span className={styles.count}>{t.count}</span>
            </button>
          ))}
        </div>
        <div className={styles.actions}>
          <Button variant="ghost" icon="sliders-horizontal">
            Sort: Recently updated
          </Button>
          <Button variant="ghost" icon="filter">
            Filters
          </Button>
        </div>
      </div>

      <div className={styles.grid}>
        {shown.map((t) => (
          <ThreadCard key={t.id} thread={t} />
        ))}
      </div>
    </div>
  );
}
