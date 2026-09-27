"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { EvidenceDrawer, Icon, StoryLanes, type StoryEntry } from "@wellbe/ui";
import { StateNote } from "@/components/placeholder/StateNote";
import { useMemoriesForThreads, useThreads } from "@/lib/hooks";
import {
  MEMORY_TYPES,
  MEMORY_TYPE_COPY,
  groupByType,
  toHubEntry,
  type HubEntry,
  type MemoryTypeId,
} from "./memoryHub";
import styles from "./MemoryHub.module.css";

type GroupId = MemoryTypeId | "other";
type Filter = GroupId | "all";

const OTHER_COPY = {
  title: "Other memories",
  description: "Kept by WellBe, linked to where each one came from.",
  empty: "Nothing here yet.",
};

function copyFor(type: GroupId) {
  return type === "other" ? OTHER_COPY : MEMORY_TYPE_COPY[type];
}

/**
 * The Memory hub: every memory WellBe keeps around your threads
 * (/v2/threads/{id}/memories), grouped by the six C8 memory types. Within a type,
 * StoryLanes keeps your own words apart from WellBe's summaries (WEL-146).
 */
export function MemoryLive() {
  const threads = useThreads();
  const list = threads.data ?? [];
  const memories = useMemoriesForThreads(list.map((t) => t.id));
  const [filter, setFilter] = useState<Filter>("all");
  const [inspecting, setInspecting] = useState<HubEntry | null>(null);

  const entries = list.flatMap((t, i) => (memories[i]?.data ?? []).map((m) => toHubEntry(m, t.title)));
  const groups = groupByType(entries);

  if (threads.isLoading) return <StateNote icon="clock" title="Loading your memory…" />;
  if (threads.isError) {
    return (
      <StateNote
        icon="alert-circle"
        title="Couldn't load your memory"
        description="Please try again in a moment."
      />
    );
  }

  const loading = memories.some((q) => q.isLoading);
  const unavailable = list.filter((_, i) => memories[i]?.isError);

  if (list.length === 0 || (!loading && entries.length === 0 && unavailable.length === 0)) {
    return (
      <StateNote
        icon="book"
        title="Nothing kept yet"
        description="As you add symptoms, results, and notes, WellBe keeps source-linked memories around each thread here."
      />
    );
  }

  const count = (type: GroupId) => groups.get(type)?.length ?? 0;
  const filterIds: GroupId[] = [...MEMORY_TYPES, ...(count("other") > 0 ? (["other"] as const) : [])];
  const shown: GroupId[] = filter === "all" ? filterIds.filter((t) => count(t) > 0) : [filter];
  const notYet = filter === "all" ? MEMORY_TYPES.filter((t) => count(t) === 0) : [];

  return (
    <div className={styles.wrap}>
      <p className={styles.hint}>
        <Icon name="lock" size={14} />
        Your longitudinal record — every memory links back to what you added.
      </p>

      <div className={styles.filters} role="group" aria-label="Show memory type">
        <FilterButton active={filter === "all"} onClick={() => setFilter("all")} count={entries.length}>
          All
        </FilterButton>
        {filterIds.map((t) => (
          <FilterButton key={t} active={filter === t} onClick={() => setFilter(t)} count={count(t)}>
            {copyFor(t).title}
          </FilterButton>
        ))}
      </div>

      {unavailable.length > 0 && (
        <p className={styles.quiet} role="status">
          <Icon name="info" size={14} />
          Memories for {unavailable.map((t) => t.title).join(", ")} aren&rsquo;t available right now.
        </p>
      )}

      {loading && entries.length === 0 ? (
        <p className={styles.quiet} role="status">
          Loading memories…
        </p>
      ) : (
        shown.map((type) => (
          <TypeSection
            key={type}
            type={type}
            entries={groups.get(type) ?? []}
            onOpenSources={(e) => setInspecting(entries.find((x) => x.id === e.id) ?? null)}
          />
        ))
      )}

      {notYet.length > 0 && !loading && (
        <p className={styles.quiet}>
          Not kept yet: {notYet.map((t) => MEMORY_TYPE_COPY[t].title).join(" · ")}
        </p>
      )}

      <EvidenceDrawer
        open={inspecting !== null}
        onClose={() => setInspecting(null)}
        title="Where this came from"
        sources={inspecting?.sources ?? []}
        claim={
          inspecting && (
            <>
              {inspecting.text} · kept in{" "}
              <Link href={`/threads/${inspecting.threadId}`}>{inspecting.threadTitle}</Link>
            </>
          )
        }
      />
    </div>
  );
}

function FilterButton({
  active,
  count,
  onClick,
  children,
}: {
  active: boolean;
  count: number;
  onClick: () => void;
  children: string;
}) {
  return (
    <button type="button" className={styles.filter} aria-pressed={active} onClick={onClick}>
      {children}
      <span className={styles.count} aria-hidden="true">
        {count}
      </span>
      <span className={styles.srOnly}>
        , {count} {count === 1 ? "memory" : "memories"}
      </span>
    </button>
  );
}

function TypeSection({
  type,
  entries,
  onOpenSources,
}: {
  type: GroupId;
  entries: HubEntry[];
  onOpenSources: (entry: StoryEntry) => void;
}) {
  const headingId = useId();
  const copy = copyFor(type);
  const threads = Array.from(new Map(entries.map((e) => [e.threadId, e.threadTitle])));

  return (
    <section className={styles.section} aria-labelledby={headingId} data-memory-type={type}>
      <header className={styles.sectionHead}>
        <h2 id={headingId} className={styles.sectionTitle}>
          {copy.title}
        </h2>
        <p className={styles.sectionDescription}>{copy.description}</p>
      </header>

      {entries.length === 0 ? (
        <p className={styles.empty}>{copy.empty}</p>
      ) : (
        <>
          <StoryLanes entries={entries} onOpenSources={onOpenSources} />
          <p className={styles.keptIn}>
            <span>Kept in</span>
            {threads.map(([id, title]) => (
              <Link key={id} href={`/threads/${id}`} className={styles.threadLink}>
                {title}
              </Link>
            ))}
          </p>
        </>
      )}
    </section>
  );
}
