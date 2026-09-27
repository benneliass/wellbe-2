"use client";

import Link from "next/link";
import { Icon } from "@wellbe/ui";
import { continuityLine } from "@/lib/home-continuity";
import { useContinuityCounts } from "@/lib/home-hooks";
import styles from "./Launcher.module.css";

/**
 * One quiet line of continuity under the Ask bar — "5 threads carrying forward ·
 * 1 open loop · 1 thing noticed → Full View" — from /v1/threads,
 * /v2/pending-items and /v1/things-noticed. Its height is reserved while loading
 * so the approved layout never jumps; it renders nothing if the data can't load.
 */
export function ContinuityStrip() {
  const counts = useContinuityCounts();
  if (counts === null) return <div className={styles.continuity} aria-hidden="true" />;

  const line = continuityLine(counts) || "Nothing carrying forward yet";
  return (
    <div className={styles.continuity}>
      <Link href="/workspace" className={styles.continuityLink}>
        <span className={styles.continuityText}>{line}</span>
        <span className={styles.continuityGo}>
          Full View <Icon name="arrow-right" size={14} />
        </span>
      </Link>
    </div>
  );
}
