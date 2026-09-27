"use client";

import { useState } from "react";
import { Button, Chip, Icon } from "@wellbe/ui";
import { formatShortDate } from "@/lib/adapters";
import { useReviewThingNoticed, useThingsNoticed } from "@/lib/hooks";
import styles from "./ThingsNoticed.module.css";

const TYPE_LABEL: Record<string, string> = {
  symptom: "Symptom",
  lab_abnormality: "Result",
  medication: "Medication",
  condition: "Condition",
};

/**
 * "Things noticed" (/v1/things-noticed): candidates WellBe spotted in what you
 * added, waiting for you to decide. Confirming opens a health thread; dismissing
 * sets it aside. Nothing becomes a thread without the person's say-so.
 */
export function ThingsNoticed() {
  const { data, isLoading, isError } = useThingsNoticed();
  const review = useReviewThingNoticed();
  const [failed, setFailed] = useState<string | null>(null);

  const pending = (data ?? []).filter((c) => c.status === "pending");
  if (isLoading || isError || pending.length === 0) return null;

  async function act(id: string, action: "confirm" | "dismiss") {
    setFailed(null);
    try {
      await review.mutateAsync({ id, action });
    } catch {
      setFailed(id);
    }
  }

  return (
    <section className={styles.section} aria-labelledby="things-noticed-heading">
      <header className={styles.head}>
        <h2 id="things-noticed-heading" className={styles.title}>
          <Icon name="sparkles" size={16} />
          Things noticed
        </h2>
        <span className={styles.sub}>
          From what you added — confirm to start a thread, or dismiss. Never a diagnosis.
        </span>
      </header>
      <ul className={styles.list}>
        {pending.map((c) => {
          const busy = review.isPending && review.variables?.id === c.candidate_id;
          const seen = formatShortDate(c.last_seen_at);
          return (
            <li key={c.candidate_id} className={styles.row}>
              <div className={styles.main}>
                <span className={styles.name}>{c.title}</span>
                <span className={styles.meta}>
                  <Chip size="sm">{TYPE_LABEL[c.candidate_type] ?? "Noticed"}</Chip>
                  {c.seen_count === 1 ? "Seen once" : `Seen ${c.seen_count} times`}
                  {seen ? ` · last ${seen}` : ""}
                </span>
                {failed === c.candidate_id && (
                  <span className={styles.error}>That didn&rsquo;t go through. Please try again.</span>
                )}
              </div>
              <div className={styles.actions}>
                <Button
                  variant="tertiary"
                  size="sm"
                  onClick={() => act(c.candidate_id, "dismiss")}
                  disabled={busy}
                  aria-label={`Dismiss ${c.title}`}
                >
                  Dismiss
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon="check"
                  onClick={() => act(c.candidate_id, "confirm")}
                  disabled={busy}
                  aria-label={`Confirm ${c.title}`}
                >
                  Confirm
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
