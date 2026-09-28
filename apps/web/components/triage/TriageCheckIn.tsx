"use client";

import { useEffect, useId, useRef, useState, type RefObject } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import type { components } from "@wellbe/api-client";
import { queryKeys } from "@wellbe/api-client/react-query";
import { Button, Icon } from "@wellbe/ui";
import { getApiClient } from "@/lib/api";
import { useThreads } from "@/lib/hooks";
import styles from "./TriageCheckIn.module.css";

const ONSET_OPTIONS = [
  "Today",
  "In the last few days",
  "Over the last few weeks",
  "Months ago or longer",
  "I'm not sure",
];

const IMPACT_OPTIONS = [
  "Not much",
  "Some things are harder",
  "Hard to do my usual things",
  "I can't do my usual things",
];

type Answers = {
  what: string;
  change: string;
  onset: string;
  onsetNote: string;
  impact: string;
  impactNote: string;
  worry: string;
};

const EMPTY: Answers = {
  what: "",
  change: "",
  onset: "",
  onsetNote: "",
  impact: "",
  impactNote: "",
  worry: "",
};

type Destination = "new" | "existing" | "memory";

const STEPS = [
  { key: "what", question: "What's going on?" },
  { key: "change", question: "How is this different from your normal?" },
  { key: "onset", question: "When did it start?" },
  { key: "impact", question: "How much is it affecting your day?" },
  { key: "worry", question: "What's your main worry or question?" },
] as const;

const REVIEW_STEP = STEPS.length;
const TITLE_MAX = 80;

function withNote(choice: string, note: string): string {
  const n = note.trim();
  if (choice && n) return `${choice} — ${n}`;
  return choice || n;
}

/** The check-in as the user's own words, one labelled line per answer. */
export function composeCheckIn(a: Answers): string {
  const lines = [`What's going on: ${a.what.trim()}`];
  if (a.change.trim()) lines.push(`Different from my normal: ${a.change.trim()}`);
  const onset = withNote(a.onset, a.onsetNote);
  if (onset) lines.push(`Started: ${onset}`);
  const impact = withNote(a.impact, a.impactNote);
  if (impact) lines.push(`Effect on my day: ${impact}`);
  if (a.worry.trim()) lines.push(`Main worry or question: ${a.worry.trim()}`);
  return lines.join("\n");
}

function suggestTitle(what: string): string {
  const firstLine = what.trim().split(/\n|[.!?](\s|$)/)[0] ?? "";
  const t = firstLine.trim();
  return t.length > TITLE_MAX ? `${t.slice(0, TITLE_MAX - 1).trimEnd()}…` : t;
}

type Evaluation = components["schemas"]["TriageEvaluateResponseV2"];
/** "unavailable": the warning-sign check could not run; saving still goes ahead. */
type Check = Evaluation | "unavailable";

/** Urgent treatment only when the Safety Gate itself returned route_urgent. */
function isUrgent(check: Check | null): check is Evaluation {
  return (
    check !== null &&
    check !== "unavailable" &&
    check.route === "route_urgent" &&
    check.safety_gate_decision === "route_urgent"
  );
}

function toRequest(a: Answers): components["schemas"]["TriageEvaluateRequestV2"] {
  return {
    schema_version: "c13.triage.evaluate.request.v2",
    answers: {
      what: a.what.trim(),
      change: a.change.trim(),
      onset: a.onset,
      onset_note: a.onsetNote.trim(),
      impact: a.impact,
      impact_note: a.impactNote.trim(),
      worry: a.worry.trim(),
    },
  };
}

function Backstop() {
  return (
    <aside className={styles.backstop} aria-label="If you need help now">
      <Icon name="info" size={18} />
      <p>
        When you save, WellBe checks your words for a short list of warning signs. That list
        isn&apos;t complete, and it isn&apos;t a diagnosis. If it feels severe or concerning, contact
        a clinician. If you think it&apos;s an emergency, call your local emergency number.
      </p>
    </aside>
  );
}

function UrgentGuidance({
  evaluation,
  headingId,
  headingRef,
  onSaveAnyway,
  onBack,
  saving,
}: {
  evaluation: Evaluation;
  headingId: string;
  headingRef: RefObject<HTMLHeadingElement | null>;
  onSaveAnyway: () => void;
  onBack: () => void;
  saving: boolean;
}) {
  const g = evaluation.guidance;
  return (
    <section className={styles.urgent} aria-labelledby={headingId} data-state="urgent">
      <h2 id={headingId} ref={headingRef} tabIndex={-1} className={styles.question}>
        <Icon name="heart-pulse" size={22} />
        {g.headline}
      </h2>
      <p className={styles.urgentAction}>{g.action}</p>
      {g.emergency_number && (
        <a href={`tel:${g.emergency_number}`} className={styles.callLink}>
          Call {g.emergency_number}
        </a>
      )}
      {evaluation.crisis_support && g.crisis_line && (
        <p className={styles.body}>You can also reach {g.crisis_line}.</p>
      )}
      <p className={styles.body}>{g.rationale}</p>
      <p className={styles.body}>{g.backstop}</p>
      <div className={styles.row}>
        <Button variant="secondary" onClick={onSaveAnyway} disabled={saving}>
          {saving ? "Saving…" : "Save my check-in anyway"}
        </Button>
        <Button variant="tertiary" icon="arrow-left" onClick={onBack} disabled={saving}>
          Back to my answers
        </Button>
      </div>
    </section>
  );
}

function AfterSaveGuidance({ check }: { check: Check }) {
  if (check === "unavailable") {
    return (
      <aside className={styles.attention} aria-label="About warning signs" data-state="needs_attention">
        <Icon name="info" size={18} />
        <p>
          WellBe couldn&apos;t check your words for warning signs just now. If it feels severe or
          concerning, contact a clinician. If you think it&apos;s an emergency, call your local
          emergency number.
        </p>
      </aside>
    );
  }
  if (check.route !== "route_soon") return null;
  const g = check.guidance;
  return (
    <aside className={styles.attention} aria-label={g.headline} data-state="needs_attention">
      <Icon name="info" size={18} />
      <div>
        <p className={styles.attentionHeadline}>{g.headline}</p>
        <p>{g.action}</p>
        <p>{g.rationale}</p>
        <p>{g.backstop}</p>
      </div>
    </aside>
  );
}

export function TriageCheckIn() {
  const queryClient = useQueryClient();
  const threads = useThreads();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>(EMPTY);
  const [destination, setDestination] = useState<Destination>("new");
  const [title, setTitle] = useState("");
  const [titleTouched, setTitleTouched] = useState(false);
  const [existingId, setExistingId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState<{ threadId?: string; threadTitle?: string } | null>(null);
  const [check, setCheck] = useState<Check | null>(null);
  const [showUrgent, setShowUrgent] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);
  const idempotencyKeyRef = useRef<string | null>(null);
  const createdThreadRef = useRef<{ id: string; title: string } | null>(null);
  const formId = useId();

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    headingRef.current?.focus();
  }, [step, done, showUrgent]);

  const threadList = threads.data ?? [];
  const effectiveTitle = titleTouched ? title : suggestTitle(answers.what);

  function set<K extends keyof Answers>(key: K, value: Answers[K]) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setError(null);
    setCheck(null);
    setShowUrgent(false);
  }

  function next() {
    if (step === 0 && !answers.what.trim()) {
      setError("Tell us a little about what's going on first — a few words is enough.");
      return;
    }
    setError(null);
    setStep((s) => Math.min(s + 1, REVIEW_STEP));
  }

  function back() {
    setError(null);
    setStep((s) => Math.max(s - 1, 0));
  }

  function reset() {
    setAnswers(EMPTY);
    setStep(0);
    setDestination("new");
    setTitle("");
    setTitleTouched(false);
    setExistingId("");
    setError(null);
    setDone(null);
    setCheck(null);
    setShowUrgent(false);
    idempotencyKeyRef.current = null;
    createdThreadRef.current = null;
  }

  async function evaluate(): Promise<Check> {
    try {
      const { data, error: apiError } = await getApiClient().POST("/v2/triage/evaluate", {
        body: toRequest(answers),
      });
      if (apiError || !data) return "unavailable";
      return data;
    } catch {
      return "unavailable";
    }
  }

  async function submit({ acknowledgedUrgent = false }: { acknowledgedUrgent?: boolean } = {}) {
    if (destination === "new" && !effectiveTitle.trim()) {
      setError("Give the new thread a short name first.");
      return;
    }
    if (destination === "existing" && !existingId) {
      setError("Choose which thread this belongs to first.");
      return;
    }
    setError(null);
    setSubmitting(true);
    let evaluation = check;
    if (evaluation === null) {
      evaluation = await evaluate();
      setCheck(evaluation);
    }
    if (isUrgent(evaluation) && !acknowledgedUrgent) {
      setShowUrgent(true);
      setSubmitting(false);
      return;
    }
    const api = getApiClient();
    try {
      let thread: { id: string; title: string } | undefined;
      if (destination === "new") {
        if (!createdThreadRef.current) {
          const { data, error: apiError } = await api.POST("/v1/threads", {
            body: { title: effectiveTitle.trim() },
          });
          if (apiError || !data) throw new Error("thread");
          createdThreadRef.current = { id: data.thread_id, title: data.title };
        }
        thread = createdThreadRef.current;
      } else if (destination === "existing") {
        const found = threadList.find((t) => t.id === existingId);
        thread = { id: existingId, title: found?.title ?? "your thread" };
      }

      if (!idempotencyKeyRef.current) idempotencyKeyRef.current = crypto.randomUUID();
      const { data, error: apiError } = await api.POST("/v1/capture", {
        params: { header: { "Idempotency-Key": idempotencyKeyRef.current } },
        body: {
          schema_version: "c13.capture.request.v1",
          capture_type: "symptom",
          payload: { description: composeCheckIn(answers) },
          source: "Calm check-in",
          thread_id: thread?.id ?? null,
        },
      });
      if (apiError || !data) throw new Error("capture");

      idempotencyKeyRef.current = null;
      setShowUrgent(false);
      void queryClient.invalidateQueries({ queryKey: queryKeys.threads });
      setDone({ threadId: thread?.id, threadTitle: thread?.title });
    } catch {
      setError(
        "Your check-in couldn't be saved just now. Your answers are still here — please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className={styles.wrap}>
        <section className={styles.card} aria-labelledby={`${formId}-done`}>
          <h2 id={`${formId}-done`} ref={headingRef} tabIndex={-1} className={styles.question}>
            <Icon name="check-circle-2" size={22} />
            Saved in your own words
          </h2>
          <p className={styles.body}>
            {done.threadTitle
              ? `Your check-in is part of “${done.threadTitle}” now. WellBe keeps your words as you wrote them.`
              : "Your check-in is saved privately to your memory. WellBe keeps your words as you wrote them."}
          </p>
          <div className={styles.row}>
            {done.threadId ? (
              <Link href={`/threads/${done.threadId}`} className={styles.primaryLink}>
                Open the thread
                <Icon name="arrow-right" size={16} />
              </Link>
            ) : (
              <Link href="/" className={styles.primaryLink}>
                Back to Home
                <Icon name="arrow-right" size={16} />
              </Link>
            )}
            <Button variant="tertiary" onClick={reset}>
              Start another check-in
            </Button>
          </div>
        </section>
        {check && !isUrgent(check) && <AfterSaveGuidance check={check} />}
        <Backstop />
      </div>
    );
  }

  if (showUrgent && isUrgent(check)) {
    return (
      <div className={styles.wrap}>
        <UrgentGuidance
          evaluation={check}
          headingId={`${formId}-urgent`}
          headingRef={headingRef}
          saving={submitting}
          onSaveAnyway={() => void submit({ acknowledgedUrgent: true })}
          onBack={() => setShowUrgent(false)}
        />
        {error && (
          <p className={styles.error} role="alert">
            <Icon name="alert-circle" size={16} />
            {error}
          </p>
        )}
      </div>
    );
  }

  const isReview = step === REVIEW_STEP;
  const current = STEPS[step];

  return (
    <div className={styles.wrap}>
      <p className={styles.intro}>
        Take a moment to describe what feels off, in your own words. Nothing here is a diagnosis —
        WellBe saves what you say so you can follow it over time and share it if you choose.
      </p>
      <Backstop />

      <form
        className={styles.card}
        aria-labelledby={`${formId}-q`}
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          if (isReview) void submit();
          else next();
        }}
      >
        <p className={styles.progress}>
          {isReview ? "Review" : `Question ${step + 1} of ${STEPS.length}`}
          {!isReview && step > 0 && <span className={styles.optional}> · optional</span>}
        </p>
        <h2 id={`${formId}-q`} ref={headingRef} tabIndex={-1} className={styles.question}>
          {isReview ? "Here's what you told us" : current?.question}
        </h2>

        {step === 0 && (
          <div className={styles.field}>
            <label htmlFor={`${formId}-what`} className={styles.hintLabel}>
              As much or as little as you like.
            </label>
            <textarea
              id={`${formId}-what`}
              rows={4}
              value={answers.what}
              onChange={(e) => set("what", e.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? `${formId}-err` : undefined}
            />
          </div>
        )}

        {step === 1 && (
          <div className={styles.field}>
            <label htmlFor={`${formId}-change`} className={styles.hintLabel}>
              For example: “I usually sleep through the night — now I wake up twice.”
            </label>
            <textarea
              id={`${formId}-change`}
              rows={3}
              value={answers.change}
              onChange={(e) => set("change", e.target.value)}
            />
          </div>
        )}

        {step === 2 && (
          <ChoiceStep
            name={`${formId}-onset`}
            legend="When did it start?"
            options={ONSET_OPTIONS}
            value={answers.onset}
            onChange={(v) => set("onset", v)}
            noteLabel="Has it changed since then? (optional)"
            noteId={`${formId}-onset-note`}
            note={answers.onsetNote}
            onNote={(v) => set("onsetNote", v)}
          />
        )}

        {step === 3 && (
          <ChoiceStep
            name={`${formId}-impact`}
            legend="How much is it affecting your day?"
            options={IMPACT_OPTIONS}
            value={answers.impact}
            onChange={(v) => set("impact", v)}
            noteLabel="Anything specific it gets in the way of? (optional)"
            noteId={`${formId}-impact-note`}
            note={answers.impactNote}
            onNote={(v) => set("impactNote", v)}
          />
        )}

        {step === 4 && (
          <div className={styles.field}>
            <label htmlFor={`${formId}-worry`} className={styles.hintLabel}>
              What would you most like to understand, or ask a clinician?
            </label>
            <textarea
              id={`${formId}-worry`}
              rows={3}
              value={answers.worry}
              onChange={(e) => set("worry", e.target.value)}
            />
          </div>
        )}

        {isReview && (
          <Review
            answers={answers}
            onEdit={(i) => setStep(i)}
            formId={formId}
            destination={destination}
            setDestination={(d) => {
              setDestination(d);
              setError(null);
            }}
            title={effectiveTitle}
            setTitle={(t) => {
              setTitle(t);
              setTitleTouched(true);
              setError(null);
            }}
            threads={threadList}
            existingId={existingId}
            setExistingId={(id) => {
              setExistingId(id);
              setError(null);
            }}
          />
        )}

        {error && (
          <p id={`${formId}-err`} className={styles.error} role="alert">
            <Icon name="alert-circle" size={16} />
            {error}
          </p>
        )}

        <div className={styles.row}>
          {step > 0 && (
            <Button variant="tertiary" icon="arrow-left" onClick={back} disabled={submitting}>
              Back
            </Button>
          )}
          <button type="submit" className={styles.submit} disabled={submitting}>
            {isReview ? (submitting ? "Saving…" : "Save my check-in") : "Next"}
            {!isReview && <Icon name="arrow-right" size={16} />}
          </button>
        </div>
      </form>
    </div>
  );
}

function ChoiceStep({
  name,
  legend,
  options,
  value,
  onChange,
  noteLabel,
  noteId,
  note,
  onNote,
}: {
  name: string;
  legend: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  noteLabel: string;
  noteId: string;
  note: string;
  onNote: (v: string) => void;
}) {
  return (
    <>
      <fieldset className={styles.choices}>
        <legend className={styles.srOnly}>{legend}</legend>
        {options.map((o) => (
          <label key={o} className={styles.choice} data-checked={value === o || undefined}>
            <input
              type="radio"
              name={name}
              value={o}
              checked={value === o}
              onChange={() => onChange(o)}
            />
            <span>{o}</span>
          </label>
        ))}
      </fieldset>
      <div className={styles.field}>
        <label htmlFor={noteId} className={styles.hintLabel}>
          {noteLabel}
        </label>
        <input id={noteId} type="text" value={note} onChange={(e) => onNote(e.target.value)} />
      </div>
    </>
  );
}

function Review({
  answers,
  onEdit,
  formId,
  destination,
  setDestination,
  title,
  setTitle,
  threads,
  existingId,
  setExistingId,
}: {
  answers: Answers;
  onEdit: (step: number) => void;
  formId: string;
  destination: Destination;
  setDestination: (d: Destination) => void;
  title: string;
  setTitle: (t: string) => void;
  threads: { id: string; title: string }[];
  existingId: string;
  setExistingId: (id: string) => void;
}) {
  const rows: { step: number; label: string; value: string }[] = [
    { step: 0, label: "What's going on", value: answers.what.trim() },
    { step: 1, label: "Different from my normal", value: answers.change.trim() },
    { step: 2, label: "Started", value: withNote(answers.onset, answers.onsetNote) },
    { step: 3, label: "Effect on my day", value: withNote(answers.impact, answers.impactNote) },
    { step: 4, label: "Main worry or question", value: answers.worry.trim() },
  ];

  return (
    <>
      <section className={styles.voice} aria-label="Your words">
        <p className={styles.voiceLabel}>
          <Icon name="pencil" size={15} />
          Your words
        </p>
        <dl className={styles.answers}>
          {rows.map((r) => (
            <div key={r.step} className={styles.answer}>
              <dt>{r.label}</dt>
              <dd>
                {r.value ? (
                  <span className={styles.quote}>{r.value}</span>
                ) : (
                  <span className={styles.skipped}>Skipped</span>
                )}
                <button
                  type="button"
                  className={styles.edit}
                  onClick={() => onEdit(r.step)}
                  aria-label={`Edit: ${r.label}`}
                >
                  Edit
                </button>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      <fieldset className={styles.destinations}>
        <legend className={styles.legend}>Where should this go?</legend>
        <label className={styles.destination} data-checked={destination === "new" || undefined}>
          <input
            type="radio"
            name={`${formId}-dest`}
            checked={destination === "new"}
            onChange={() => setDestination("new")}
          />
          <span>Start a new thread for this</span>
        </label>
        {destination === "new" && (
          <div className={styles.field}>
            <label htmlFor={`${formId}-title`}>Thread name</label>
            <input
              id={`${formId}-title`}
              type="text"
              maxLength={TITLE_MAX}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
        )}
        {threads.length > 0 && (
          <label
            className={styles.destination}
            data-checked={destination === "existing" || undefined}
          >
            <input
              type="radio"
              name={`${formId}-dest`}
              checked={destination === "existing"}
              onChange={() => setDestination("existing")}
            />
            <span>Add it to a thread I already have</span>
          </label>
        )}
        {destination === "existing" && (
          <div className={styles.field}>
            <label htmlFor={`${formId}-thread`}>Thread</label>
            <select
              id={`${formId}-thread`}
              value={existingId}
              onChange={(e) => setExistingId(e.target.value)}
            >
              <option value="">Choose a thread…</option>
              {threads.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>
        )}
        <label className={styles.destination} data-checked={destination === "memory" || undefined}>
          <input
            type="radio"
            name={`${formId}-dest`}
            checked={destination === "memory"}
            onChange={() => setDestination("memory")}
          />
          <span>Just save it to my memory for now</span>
        </label>
      </fieldset>
    </>
  );
}
