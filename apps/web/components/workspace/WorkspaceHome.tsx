"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Icon } from "@wellbe/ui";
import type { ThreadStatus, ThreadSummary } from "@/lib/types";
import { STATUS_META } from "@/lib/meta";
import { SummaryStrip } from "./SummaryStrip";
import { ThreadCard } from "./ThreadCard";
import styles from "./WorkspaceHome.module.css";

type TabId = "all" | Extract<ThreadStatus, "active" | "attention" | "resolved">;

type SortMode = "recent" | "oldest" | "title";

const SORT_META: Record<SortMode, { label: string; next: SortMode }> = {
  recent: { label: "Recently updated", next: "oldest" },
  oldest: { label: "Oldest first", next: "title" },
  title: { label: "Title A–Z", next: "recent" },
};

const FILTERABLE: ThreadStatus[] = [
  "active",
  "monitoring",
  "attention",
  "resolved",
  "paused",
  "closed",
];

export function WorkspaceHome({
  threads,
  pendingCount,
}: {
  threads: ThreadSummary[];
  pendingCount: number;
}) {
  const [tab, setTab] = useState<TabId>("all");
  const [sort, setSort] = useState<SortMode>("recent");
  const [hidden, setHidden] = useState<Set<ThreadStatus>>(new Set());
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filterRef = useRef<HTMLDivElement>(null);

  // Close the filters popover on an outside click.
  useEffect(() => {
    if (!filtersOpen) return;
    function onDown(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFiltersOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [filtersOpen]);

  const tabs = useMemo(
    () => [
      { id: "all" as const, label: "All", count: threads.length },
      { id: "active" as const, label: "Active", count: threads.filter((t) => t.status === "active").length },
      { id: "attention" as const, label: "Needs attention", count: threads.filter((t) => t.status === "attention").length },
      { id: "resolved" as const, label: "Resolved", count: threads.filter((t) => t.status === "resolved").length },
    ],
    [threads],
  );

  const shown = useMemo(() => {
    const byTab = tab === "all" ? threads : threads.filter((t) => t.status === tab);
    const byFilter = byTab.filter((t) => !hidden.has(t.status));
    const sorted = [...byFilter];
    sorted.sort((a, b) => {
      if (sort === "title") return a.title.localeCompare(b.title);
      const at = new Date(a.updatedAt).getTime() || 0;
      const bt = new Date(b.updatedAt).getTime() || 0;
      return sort === "recent" ? bt - at : at - bt;
    });
    return sorted;
  }, [threads, tab, hidden, sort]);

  function toggleHidden(status: ThreadStatus) {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  }

  const filterCount = hidden.size;

  return (
    <div>
      <SummaryStrip threads={threads} pendingCount={pendingCount} />

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
          <Button
            variant="ghost"
            icon="sliders-horizontal"
            onClick={() => setSort(SORT_META[sort].next)}
            title="Change sort order"
          >
            Sort: {SORT_META[sort].label}
          </Button>
          <div className={styles.filterWrap} ref={filterRef}>
            <Button
              variant="ghost"
              icon="filter"
              onClick={() => setFiltersOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={filtersOpen}
            >
              Filters{filterCount > 0 ? ` (${filterCount})` : ""}
            </Button>
            {filtersOpen && (
              <div className={styles.filterMenu} role="menu">
                <div className={styles.filterHead}>Show statuses</div>
                {FILTERABLE.map((s) => {
                  const meta = STATUS_META[s];
                  const visible = !hidden.has(s);
                  return (
                    <button
                      key={s}
                      type="button"
                      role="menuitemcheckbox"
                      aria-checked={visible}
                      className={styles.filterRow}
                      onClick={() => toggleHidden(s)}
                    >
                      <span className={styles.filterCheck} data-on={visible || undefined}>
                        {visible && <Icon name="check" size={12} />}
                      </span>
                      <Icon name={meta.icon} size={15} />
                      <span className={styles.filterLabel}>{meta.label}</span>
                    </button>
                  );
                })}
                {filterCount > 0 && (
                  <button
                    type="button"
                    className={styles.filterClear}
                    onClick={() => setHidden(new Set())}
                  >
                    Reset filters
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className={styles.grid}>
        {shown.length === 0 ? (
          <p className={styles.empty}>No threads match this view.</p>
        ) : (
          shown.map((t) => <ThreadCard key={t.id} thread={t} />)
        )}
      </div>
    </div>
  );
}
