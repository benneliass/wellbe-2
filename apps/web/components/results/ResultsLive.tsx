"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { Button, Icon } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";
import { StateNote } from "@/components/placeholder/StateNote";
import { compareWithPrevious, formatDate, formatReading } from "@/lib/records-format";
import {
  recordsKeys,
  useResults,
  type AnalyteResult,
  type RangePosition,
} from "@/lib/records-hooks";
import styles from "./ResultsLive.module.css";

const POSITION_ICON: Record<RangePosition, string> = {
  within: "check-circle-2",
  outside: "info",
  not_compared: "circle-help",
};

const POSITION_SHORT: Record<RangePosition, string> = {
  within: "Within",
  outside: "Outside",
  not_compared: "Not compared",
};

function sourceIcon(kind: string): string {
  if (kind === "entered_by_you") return "pencil";
  if (kind === "connected_source") return "activity";
  return "file-text";
}

export function ResultsLive({
  documentId,
  analyteName,
}: {
  documentId?: string;
  analyteName?: string;
}) {
  const { data, isPending, isError, refetch, signedIn } = useResults();
  const queryClient = useQueryClient();
  const [captureOpen, setCaptureOpen] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  if (signedIn === false) {
    return (
      <div className={styles.wrap}>
        <StateNote
          icon="flask-conical"
          title="Sign in to see your results"
          description="Your results come from what you enter and the documents you add. They're private to you."
        />
      </div>
    );
  }

  if (signedIn === undefined || isPending) {
    return (
      <div className={styles.wrap}>
        <p className={styles.hint} role="status">
          <Icon name="flask-conical" size={16} />
          Gathering your results…
        </p>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className={styles.wrap}>
        <div className={styles.problem} role="alert">
          <p>We couldn&apos;t load your results just now. Nothing is lost — please try again.</p>
          <Button variant="secondary" icon="rotate-ccw" onClick={() => void refetch()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  const named = analyteName?.trim().toLowerCase();
  const analytes = data.analytes.filter((a) => {
    if (documentId && !a.history.some((o) => o.source.document_id === documentId)) return false;
    if (named && a.display_label.trim().toLowerCase() !== named) return false;
    return true;
  });

  return (
    <div className={styles.wrap}>
      <section className={styles.intro} aria-labelledby="results-headline">
        <h2 id="results-headline" className={styles.headline}>
          {named ? analyteName : documentId ? "Results found in one document" : data.headline}
        </h2>
        <p className={styles.note}>{data.note}</p>
        <div className={styles.actions}>
          <Button variant="primary" icon="plus" onClick={() => setCaptureOpen(true)}>
            Add a result
          </Button>
          {(documentId || named) && (
            <Link href="/results" className={styles.textLink}>
              Show all results
            </Link>
          )}
        </div>
        {justSaved && (
          <p className={styles.saved} role="status">
            <Icon name="check-circle-2" size={16} />
            Saved. It will appear here once WellBe has read it.
          </p>
        )}
      </section>

      {analytes.length === 0 ? (
        <StateNote
          icon="flask-conical"
          title={
            named
              ? "That result is not here"
              : documentId
                ? "No results from this document"
                : "Add your first result"
          }
          description={
            named
              ? "It may still be waiting to be read, or it was entered under a different name."
              : documentId
                ? "WellBe didn't find lab or test values in that document."
                : "When you add a lab or test result — typed in or from a document — it will appear here with its date, reference range, and source."
          }
        />
      ) : (
        <ul className={styles.list} aria-label="Your results">
            {analytes.map((a) => (
            <AnalyteCard key={a.analyte_key} analyte={a} focused={Boolean(named)} />
          ))}
        </ul>
      )}

      {captureOpen && (
        <CaptureModal
          initialType="lab"
          onClose={() => setCaptureOpen(false)}
          onCaptured={() => {
            setJustSaved(true);
            void queryClient.invalidateQueries({ queryKey: recordsKeys.results });
          }}
        />
      )}
    </div>
  );
}

function AnalyteCard({ analyte: a, focused }: { analyte: AnalyteResult; focused?: boolean }) {
  const cardRef = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (focused) cardRef.current?.scrollIntoView({ block: "center" });
  }, [focused]);
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const headingId = useId();
  const latest = a.latest;
  const previous = a.history.length > 1 ? a.history[a.history.length - 2] : undefined;
  const change = previous ? compareWithPrevious(latest, previous) : null;

  return (
    <li
      ref={cardRef}
      className={styles.card}
      aria-labelledby={headingId}
      data-focus={focused ? "true" : undefined}
    >
      <div className={styles.cardHead}>
        <h3 id={headingId} className={styles.name}>
          {a.display_label}
        </h3>
        <span className={styles.date}>{formatDate(latest.observed_at)}</span>
      </div>

      <p className={styles.value}>
        <span className={styles.num}>{latest.value}</span>
        {latest.unit && <span className={styles.unit}> {latest.unit}</span>}
      </p>

      <p className={styles.range} data-position={latest.range_position}>
        <Icon name={POSITION_ICON[latest.range_position]} size={16} />
        <span>
          {latest.range_note}
          {latest.reference_range && (
            <span className={styles.rangeText}>Range shown: {latest.reference_range}</span>
          )}
        </span>
      </p>

      {change && <p className={styles.change}>{change}</p>}

      <p className={styles.source}>
        <Icon name={sourceIcon(latest.source.kind)} size={15} />
        <span>{latest.source.display_label}</span>
        {latest.source.document_id && (
          <Link href={`/documents#document-${latest.source.document_id}`} className={styles.textLink}>
            View document
          </Link>
        )}
      </p>

      {a.threads.length > 0 && (
        <ul className={styles.threads} aria-label={`Threads for ${a.display_label}`}>
          {a.threads.map((t) => (
            <li key={t.thread_id}>
              <Link href={`/threads/${t.thread_id}`} className={styles.thread}>
                <Icon name="git-fork" size={15} />
                <span>In your thread: {t.title}</span>
                <Icon name="arrow-right" size={15} />
              </Link>
              <Link href={`/memory?thread=${t.thread_id}`} className={styles.thread}>
                <Icon name="book" size={15} />
                <span>In Memory</span>
                <Icon name="arrow-right" size={15} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      {a.history.length > 1 && (
        <>
          <button
            type="button"
            className={styles.expand}
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((v) => !v)}
          >
            <Icon name={open ? "chevron-down" : "chevron-right"} size={16} />
            {open ? "Hide readings" : `Show all ${a.history.length} readings`}
          </button>
          {open && (
            <div
              id={panelId}
              className={styles.tableWrap}
              role="region"
              aria-label={`All readings of ${a.display_label}`}
              tabIndex={0}
            >
              <table className={styles.table}>
                <caption className={styles.caption}>
                  All readings of {a.display_label}, oldest first
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Value</th>
                    <th scope="col">Range shown</th>
                    <th scope="col">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {a.history.map((o, i) => (
                    <tr key={`${o.source.capture_id}-${i}`}>
                      <td>{formatDate(o.observed_at)}</td>
                      <td className={styles.numCell}>{formatReading(o)}</td>
                      <td>
                        {o.reference_range ?? "None given"}
                        <span className={styles.position}> · {POSITION_SHORT[o.range_position]}</span>
                      </td>
                      <td>{o.source.display_label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </li>
  );
}
