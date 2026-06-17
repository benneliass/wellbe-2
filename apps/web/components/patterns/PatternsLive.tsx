"use client";

import { useEffect, useState } from "react";
import { Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient, devSessionConfigured } from "@/lib/api";
import { StateNote } from "@/components/placeholder/StateNote";
import styles from "./PatternsLive.module.css";

type PatternsResponse = components["schemas"]["PatternsResponseV2"];
type Pattern = components["schemas"]["PatternCandidateV2"];

const TIER_LABEL: Record<string, string> = {
  stronger_signal: "Stronger signal",
  moderate_signal: "Moderate signal",
  early_signal: "Early signal",
};

export function PatternsLive() {
  const [data, setData] = useState<PatternsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!devSessionConfigured) {
      setLoading(false);
      return;
    }
    let active = true;
    (async () => {
      try {
        const { data: resp, error: apiError } = await getApiClient().GET(
          "/v2/patterns",
          { params: { query: {} } },
        );
        if (!active) return;
        if (apiError || !resp) {
          setError("Couldn't load your patterns right now. Please try again.");
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
  }, []);

  if (!devSessionConfigured) {
    return (
      <div className={styles.wrap}>
        <StateNote
          icon="lock"
          title="Sign in to check your patterns"
          description="Pattern check looks across your own records, so it needs you signed in first. It never diagnoses — it surfaces source-linked connections you can explore."
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.wrap}>
        <p className={styles.hint}>
          <Icon name="bar-chart-3" size={14} />
          Looking across your own records…
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

  const patterns = data?.patterns ?? [];

  return (
    <div className={styles.wrap}>
      <p className={styles.hint}>
        <Icon name="lock" size={13} />
        {data?.note}
      </p>

      {patterns.length === 0 ? (
        <StateNote
          icon="bar-chart-3"
          title="No patterns yet"
          description="As you log more — symptoms, results, notes — WellBe will surface connections across your own records here. Always source-linked, never a diagnosis."
        />
      ) : (
        <ul className={styles.list}>
          {patterns.map((p) => (
            <PatternCard key={p.id} pattern={p} />
          ))}
        </ul>
      )}
    </div>
  );
}

function PatternCard({ pattern: p }: { pattern: Pattern }) {
  return (
    <li
      className={styles.card}
      data-contradiction={p.is_contradiction ? "true" : undefined}
    >
      <div className={styles.headline}>
        <span className={styles.subject}>{p.subject_label}</span>
        <span className={styles.relation}>{p.relation_phrase}</span>
        <span className={styles.object}>{p.object_label}</span>
      </div>

      <div className={styles.tags}>
        {p.is_contradiction ? (
          <span className={styles.tier} data-kind="contradiction">
            <Icon name="alert-triangle" size={11} />
            Conflict in your records
          </span>
        ) : (
          <span className={styles.tier}>
            <Icon name="bar-chart-3" size={11} />
            {TIER_LABEL[p.evidence_tier] ?? "Signal"}
          </span>
        )}
        {(p.sources ?? []).map((s, i) => (
          <span key={i} className={styles.source}>
            <Icon name="badge-check" size={11} />
            {s.label}
          </span>
        ))}
      </div>

      <p className={styles.caveat}>{p.caveat}</p>

      {p.missing_data_note && (
        <p className={styles.note}>
          <Icon name="info" size={13} />
          {p.missing_data_note}
        </p>
      )}
      {p.confounder_note && (
        <p className={styles.note}>
          <Icon name="git-fork" size={13} />
          {p.confounder_note}
        </p>
      )}

      {(p.alternative_explanations ?? []).length > 0 && (
        <details className={styles.alts}>
          <summary>Other ways to read this</summary>
          <ul>
            {(p.alternative_explanations ?? []).map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}
