"use client";

import { useEffect, useState } from "react";
import { Chip, ConfidenceDots, Icon, type Tone } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import styles from "./Launcher.module.css";

type SignalsSummary = components["schemas"]["SignalsSummaryV2"];
type SignalArea = components["schemas"]["SignalArea"];

const PANEL_ID = "launcher-signals-panel";

// Coverage/recency tone — calm by design. "recent_data" is teal (brand calm),
// not green, to avoid implying a clinical "all good". Stale/missing are neutral,
// never amber/red: missing data is an honest unknown, never an alarm.
const STATUS_TONE: Record<string, Tone> = {
  recent_data: "teal",
  stale_data: "neutral",
  no_data: "neutral",
};

const CONF_DOTS: Record<string, number> = { good: 4, limited: 2, none: 0 };

/** Calm fallback shown before sign-in — never asserts a status. */
const SIGNED_OUT: SignalsSummary = {
  schema_version: "c13.signals.v2",
  headline: "Your health signals",
  coverage_label: "Sign in to see what's current in your records",
  areas_with_data: 0,
  areas_total: 6,
  areas: [],
  note: "",
  suppressed: true,
  not_diagnosis: true,
};

export function SignalsPanel() {
  const session = useSession();
  const signedIn = Boolean(session?.patientId);
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<SignalsSummary | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!signedIn) {
      setData(null);
      return;
    }
    let active = true;
    setLoading(true);
    (async () => {
      try {
        const { data: resp } = await getApiClient().GET("/v2/signals");
        if (active && resp) setData(resp);
      } catch {
        /* keep the calm default on any error */
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [signedIn]);

  const summary = data ?? (signedIn ? null : SIGNED_OUT);
  const headline = loading
    ? "Checking your records…"
    : summary?.headline ?? "Your health signals";
  const detail = loading ? "One moment" : summary?.coverage_label ?? "";
  const areas: SignalArea[] = summary?.areas ?? [];

  return (
    <div className={styles.signalsWrap}>
      <button
        type="button"
        className={styles.signals}
        data-open={open || undefined}
        aria-expanded={open}
        aria-controls={PANEL_ID}
        onClick={() => setOpen((v) => !v)}
        disabled={areas.length === 0}
      >
        <span className={styles.signalsIcon}>
          <Icon name="activity" size={20} />
        </span>
        <span className={styles.signalsText}>
          <b>{headline}</b>
          <span>{detail}</span>
        </span>
        {areas.length > 0 && (
          <Icon name="chevron-down" size={18} className={styles.signalsChev} />
        )}
      </button>
      <div
        id={PANEL_ID}
        className={styles.signalsPanel}
        data-open={open || undefined}
        role="region"
        aria-label="Signal breakdown"
        aria-hidden={!open}
      >
        <div className={styles.signalRows}>
          {summary?.note && <p className={styles.signalsNote}>{summary.note}</p>}
          <ul className={styles.signalList}>
            {areas.map((a) => (
              <li key={a.id} className={styles.signalRow}>
                <span className={styles.signalLabel}>{a.label}</span>
                <span className={styles.signalValue}>{a.recency_note}</span>
                <Chip tone={STATUS_TONE[a.status] ?? "neutral"} size="sm">
                  {a.status_label}
                </Chip>
                <ConfidenceDots level={CONF_DOTS[a.confidence] ?? 0} />
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
