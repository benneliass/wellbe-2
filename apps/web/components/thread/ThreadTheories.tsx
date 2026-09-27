"use client";

import { useId, useState, type FormEvent } from "react";
import { Button, Chip, type Tone } from "@wellbe/ui";
import { formatShortDate } from "@/lib/adapters";
import {
  EvaluationProblem,
  useEvaluateTheory,
  useInvestigationTheories,
  useTheoryEvaluations,
  useThreadEvidenceOptions,
  useThreadInvestigations,
  type EvidenceOption,
  type InvestigationV2,
  type TheoryAssessment,
  type TheoryV2,
} from "@/lib/theories";
import { Panel } from "./Panel";
import styles from "./ThreadTheories.module.css";

const RATIONALE_MAX = 2000;

// The user's own marks. Calm tones only: a user's evaluation is never an alarm.
const ASSESSMENTS: { value: TheoryAssessment; label: string; hint: string }[] = [
  { value: "supported", label: "Supported", hint: "My data fits this so far" },
  { value: "weakened", label: "Weakened", hint: "Some of my data points the other way" },
  { value: "ruled_out", label: "Ruled out", hint: "My data doesn't fit this" },
  { value: "under_review", label: "Under review", hint: "Still looking into it" },
  { value: "open", label: "Reopen", hint: "Start fresh on this theory" },
];

const ASSESSMENT_TONE: Record<string, Tone> = {
  supported: "teal",
  weakened: "neutral",
  ruled_out: "neutral",
  under_review: "violet",
  open: "neutral",
};

/** Investigations that include this thread, with their theories and the user's evaluations. */
export function ThreadTheories({ threadId }: { threadId: string }) {
  const investigations = useThreadInvestigations(threadId);
  const evidence = useThreadEvidenceOptions(threadId);

  if (investigations.isLoading || !investigations.data?.length) return null;

  return (
    <div className={styles.stack}>
      {investigations.data.map((inv) => (
        <InvestigationTheories
          key={inv.investigation_id}
          investigation={inv}
          evidence={evidence.data ?? []}
        />
      ))}
    </div>
  );
}

function InvestigationTheories({
  investigation,
  evidence,
}: {
  investigation: InvestigationV2;
  evidence: EvidenceOption[];
}) {
  const { data: theories = [], isLoading } = useInvestigationTheories(
    investigation.investigation_id,
  );
  const count = theories.length === 1 ? "1 theory" : `${theories.length} theories`;

  return (
    <Panel title={investigation.primary_question} icon="flask-conical" count={count}>
      {isLoading && <p className={styles.muted}>Loading theories…</p>}
      {!isLoading && theories.length === 0 && (
        <p className={styles.muted}>No theories in this investigation yet.</p>
      )}
      <ul className={styles.theories}>
        {theories.map((t) => (
          <TheoryItem
            key={t.theory_id}
            theory={t}
            investigationId={investigation.investigation_id}
            evidence={evidence}
          />
        ))}
      </ul>
    </Panel>
  );
}

function TheoryItem({
  theory,
  investigationId,
  evidence,
}: {
  theory: TheoryV2;
  investigationId: string;
  evidence: EvidenceOption[];
}) {
  const [editing, setEditing] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const history = useTheoryEvaluations(theory.theory_id, showHistory);
  const latest = theory.latest_evaluation;

  return (
    <li className={styles.theory}>
      <div className={styles.theoryHead}>
        <p className={styles.theoryLabel}>{theory.label}</p>
        {theory.assessment && (
          <Chip tone={ASSESSMENT_TONE[theory.assessment] ?? "neutral"} size="sm">
            {ASSESSMENTS.find((a) => a.value === theory.assessment)?.label ?? theory.assessment}
          </Chip>
        )}
      </div>
      {latest && (
        <p className={styles.latest}>
          {latest.assessment_label}
          {formatShortDate(latest.created_at) && ` · ${formatShortDate(latest.created_at)}`}
        </p>
      )}
      <div className={styles.actions}>
        {!editing && (
          <Button size="sm" variant="secondary" icon="pencil" onClick={() => setEditing(true)}>
            Evaluate
          </Button>
        )}
        <Button
          size="sm"
          variant="ghost"
          icon="clock"
          aria-expanded={showHistory}
          onClick={() => setShowHistory((v) => !v)}
        >
          {showHistory ? "Hide history" : "History"}
        </Button>
      </div>
      {editing && (
        <EvaluateForm
          theory={theory}
          investigationId={investigationId}
          evidence={evidence}
          onDone={() => {
            setEditing(false);
            setShowHistory(true);
          }}
          onCancel={() => setEditing(false)}
        />
      )}
      {showHistory && (
        <div className={styles.history} aria-live="polite">
          {history.isLoading && <p className={styles.muted}>Loading history…</p>}
          {history.data?.length === 0 && (
            <p className={styles.muted}>You haven&apos;t evaluated this theory yet.</p>
          )}
          <ol className={styles.historyList}>
            {history.data?.map((ev) => (
              <li key={ev.evaluation_id} className={styles.historyItem}>
                <span className={styles.historyTitle}>{ev.assessment_label}</span>
                <span className={styles.muted}>
                  {formatShortDate(ev.created_at)} · {ev.evidence_refs?.length ?? 0} cited
                </span>
                <q className={styles.rationale}>{ev.rationale}</q>
              </li>
            ))}
          </ol>
        </div>
      )}
    </li>
  );
}

function EvaluateForm({
  theory,
  investigationId,
  evidence,
  onDone,
  onCancel,
}: {
  theory: TheoryV2;
  investigationId: string;
  evidence: EvidenceOption[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const formId = useId();
  const evaluate = useEvaluateTheory();
  const [status, setStatus] = useState<TheoryAssessment | null>(null);
  const [cited, setCited] = useState<Set<string>>(new Set());
  const [rationale, setRationale] = useState("");
  const [idempotencyKey] = useState(() => `web-eval-${crypto.randomUUID()}`);

  const ready = status !== null && cited.size > 0 && rationale.trim().length > 0;
  const problem = evaluate.error instanceof EvaluationProblem ? evaluate.error : null;
  const conflict = problem?.status === 409;

  function toggle(id: string) {
    setCited((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!ready || status === null) return;
    evaluate.mutate(
      {
        theoryId: theory.theory_id,
        investigationId,
        toStatus: status,
        rationale: rationale.trim(),
        evidenceRefs: evidence
          .filter((o) => cited.has(o.id))
          .map((o) => ({ kind: o.kind, id: o.id })),
        expectedVersion: theory.version ?? 1,
        idempotencyKey,
      },
      { onSuccess: onDone },
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-labelledby={`${formId}-title`}>
      <p id={`${formId}-title`} className={styles.formTitle}>
        How does your data look for this theory?
      </p>

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>Your evaluation</legend>
        <div className={styles.options}>
          {ASSESSMENTS.map((a) => (
            <label key={a.value} className={styles.option} data-on={status === a.value || undefined}>
              <input
                type="radio"
                name={`${formId}-status`}
                value={a.value}
                checked={status === a.value}
                onChange={() => setStatus(a.value)}
              />
              <span className={styles.optionLabel}>{a.label}</span>
              <span className={styles.optionHint}>{a.hint}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>Evidence from this thread (pick at least one)</legend>
        {evidence.length === 0 ? (
          <p className={styles.muted}>
            This thread has no entries to cite yet. Add a note or result to the thread first.
          </p>
        ) : (
          <div className={styles.evidence}>
            {evidence.map((o) => (
              <label key={o.id} className={styles.evidenceItem}>
                <input type="checkbox" checked={cited.has(o.id)} onChange={() => toggle(o.id)} />
                <span>{o.label}</span>
              </label>
            ))}
          </div>
        )}
      </fieldset>

      <label className={styles.legend} htmlFor={`${formId}-rationale`}>
        Why? (a short note in your own words)
      </label>
      <textarea
        id={`${formId}-rationale`}
        className={styles.textarea}
        rows={3}
        maxLength={RATIONALE_MAX}
        value={rationale}
        onChange={(e) => setRationale(e.target.value)}
        placeholder="e.g. My headaches continued on days without screens."
      />

      {problem && (
        <p className={styles.error} role="alert">
          {conflict
            ? "This theory changed since you opened it. We've refreshed it — please review and try again."
            : problem.message}
        </p>
      )}

      <p className={styles.note}>
        This is your own judgement about your data, not a diagnosis. You can change it anytime.
      </p>

      <div className={styles.actions}>
        <Button size="sm" onClick={() => submit()} disabled={!ready || evaluate.isPending}>
          {evaluate.isPending ? "Saving…" : "Save evaluation"}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel} disabled={evaluate.isPending}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
