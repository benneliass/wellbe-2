"use client";

import { useState } from "react";
import { Button, Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient } from "@/lib/api";
import { useSession } from "@/lib/useSession";
import { useThreads } from "@/lib/hooks";
import { StateNote } from "@/components/placeholder/StateNote";
import { PacketShareSheet } from "./PacketShareSheet";
import styles from "./PrepareLive.module.css";

type VisitPacket = components["schemas"]["VisitPacketV2"];
type Statement = components["schemas"]["VisitPacketStatementV2"];

const CLASS_LABELS: Record<string, string> = {
  direct_source_fact: "From your records",
  patient_reported: "Your words",
  generated_synthesis: "Summary",
  generated_inference: "Inference",
  source_record_diagnosis: "On record",
  new_ai_diagnosis: "Blocked",
};

const LAYER_LABELS: Record<string, string> = {
  patient_prep: "What you want to raise",
  summary: "Source-linked summary",
};

function StatementCard({
  statement,
  onToggle,
}: {
  statement: Statement;
  onToggle: (id: string, included: boolean) => void;
}) {
  return (
    <div className={styles.stmt} data-off={!statement.included || undefined}>
      <button
        type="button"
        className={styles.check}
        data-on={statement.included || undefined}
        aria-label={statement.included ? "Included — click to remove" : "Deselected — click to include"}
        onClick={() => onToggle(statement.statement_id, !statement.included)}
      >
        {statement.included && <Icon name="check" size={12} />}
      </button>
      <div className={styles.stmtBody}>
        <p className={styles.stmtText}>{statement.text}</p>
        <div className={styles.stmtMeta}>
          <span className={styles.chip} data-absent={statement.absent || undefined}>
            {statement.absent
              ? `Known gap: ${statement.absence_reason ?? "unavailable"}`
              : (CLASS_LABELS[statement.classification] ?? statement.classification)}
          </span>
          {(statement.source_refs ?? []).map((ref, i) => (
            <span key={i} className={styles.source}>
              <Icon name="badge-check" size={11} />
              {ref.label ?? ref.ref_type}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function PrepareLive() {
  const signedIn = Boolean(useSession()?.patientId);
  const threadsQuery = useThreads();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [questions, setQuestions] = useState("");
  const [goals, setGoals] = useState("");
  const [packet, setPacket] = useState<VisitPacket | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showShare, setShowShare] = useState(false);
  const [exported, setExported] = useState(false);

  if (!signedIn && threadsQuery.isError) {
    return (
      <StateNote
        icon="lock"
        title="Sign in to prepare a packet"
        description="Once you're signed in, you can build a source-linked packet from your threads."
      />
    );
  }

  const threads = threadsQuery.data ?? [];

  function toggleThread(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function splitLines(value: string): string[] {
    return value
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function handleGenerate() {
    setError(null);
    setBusy(true);
    setExported(false);
    try {
      const { data, error: apiError } = await getApiClient().POST("/v2/visit-packets", {
        body: {
          title: "Visit packet",
          thread_ids: Array.from(selected),
          include_summary: true,
          prep: {
            questions: splitLines(questions),
            goals: splitLines(goals),
            observations: [],
          },
        },
      });
      if (apiError || !data) throw new Error("Couldn't build the packet. Please try again.");
      setPacket({ ...data, statements: data.statements ?? [] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong building the packet.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatement(id: string, included: boolean) {
    if (!packet) return;
    setPacket({
      ...packet,
      statements: (packet.statements ?? []).map((s) =>
        s.statement_id === id ? { ...s, included } : s,
      ),
    });
    await getApiClient().PATCH("/v2/visit-packets/{packet_id}", {
      params: { path: { packet_id: packet.packet_id } },
      body: { inclusions: [{ statement_id: id, included }] },
    });
  }

  async function handleExport() {
    if (!packet) return;
    await getApiClient().POST("/v2/visit-packets/{packet_id}/export", {
      params: { path: { packet_id: packet.packet_id } },
    });
    setExported(true);
  }

  if (!packet) {
    return (
      <div className={styles.wrap}>
        <p className={styles.intro}>
          Build a one-page, source-linked packet for an upcoming visit. Pick the concerns to
          include and add what you want to raise — you preview and approve everything before any
          sharing.
        </p>

        <div className={styles.section}>
          <div className={styles.sectionHead}>Concerns to include</div>
          {threadsQuery.isLoading ? (
            <p className={styles.muted}>Loading your threads…</p>
          ) : threads.length === 0 ? (
            <p className={styles.muted}>
              No threads yet. You can still add questions and goals below.
            </p>
          ) : (
            <div className={styles.threadList}>
              {threads.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={styles.threadRow}
                  data-on={selected.has(t.id) || undefined}
                  onClick={() => toggleThread(t.id)}
                >
                  <span className={styles.check} data-on={selected.has(t.id) || undefined}>
                    {selected.has(t.id) && <Icon name="check" size={12} />}
                  </span>
                  <span className={styles.threadTitle}>{t.title}</span>
                </button>
              ))}
            </div>
          )}
          <p className={styles.hintLine}>
            Leave all unchecked to include every active concern.
          </p>
        </div>

        <div className={styles.section}>
          <div className={styles.sectionHead}>Questions you want to ask</div>
          <textarea
            className={styles.textarea}
            placeholder="One question per line…"
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
          />
        </div>

        <div className={styles.section}>
          <div className={styles.sectionHead}>Your goals for the visit</div>
          <textarea
            className={styles.textarea}
            placeholder="One goal per line…"
            value={goals}
            onChange={(e) => setGoals(e.target.value)}
          />
        </div>

        {error && (
          <p className={styles.error}>
            <Icon name="alert-circle" size={14} /> {error}
          </p>
        )}

        <div className={styles.actions}>
          <Button variant="primary" icon="sparkles" onClick={handleGenerate} disabled={busy}>
            {busy ? "Building…" : "Build packet"}
          </Button>
        </div>
      </div>
    );
  }

  const allStatements = packet.statements ?? [];
  const byLayer = (layer: string) => allStatements.filter((s) => s.layer === layer);
  const includedCount = allStatements.filter((s) => s.included).length;

  return (
    <div className={styles.wrap}>
      <div className={styles.previewHead}>
        <div>
          <div className={styles.previewTitle}>{packet.title}</div>
          <div className={styles.muted}>
            {includedCount} of {allStatements.length} items included · every statement links to its
            source
          </div>
        </div>
        <div className={styles.actions}>
          <Button variant="tertiary" icon="rotate-ccw" onClick={() => setPacket(null)}>
            Start over
          </Button>
          <Button variant="secondary" icon="file-text" onClick={handleExport}>
            {exported ? "Exported" : "Export copy"}
          </Button>
          <Button variant="primary" icon="share" onClick={() => setShowShare(true)}>
            Share
          </Button>
        </div>
      </div>

      {exported && (
        <p className={styles.exportNote}>
          <Icon name="info" size={13} /> Exported a copy. A saved or forwarded copy can&rsquo;t be
          recalled — only link sharing can be revoked.
        </p>
      )}

      {["patient_prep", "summary"].map((layer) => {
        const items = byLayer(layer);
        if (items.length === 0) return null;
        return (
          <div key={layer} className={styles.section}>
            <div className={styles.sectionHead}>{LAYER_LABELS[layer]}</div>
            <div className={styles.stmtList}>
              {items.map((s) => (
                <StatementCard key={s.statement_id} statement={s} onToggle={toggleStatement} />
              ))}
            </div>
          </div>
        );
      })}

      {showShare && (
        <PacketShareSheet
          packetId={packet.packet_id}
          packetTitle={packet.title}
          onClose={() => setShowShare(false)}
        />
      )}
    </div>
  );
}
