"use client";

import { useState } from "react";
import Link from "next/link";
import { Chip, Icon, type IconName } from "@wellbe/ui";
import type { PendingItemV2 } from "@/lib/pending";
import {
  groupOpenLoops,
  LOOP_GROUPS,
  loopStateLabel,
  nextStepFor,
  type LoopGroupId,
} from "@/lib/home-continuity";
import styles from "./OpenLoops.module.css";

const GROUP_ICON: Record<LoopGroupId, IconName> = {
  attention: "clock",
  motion: "activity",
  steady: "clipboard-list",
};

/**
 * Follow-ups the person is carrying forward, grouped by what they can do
 * (WEL-145): Needs attention (due / still open past its date), In motion
 * (waiting on a result, referral or appointment) and Steady (folded until asked
 * for). Each row carries one plain next step. Overdue raises order, never alarm.
 */
export function OpenLoops({
  items,
  linkToThread = true,
  title = "Open loops",
}: {
  items: PendingItemV2[];
  linkToThread?: boolean;
  title?: string;
}) {
  const [steadyOpen, setSteadyOpen] = useState(false);
  const groups = groupOpenLoops(items);
  const total = groups.attention.length + groups.motion.length + groups.steady.length;
  if (total === 0) return null;

  const renderGroup = (id: LoopGroupId, rows: PendingItemV2[]) => (
    <div className={styles.group} data-group={id} key={id}>
      <h3 className={styles.groupHead}>
        <Icon name={GROUP_ICON[id]} size={14} />
        {LOOP_GROUPS[id].label}
        <span className={styles.count}>{rows.length}</span>
      </h3>
      <ul className={styles.list}>
        {rows.map((item) => {
          const state = loopStateLabel(item);
          const body = (
            <>
              <span className={styles.text}>
                <span className={styles.title}>{item.title}</span>
                <span className={styles.next}>{nextStepFor(item)}</span>
              </span>
              <Chip tone={state.tone} size="sm">
                {state.label}
              </Chip>
            </>
          );
          return (
            <li key={item.pending_item_id} data-status={item.status}>
              {linkToThread ? (
                <Link href={`/threads/${item.primary_thread_id}`} className={styles.row}>
                  {body}
                  <Icon name="chevron-right" size={16} />
                </Link>
              ) : (
                <div className={styles.row}>{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );

  return (
    <section className={styles.loops} aria-label={title}>
      <h2 className={styles.head}>{title}</h2>
      {groups.attention.length > 0 && renderGroup("attention", groups.attention)}
      {groups.motion.length > 0 && renderGroup("motion", groups.motion)}
      {groups.steady.length > 0 &&
        (steadyOpen ? (
          renderGroup("steady", groups.steady)
        ) : (
          <button
            type="button"
            className={styles.fold}
            aria-expanded={false}
            onClick={() => setSteadyOpen(true)}
          >
            <Icon name={GROUP_ICON.steady} size={14} />
            {groups.steady.length} steady {groups.steady.length === 1 ? "loop" : "loops"} — nothing due yet
            <Icon name="chevron-down" size={14} />
          </button>
        ))}
    </section>
  );
}
