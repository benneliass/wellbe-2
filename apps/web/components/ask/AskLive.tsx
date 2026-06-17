"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "@wellbe/ui";
import type { components } from "@wellbe/api-client";
import { getApiClient, devSessionConfigured } from "@/lib/api";
import { StateNote } from "@/components/placeholder/StateNote";
import styles from "./AskLive.module.css";

type AskAnswer = components["schemas"]["AskAnswerV2"];

const MODE_TAG: Record<string, string> = {
  answered: "From your records",
  no_sources: "Nothing on record",
  out_of_scope_redirect: "For your clinician",
  urgent: "Please get help now",
  blocked: "Can't answer safely",
};

export function AskLive({ initialQuery }: { initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [answer, setAnswer] = useState<AskAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const askedRef = useRef<string | null>(null);

  async function ask(question: string) {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const { data, error: apiError } = await getApiClient().POST("/v2/ask", {
        body: { schema_version: "c13.ask.request.v1", question: q },
      });
      if (apiError || !data) {
        setError("Something went wrong answering that. Please try again.");
        return;
      }
      setAnswer(data);
    } catch {
      setError("Couldn't reach WellBe. Check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }

  // Auto-run the query passed in from the Home launcher (?q=...), once.
  useEffect(() => {
    if (devSessionConfigured && initialQuery && askedRef.current !== initialQuery) {
      askedRef.current = initialQuery;
      void ask(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  if (!devSessionConfigured) {
    return (
      <div className={styles.wrap}>
        {initialQuery && (
          <p className={styles.echo}>
            You asked: <strong>“{initialQuery}”</strong>
          </p>
        )}
        <StateNote
          icon="lock"
          title="Sign in to ask about your health"
          description="Ask WellBe answers only from your own records, so it needs you signed in first."
        />
      </div>
    );
  }

  const answerParagraphs = answer ? answer.answer_text.split("\n").filter(Boolean) : [];

  return (
    <div className={styles.wrap}>
      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault();
          void ask(query);
        }}
      >
        <Icon name="message-circle" size={18} />
        <input
          placeholder="Ask about your own health…"
          aria-label="Ask WellBe"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" className={styles.go} aria-label="Ask" disabled={loading}>
          <Icon name="arrow-right" size={18} />
        </button>
      </form>

      <p className={styles.hint}>
        <Icon name="lock" size={13} />
        Grounded only in your records — never a diagnosis or outside medical advice.
      </p>

      {error && <p className={styles.error}>{error}</p>}

      {loading && <p className={styles.hint}>Looking through your records…</p>}

      {answer && !loading && (
        <div className={styles.answer} data-mode={answer.mode}>
          <span className={styles.modeTag}>
            <Icon name={answer.mode === "urgent" ? "activity" : "badge-check"} size={13} />
            {MODE_TAG[answer.mode] ?? "Answer"}
          </span>

          <div className={styles.body}>
            {answerParagraphs.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>

          {(answer.citations ?? []).length > 0 && (
            <div className={styles.citations}>
              {(answer.citations ?? []).map((c, i) => (
                <span key={i} className={styles.cite}>
                  <Icon name="badge-check" size={11} />
                  {c.label}
                </span>
              ))}
            </div>
          )}

          {(answer.next_steps ?? []).length > 0 && (
            <div className={styles.steps}>
              <span className={styles.stepsLabel}>What you can do</span>
              <ul>
                {(answer.next_steps ?? []).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
