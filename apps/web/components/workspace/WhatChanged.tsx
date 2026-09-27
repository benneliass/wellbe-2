"use client";

import Link from "next/link";
import { Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { formatShortDate } from "@/lib/adapters";
import type { PendingItemV2 } from "@/lib/pending";
import { buildWhatChanged, homeStatusLine } from "@/lib/home-continuity";
import { useDelta, useLastVisitSince } from "@/lib/home-hooks";
import { useResults } from "@/lib/records-hooks";
import styles from "./WhatChanged.module.css";

type DeltaEventV2 = components["schemas"]["DeltaEventV2"];

const REASON_LABEL: Record<string, string> = {
  "New open item": "New open loop",
  "Open item changed": "Open loop updated",
  "Item resolved": "Loop resolved",
  "Item closed": "Loop closed",
};

function hrefFor(event: DeltaEventV2, pending: PendingItemV2[]): string | null {
  if (event.source.ref_type === "health_thread") return `/threads/${event.source.source_id}`;
  if (event.source.ref_type === "pending_item") {
    const item = pending.find((p) => p.pending_item_id === event.source.source_id);
    return item ? `/threads/${item.primary_thread_id}` : null;
  }
  return null;
}

/**
 * Home's L0/L1 opener (WEL-145): one calm "what changed since you last looked"
 * headline plus the holistic status line, from /v2/delta, /v2/results and the
 * open loops. A few one-line changes link into their thread; the full digest
 * lives on /delta. Never a timeline, graph or metric wall.
 */
export function WhatChanged({ pending }: { pending: PendingItemV2[] }) {
  const since = useLastVisitSince();
  const delta = useDelta(since);
  const results = useResults();

  const windowStart = since ?? delta.data?.window_since ?? null;
  const ready = delta.isSuccess && windowStart !== null;
  const summary = ready
    ? buildWhatChanged({
        since: windowStart,
        events: delta.data.events ?? [],
        resultDates: (results.data?.analytes ?? []).map((a) => a.latest.observed_at),
        pending,
        now: new Date(),
      })
    : null;
  const status = homeStatusLine(pending);

  return (
    <section className={styles.wrap} aria-labelledby="what-changed-headline">
      <h2 id="what-changed-headline" className={styles.headline}>
        {summary ? summary.headline : delta.isError ? "Here's where things stand" : "Catching up on what changed…"}
      </h2>
      <p className={styles.status}>{status}</p>

      {summary && summary.recent.length > 0 && (
        <ul className={styles.list} aria-label="Recent changes">
          {summary.recent.map((e) => {
            const href = hrefFor(e, pending);
            const when = formatShortDate(e.occurred_at);
            const body = (
              <>
                <span className={styles.kind}>{REASON_LABEL[e.ranking_reason] ?? e.ranking_reason}</span>
                <span className={styles.title}>{e.title}</span>
                {when && <span className={styles.when}>{when}</span>}
              </>
            );
            return (
              <li key={e.id}>
                {href ? (
                  <Link href={href} className={styles.row}>
                    {body}
                  </Link>
                ) : (
                  <span className={styles.row}>{body}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {summary && (
        <Link href="/delta" className={styles.all}>
          Everything that changed <Icon name="arrow-right" size={14} />
        </Link>
      )}
    </section>
  );
}
