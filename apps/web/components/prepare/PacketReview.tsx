"use client";

import { useState } from "react";
import { Button, EvidenceDrawer, Icon, ReviewMarkerList, SourceMarker } from "@wellbe/ui";
import type { EvidenceSource } from "@wellbe/ui";
import {
  ABSENCE_LABELS,
  LAYER_LABELS,
  isEditable,
  reviewMarkersFor,
  toEvidenceSource,
  type Statement,
  type VisitPacket,
} from "./packetFormat";
import styles from "./PrepareLive.module.css";

function StatementReviewCard({
  statement,
  onToggle,
  onEdit,
  onOpenSources,
}: {
  statement: Statement;
  onToggle: (id: string, included: boolean) => void;
  onEdit: (id: string, text: string) => Promise<void>;
  onOpenSources: (statement: Statement, sources: EvidenceSource[]) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(statement.text);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sources = (statement.source_refs ?? []).map((ref, i) => toEvidenceSource(statement, ref, i));
  const included = statement.included ?? true;
  const editId = `stmt-edit-${statement.statement_id}`;

  async function save() {
    const text = draft.trim();
    if (!text) {
      setError("Add some words, or remove this item instead.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onEdit(statement.statement_id, text);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save that change.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className={styles.stmt} data-off={!included || undefined}>
      <div className={styles.stmtBody}>
        {editing ? (
          <div className={styles.editBox}>
            <label htmlFor={editId} className={styles.srOnly}>
              Edit this item
            </label>
            <textarea
              id={editId}
              className={styles.textarea}
              value={draft}
              maxLength={2000}
              onChange={(e) => setDraft(e.target.value)}
            />
            {error && (
              <p className={styles.error}>
                <Icon name="alert-circle" size={14} /> {error}
              </p>
            )}
            <div className={styles.actions}>
              <Button variant="primary" onClick={save} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </Button>
              <Button
                variant="tertiary"
                onClick={() => {
                  setDraft(statement.text);
                  setEditing(false);
                  setError(null);
                }}
                disabled={saving}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <p className={styles.stmtText}>{statement.text}</p>
        )}
        <div className={styles.stmtMeta}>
          {statement.absent ? (
            <span className={styles.chip} data-absent>
              {ABSENCE_LABELS[statement.absence_reason ?? "unavailable"] ?? "Not available"}
            </span>
          ) : (
            <ReviewMarkerList values={reviewMarkersFor(statement)} />
          )}
          {sources.length > 0 && (
            <SourceMarker
              displayLabel={sources[0]!.displayLabel}
              component={sources[0]!.component}
              kind={sources[0]!.kind}
              count={sources.length}
              onOpen={() => onOpenSources(statement, sources)}
            />
          )}
          {!included && <span className={styles.offLabel}>Removed — won&rsquo;t be shared</span>}
        </div>
      </div>
      {!editing && (
        <div className={styles.stmtActions}>
          {included && isEditable(statement) && (
            <Button
              variant="tertiary"
              icon="pencil"
              aria-label={`Edit: ${statement.text}`}
              onClick={() => {
                setDraft(statement.text);
                setEditing(true);
              }}
            >
              Edit
            </Button>
          )}
          <Button
            variant="tertiary"
            icon={included ? "x" : "plus"}
            aria-label={`${included ? "Remove" : "Add back"}: ${statement.text}`}
            onClick={() => onToggle(statement.statement_id, !included)}
          >
            {included ? "Remove" : "Add back"}
          </Button>
        </div>
      )}
    </li>
  );
}

/** Step 2 — the source-linked preview. Nothing leaves WellBe from this step. */
export function PacketReview({
  packet,
  onToggle,
  onEdit,
  onBack,
  onContinue,
}: {
  packet: VisitPacket;
  onToggle: (id: string, included: boolean) => void;
  onEdit: (id: string, text: string) => Promise<void>;
  onBack: () => void;
  onContinue: () => void;
}) {
  const [drawer, setDrawer] = useState<{ claim: string; sources: EvidenceSource[] } | null>(null);
  const all = packet.statements ?? [];
  const includedCount = all.filter((s) => s.included ?? true).length;

  return (
    <div>
      <div className={styles.previewHead}>
        <div>
          <h2 className={styles.previewTitle}>{packet.title}</h2>
          <div className={styles.muted}>
            {includedCount} of {all.length} items included · every statement links to its source
          </div>
        </div>
      </div>

      <div className={styles.approveNote} role="note">
        <Icon name="shield-check" size={16} />
        <span>
          <b>You approve everything before sharing.</b> Nothing is sent from this step. Remove
          anything you don&rsquo;t want included, and reword your own questions or goals. Summary
          items stay as their source says — remove them if they&rsquo;re not right.
        </span>
      </div>

      {["patient_prep", "summary"].map((layer) => {
        const items = all.filter((s) => s.layer === layer);
        if (items.length === 0) return null;
        return (
          <section key={layer} className={styles.section} aria-label={LAYER_LABELS[layer]}>
            <h3 className={styles.sectionHead}>{LAYER_LABELS[layer]}</h3>
            <ul className={styles.stmtList}>
              {items.map((s) => (
                <StatementReviewCard
                  key={s.statement_id}
                  statement={s}
                  onToggle={onToggle}
                  onEdit={onEdit}
                  onOpenSources={(st, sources) => setDrawer({ claim: st.text, sources })}
                />
              ))}
            </ul>
          </section>
        );
      })}

      <div className={styles.stepFoot}>
        <Button variant="tertiary" icon="arrow-left" onClick={onBack}>
          Back to choose
        </Button>
        <Button
          variant="primary"
          icon="check"
          onClick={onContinue}
          disabled={includedCount === 0}
        >
          Approve and continue
        </Button>
      </div>
      {includedCount === 0 && (
        <p className={styles.hintLine}>Add back at least one item to continue.</p>
      )}

      <EvidenceDrawer
        open={drawer !== null}
        onClose={() => setDrawer(null)}
        title="Where this comes from"
        claim={drawer?.claim}
        sources={drawer?.sources ?? []}
      />
    </div>
  );
}
