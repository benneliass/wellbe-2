"use client";

import { useEffect, useState } from "react";
import { Icon, type IconName } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import { StateNote } from "@/components/placeholder/StateNote";
import styles from "./DeltaLive.module.css";

type DeltaDigest = components["schemas"]["DeltaDigestV2"];
type DeltaEvent = components["schemas"]["DeltaEventV2"];

const CATEGORY: Record<string, { label: string; icon: IconName }> = {
  open_loop: { label: "Open item", icon: "circle-help" },
  lifecycle: { label: "Status", icon: "activity" },
  new_fact: { label: "New", icon: "plus-circle" },
};

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function DeltaLive() {
  const signedIn = Boolean(useSession()?.patientId);
  const [data, setData] = useState<DeltaDigest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!signedIn) {
      setLoading(false);
      return;
    }
    let active = true;
    (async () => {
      try {
        const { data: resp, error: apiError } = await getApiClient().GET(
          "/v2/delta",
          { params: { query: {} } },
        );
        if (!active) return;
        if (apiError || !resp) {
          setError("Couldn't load your what-changed digest. Please try again.");
          return;
        }
        setData(resp);
      } catch {
        if (active) setError("Couldn't reach WellBe. Check your connection.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [signedIn]);

  if (!signedIn) {
    return (
      <div className={styles.wrap}>
        <StateNote
          icon="activity"
          title="Sign in to see what changed"
          description="Your what-changed digest gathers updates across your own threads and open items. It needs you signed in, and it's always source-linked — never a diagnosis."
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.wrap}>
        <p className={styles.hint}>
          <Icon name="activity" size={14} />
          Gathering what changed…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <p className={styles.error}>{error}</p>
      </div>
    );
  }

  const events = data?.events ?? [];

  return (
    <div className={styles.wrap}>
      <p className={styles.hint}>
        <Icon name="lock" size={13} />
        {data?.note}
      </p>

      {events.length === 0 ? (
        <StateNote
          icon="check-circle-2"
          title="Nothing new to catch up on"
          description="When results, notes, or status updates arrive on your threads, they'll gather here — calmly and source-linked."
        />
      ) : (
        <ul className={styles.list}>
          {events.map((e) => (
            <DeltaItem key={e.id} event={e} />
          ))}
        </ul>
      )}
    </div>
  );
}

function DeltaItem({ event: e }: { event: DeltaEvent }) {
  const cat = CATEGORY[e.category] ?? { label: "Update", icon: "info" as IconName };
  return (
    <li className={styles.card} data-category={e.category}>
      <span className={styles.cat}>
        <Icon name={cat.icon} size={12} />
        {cat.label}
      </span>
      <div className={styles.body}>
        <p className={styles.title}>{e.title}</p>
        <p className={styles.reason}>
          {e.ranking_reason}
          {e.detail ? ` — ${e.detail}` : ""}
        </p>
        <span className={styles.source}>
          <Icon name="badge-check" size={11} />
          {e.source.label}
          {e.occurred_at ? <span className={styles.when}> · {formatWhen(e.occurred_at)}</span> : null}
        </span>
      </div>
    </li>
  );
}
