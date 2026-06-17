"use client";

import { useCallback, useEffect, useState } from "react";
import { Button, Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import styles from "./SharedPacketView.module.css";

type SharedView = components["schemas"]["SharedPacketView"];

const CLASS_LABELS: Record<string, string> = {
  direct_source_fact: "From records",
  patient_reported: "Patient's words",
  generated_synthesis: "Summary",
  generated_inference: "Inference",
  source_record_diagnosis: "On record",
};

type Status = "loading" | "ok" | "passcode" | "gone";

export function SharedPacketView({ token }: { token: string }) {
  const [status, setStatus] = useState<Status>("loading");
  const [view, setView] = useState<SharedView | null>(null);
  const [passcode, setPasscode] = useState("");

  const load = useCallback(
    async (code?: string) => {
      const { data, error } = await getApiClient().GET("/v2/share/{token}", {
        params: {
          path: { token },
          header: code ? { "X-Share-Passcode": code } : undefined,
        },
      });
      if (error || !data) {
        // A passcode-protected link returns 404 until the right passcode is given.
        setStatus((prev) => (prev === "loading" ? "passcode" : "gone"));
        return;
      }
      setView(data);
      setStatus("ok");
    },
    [token],
  );

  useEffect(() => {
    void load();
  }, [load]);

  if (status === "loading") {
    return (
      <div className={styles.center}>
        <Icon name="clock" size={22} />
        <p>Opening shared packet…</p>
      </div>
    );
  }

  if (status === "gone") {
    return (
      <div className={styles.center}>
        <Icon name="lock" size={22} />
        <h1>This link is no longer active</h1>
        <p>It may have been revoked by the patient, expired, or the passcode was incorrect.</p>
      </div>
    );
  }

  if (status === "passcode") {
    return (
      <div className={styles.center}>
        <Icon name="lock" size={22} />
        <h1>This packet is passcode-protected</h1>
        <p>Enter the passcode the patient shared with you.</p>
        <div className={styles.passRow}>
          <input
            className={styles.passInput}
            placeholder="Passcode"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
          />
          <Button variant="primary" onClick={() => load(passcode)} disabled={!passcode.trim()}>
            Open
          </Button>
        </div>
      </div>
    );
  }

  if (!view) return null;

  return (
    <div className={styles.page}>
      <div className={styles.sheet}>
        <h1 className={styles.title}>{view.title}</h1>
        <div className={styles.review}>
          <Icon name="info" size={14} />
          <span>{view.review_note}</span>
        </div>

        <div className={styles.statements}>
          {(view.statements ?? []).map((s) => (
            <div key={s.statement_id} className={styles.stmt}>
              <p>{s.text}</p>
              <div className={styles.meta}>
                <span className={styles.chip} data-absent={s.absent || undefined}>
                  {s.absent
                    ? `Known gap: ${s.absence_reason ?? "unavailable"}`
                    : (CLASS_LABELS[s.classification] ?? s.classification)}
                </span>
                {(s.source_refs ?? []).map((ref, i) => (
                  <span key={i} className={styles.source}>
                    <Icon name="badge-check" size={11} />
                    {ref.label ?? ref.ref_type}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <p className={styles.foot}>
          <Icon name="clock" size={12} /> Access expires{" "}
          {new Date(view.expires_at).toLocaleString()}
        </p>
      </div>
    </div>
  );
}
